import datetime
import uuid

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.api_helpers import paginate
from core.constants import (
    ACTUAL_HOURS_EDIT_ROLES,
    ACTIVITY_COMMENT_ADDED,
    ACTIVITY_FILE_UPLOADED,
    ACTIVITY_STATUS_CHANGED,
    ACTIVITY_TASK_ASSIGNED,
    ACTIVITY_TASK_CREATED,
    ACTIVITY_TASK_UPDATED,
    FULL_VISIBILITY_ROLES,
    KANBAN_COLUMNS,
    MANAGEMENT_ROLES,
    NOTIF_COMMENT_MENTION,
    NOTIF_TASK_ASSIGNED,
    NOTIF_TASK_COMPLETED,
    NOTIF_TASK_UPDATED,
    STATUS_LABELS,
)
from core.utils import extract_mentions, save_upload
from notifications.services import notify
from projects.models import Project
from projects.services import can_view_project, visible_projects
from tasks.models import (
    ActivityLog,
    Attachment,
    Comment,
    SubTask,
    Task,
    TimeLog,
    running_segment_seconds,
)
from tasks.serializers import (
    BulkAssignSerializer,
    BulkStatusSerializer,
    CommentSerializer,
    MoveSerializer,
    SubtaskSerializer,
    TaskUpdateSerializer,
    TaskWriteSerializer,
    activity_repr,
    attachment_repr,
    comment_repr,
    task_repr,
    timelog_repr,
)
from tasks.services import (
    board_scope,
    broadcast_board,
    log_activity,
    next_task_id,
)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Visibility helpers
# ---------------------------------------------------------------------------
def visible_tasks(user):
    # Only super-admins see every task; everyone else is scoped to tasks in
    # projects they can see, plus tasks assigned to or reported by them.
    if user.role in FULL_VISIBILITY_ROLES:
        return Task.objects()
    project_ids = [p.id for p in visible_projects(user, include_archived=True)]
    return Task.objects(
        __raw__={
            "$or": [
                {"project": {"$in": project_ids}},
                {"assigned_to": user.id},
                {"reporter": user.id},
            ]
        }
    )


def get_task_for_user(user, pk):
    task = Task.objects(id=pk).first()
    if not task:
        return None, Response({"detail": "Not found."}, status=404)
    if user.role not in FULL_VISIBILITY_ROLES:
        allowed = (
            (task.assigned_to and str(task.assigned_to.id) == str(user.id))
            or (task.reporter and str(task.reporter.id) == str(user.id))
            or (task.project and can_view_project(user, task.project))
        )
        if not allowed:
            return None, Response({"detail": "Forbidden."}, status=403)
    return task, None


def require_task_assignee(task, user):
    """Gate timer actions to the task's assigned person only.

    Tracked time belongs to whoever is actually doing the work, so only the
    assignee may start/pause/resume/stop a task's timer. Everyone else (other
    employees, the reporter, project viewers, even management) is rejected —
    the UI disables the controls for them and this enforces it server-side.
    Returns an error Response when the user is not the assignee, else None.
    """
    if not task.assigned_to or str(task.assigned_to.id) != str(user.id):
        return Response(
            {"detail": "Only the assigned person can use this task's timer."},
            status=403,
        )
    return None


# ---------------------------------------------------------------------------
# Module 3: Task CRUD + list with search/filter/sort/pagination
# ---------------------------------------------------------------------------
class TaskListCreateView(APIView):
    def get(self, request):
        qs = visible_tasks(request.user)
        p = request.query_params
        if p.get("project_id"):
            qs = qs.filter(project=p["project_id"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("priority"):
            qs = qs.filter(priority=p["priority"])
        if p.get("assigned_to_id"):
            qs = qs.filter(assigned_to=p["assigned_to_id"])
        if p.get("mine") == "true":
            qs = qs.filter(assigned_to=request.user.id)
        if p.get("search"):
            qs = qs.filter(title__icontains=p["search"])
        if p.get("tag"):
            qs = qs.filter(tags=p["tag"])
        qs = qs.order_by(p.get("ordering", "-created_at"))
        return paginate(request, qs, task_repr)

    def post(self, request):
        s = TaskWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        project = Project.objects(id=d["project_id"]).first()
        if not project:
            return Response({"detail": "Project not found."}, status=400)
        # RBAC: don't let a user create tasks in a project they can't access.
        if not can_view_project(request.user, project):
            return Response({"detail": "Forbidden."}, status=403)
        assignee = (
            User.objects(id=d["assigned_to_id"]).first()
            if d.get("assigned_to_id")
            else None
        )
        task = Task(
            task_id=next_task_id(),
            title=d["title"],
            description=d.get("description"),
            project=project,
            assigned_to=assignee,
            reporter=request.user,
            priority=d["priority"],
            status=d["status"],
            due_date=d.get("due_date"),
            estimated_hours=d.get("estimated_hours") or 0,
            tags=d.get("tags", []),
            created_by=request.user,
        ).save()
        log_activity(
            actor=request.user,
            task=task,
            verb=ACTIVITY_TASK_CREATED,
            message=f"created task {task.task_id}",
        )
        if assignee:
            notify(
                assignee,
                title="New task assigned",
                message=f"You were assigned '{task.title}'.",
                notif_type=NOTIF_TASK_ASSIGNED,
                actor=request.user,
                link=f"/tasks/{task.id}/",
            )
        broadcast_board(project.id, "created", task)
        return Response(task_repr(task, full=True), status=201)


class TaskDetailView(APIView):
    def get(self, request, pk):
        task, err = get_task_for_user(request.user, pk)
        if err:
            return err
        return Response(task_repr(task, full=True))

    def patch(self, request, pk):
        task, err = get_task_for_user(request.user, pk)
        if err:
            return err
        s = TaskUpdateSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        prev_status = task.status
        for f in ("title", "description", "priority", "due_date", "estimated_hours",
                  "tags"):
            if f in d:
                setattr(task, f, d[f])
        if "assigned_to_id" in d:
            task.assigned_to = (
                User.objects(id=d["assigned_to_id"]).first() if d["assigned_to_id"] else None
            )
        status_changed = "status" in d and d["status"] != prev_status
        if status_changed:
            task.status = d["status"]
            if d["status"] in ("completed", "rejected"):
                task.completed_at = utcnow()
                # Auto-stop any running timers so actual_hours stays accurate.
                # (task.save() below recomputes actual_hours from the logs.)
                for log in TimeLog.objects(task=task, end_time=None):
                    if log.is_running:
                        log.accumulated_seconds += running_segment_seconds(log.start_time)
                        log.is_running = False
                    log.end_time = utcnow()
                    log.save()
            log_activity(
                actor=request.user,
                task=task,
                verb=ACTIVITY_STATUS_CHANGED,
                message=(
                    f"changed status from {STATUS_LABELS.get(prev_status, prev_status)}"
                    f" → {STATUS_LABELS.get(d['status'], d['status'])}"
                ),
            )
            if d["status"] == "completed" and task.reporter:
                notify(
                    task.reporter,
                    title="Task completed",
                    message=f"'{task.title}' was marked completed.",
                    notif_type=NOTIF_TASK_COMPLETED,
                    actor=request.user,
                    link=f"/tasks/{task.id}/",
                )
        task.save()
        # A status change already logged ACTIVITY_STATUS_CHANGED above; don't
        # also emit a redundant generic "updated task" entry for the same edit.
        if not status_changed:
            log_activity(
                actor=request.user,
                task=task,
                verb=ACTIVITY_TASK_UPDATED,
                message=f"updated task {task.task_id}",
            )
            # Notify the assignee of a content edit (status changes get their own
            # notifications); skip self-notifying the editor.
            if task.assigned_to and str(task.assigned_to.id) != str(request.user.id):
                notify(
                    task.assigned_to,
                    title="Task updated",
                    message=f"'{task.title}' was updated.",
                    notif_type=NOTIF_TASK_UPDATED,
                    actor=request.user,
                    link=f"/tasks/{task.id}/",
                )
        broadcast_board(task.project.id, "updated", task)
        return Response(task_repr(task, full=True))

    def delete(self, request, pk):
        task, err = get_task_for_user(request.user, pk)
        if err:
            return err
        if request.user.role not in MANAGEMENT_ROLES and (
            not task.reporter or str(task.reporter.id) != str(request.user.id)
        ):
            return Response({"detail": "Forbidden."}, status=403)
        project_id = task.project.id if task.project else None
        Comment.objects(task=task).delete()
        TimeLog.objects(task=task).delete()
        ActivityLog.objects(task=task).delete()
        task.delete()
        if project_id:
            broadcast_board(project_id, "deleted", extra={"task_id": pk})
        return Response(status=204)


# ---------------------------------------------------------------------------
# Assign / Reassign / Clone
# ---------------------------------------------------------------------------
@api_view(["POST"])
def assign_task(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    assignee = User.objects(id=request.data.get("assigned_to_id")).first()
    if not assignee:
        return Response({"detail": "Assignee not found."}, status=400)
    task.assigned_to = assignee
    task.save()
    log_activity(
        actor=request.user,
        task=task,
        verb=ACTIVITY_TASK_ASSIGNED,
        message=f"assigned task to {assignee.full_name}",
    )
    notify(
        assignee,
        title="Task assigned",
        message=f"You were assigned '{task.title}'.",
        notif_type=NOTIF_TASK_ASSIGNED,
        actor=request.user,
        link=f"/tasks/{task.id}/",
    )
    broadcast_board(task.project.id, "updated", task)
    return Response(task_repr(task, full=True))


@api_view(["POST"])
def clone_task(request, pk):
    src, err = get_task_for_user(request.user, pk)
    if err:
        return err
    clone = Task(
        task_id=next_task_id(),
        title=f"{src.title} (copy)",
        description=src.description,
        project=src.project,
        assigned_to=src.assigned_to,
        reporter=request.user,
        priority=src.priority,
        status="todo",
        due_date=src.due_date,
        estimated_hours=src.estimated_hours,
        tags=list(src.tags or []),
        subtasks=[
            SubTask(sid=uuid.uuid4().hex, title=s.title, assigned_to=s.assigned_to)
            for s in src.subtasks
        ],
        created_by=request.user,
    ).save()
    log_activity(
        actor=request.user,
        task=clone,
        verb=ACTIVITY_TASK_CREATED,
        message=f"cloned from {src.task_id}",
    )
    broadcast_board(clone.project.id, "created", clone)
    return Response(task_repr(clone, full=True), status=201)


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------
@api_view(["POST"])
def bulk_assign(request):
    if request.user.role not in MANAGEMENT_ROLES:
        return Response({"detail": "Forbidden."}, status=403)
    s = BulkAssignSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    assignee = User.objects(id=s.validated_data["assigned_to_id"]).first()
    if not assignee:
        return Response({"detail": "Assignee not found."}, status=400)
    tasks = Task.objects(id__in=s.validated_data["task_ids"])
    updated = 0
    for t in tasks:
        t.assigned_to = assignee
        t.save()
        log_activity(
            actor=request.user, task=t, verb=ACTIVITY_TASK_ASSIGNED,
            message=f"bulk-assigned to {assignee.full_name}",
        )
        notify(
            assignee, title="Task assigned",
            message=f"You were assigned '{t.title}'.",
            notif_type=NOTIF_TASK_ASSIGNED, actor=request.user,
            link=f"/tasks/{t.id}/",
        )
        broadcast_board(t.project.id, "updated", t)
        updated += 1
    return Response({"updated": updated})


@api_view(["POST"])
def bulk_status(request):
    s = BulkStatusSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    new_status = s.validated_data["status"]
    tasks = Task.objects(id__in=s.validated_data["task_ids"])
    updated = 0
    for t in tasks:
        if request.user.role not in MANAGEMENT_ROLES:
            if not (t.assigned_to and str(t.assigned_to.id) == str(request.user.id)):
                continue
        prev = t.status
        t.status = new_status
        if new_status in ("completed", "rejected"):
            t.completed_at = utcnow()
            # Auto-stop running timers so actual_hours finalizes correctly
            # (matches single-task complete via move_task / TaskDetailView.patch).
            for log in TimeLog.objects(task=t, end_time=None):
                if log.is_running:
                    log.accumulated_seconds += running_segment_seconds(log.start_time)
                    log.is_running = False
                log.end_time = utcnow()
                log.save()
        t.save()
        log_activity(
            actor=request.user, task=t, verb=ACTIVITY_STATUS_CHANGED,
            message=f"bulk status {prev} → {new_status}",
        )
        broadcast_board(t.project.id, "updated", t)
        updated += 1
    return Response({"updated": updated})


# ---------------------------------------------------------------------------
# Module 5: Kanban board data + move
# ---------------------------------------------------------------------------
@api_view(["GET"])
def kanban_board(request, project_id):
    project = Project.objects(id=project_id).first()
    if not project:
        return Response({"detail": "Not found."}, status=404)
    if not can_view_project(request.user, project):
        return Response({"detail": "Forbidden."}, status=403)
    # Scope the visible cards by the viewer's role (RBAC).
    qs, scope_label = board_scope(request.user, project)
    if request.query_params.get("search"):
        qs = qs.filter(title__icontains=request.query_params["search"])
    if request.query_params.get("assigned_to_id"):
        qs = qs.filter(assigned_to=request.query_params["assigned_to_id"])
    columns = {col: [] for col in KANBAN_COLUMNS}
    for t in qs.order_by("board_order", "created_at"):
        if t.status in columns:
            columns[t.status].append(task_repr(t))
    return Response(
        {
            "project": {"id": str(project.id), "name": project.name},
            "scope": scope_label,
            "columns": [
                {"key": col, "label": STATUS_LABELS[col], "tasks": columns[col]}
                for col in KANBAN_COLUMNS
            ],
        }
    )


@api_view(["POST"])
def move_task(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    s = MoveSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    prev = task.status
    task.status = s.validated_data["status"]
    task.board_order = s.validated_data.get("board_order", 0)
    if task.status in ("completed", "rejected"):
        task.completed_at = utcnow()
        for log in TimeLog.objects(task=task, end_time=None):
            if log.is_running:
                log.accumulated_seconds += running_segment_seconds(log.start_time)
                log.is_running = False
            log.end_time = utcnow()
            log.save()
    task.save()  # recomputes actual_hours from the (now-stopped) time logs
    if prev != task.status:
        log_activity(
            actor=request.user, task=task, verb=ACTIVITY_STATUS_CHANGED,
            message=f"moved {STATUS_LABELS.get(prev, prev)} → "
                    f"{STATUS_LABELS.get(task.status, task.status)}",
        )
    broadcast_board(task.project.id, "moved", task, extra={"from": prev})
    return Response(task_repr(task))


# ---------------------------------------------------------------------------
# Module 4: Subtasks
# ---------------------------------------------------------------------------
@api_view(["POST"])
def add_subtask(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    s = SubtaskSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    assignee = (
        User.objects(id=s.validated_data["assigned_to_id"]).first()
        if s.validated_data.get("assigned_to_id")
        else None
    )
    task.subtasks.append(
        SubTask(sid=uuid.uuid4().hex, title=s.validated_data["title"], assigned_to=assignee)
    )
    task.save()
    broadcast_board(task.project.id, "updated", task)
    return Response(task_repr(task, full=True), status=201)


@api_view(["POST"])
def toggle_subtask(request, pk, sid):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    found = False
    for st in task.subtasks:
        if st.sid == sid:
            st.is_done = not st.is_done
            st.completed_at = utcnow() if st.is_done else None
            found = True
            break
    if not found:
        return Response({"detail": "Subtask not found."}, status=404)
    task.save()
    broadcast_board(task.project.id, "updated", task)
    return Response(task_repr(task, full=True))


@api_view(["DELETE"])
def delete_subtask(request, pk, sid):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    task.subtasks = [s for s in task.subtasks if s.sid != sid]
    task.save()
    broadcast_board(task.project.id, "updated", task)
    return Response(task_repr(task, full=True))


# ---------------------------------------------------------------------------
# Module 6: Comments (+ @mentions)
# ---------------------------------------------------------------------------
def _resolve_mentions(text):
    handles = extract_mentions(text)
    users = []
    for h in handles:
        u = User.objects(employee_id=h).first() or User.objects(
            full_name__iexact=h.replace("_", " ")
        ).first()
        if u:
            users.append(u)
    return users


class CommentListCreateView(APIView):
    def get(self, request, pk):
        task, err = get_task_for_user(request.user, pk)
        if err:
            return err
        comments = Comment.objects(task=task).order_by("created_at")
        return Response([comment_repr(c) for c in comments])

    def post(self, request, pk):
        task, err = get_task_for_user(request.user, pk)
        if err:
            return err
        s = CommentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        mentions = _resolve_mentions(s.validated_data["body"])
        comment = Comment(
            task=task,
            author=request.user,
            body=s.validated_data["body"],
            mentions=mentions,
        ).save()
        log_activity(
            actor=request.user, task=task, verb=ACTIVITY_COMMENT_ADDED,
            message="added a comment",
        )
        for m in mentions:
            notify(
                m, title="You were mentioned",
                message=f"{request.user.full_name} mentioned you on '{task.title}'.",
                notif_type=NOTIF_COMMENT_MENTION, actor=request.user,
                link=f"/tasks/{task.id}/",
            )
        return Response(comment_repr(comment), status=201)


class CommentDetailView(APIView):
    def patch(self, request, pk, comment_id):
        comment = Comment.objects(id=comment_id, task=pk).first()
        if not comment:
            return Response({"detail": "Not found."}, status=404)
        if str(comment.author.id) != str(request.user.id):
            return Response({"detail": "Forbidden."}, status=403)
        comment.body = request.data.get("body", comment.body)
        comment.mentions = _resolve_mentions(comment.body)
        comment.is_edited = True
        comment.updated_at = utcnow()
        comment.save()
        return Response(comment_repr(comment))

    def delete(self, request, pk, comment_id):
        comment = Comment.objects(id=comment_id, task=pk).first()
        if not comment:
            return Response({"detail": "Not found."}, status=404)
        if str(comment.author.id) != str(request.user.id) and (
            request.user.role not in MANAGEMENT_ROLES
        ):
            return Response({"detail": "Forbidden."}, status=403)
        comment.delete()
        return Response(status=204)


# ---------------------------------------------------------------------------
# Module 7: Attachments
# ---------------------------------------------------------------------------
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_attachment(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "No file provided."}, status=400)
    try:
        path, name, size, ctype = save_upload(f, "attachments")
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    att = Attachment(
        file_path=path, original_name=name, size=size,
        content_type=ctype, uploaded_by=request.user,
    ).save()
    task.attachments.append(att)
    task.save()
    log_activity(
        actor=request.user, task=task, verb=ACTIVITY_FILE_UPLOADED,
        message=f"uploaded {name}",
    )
    broadcast_board(task.project.id, "updated", task)
    return Response(attachment_repr(att), status=201)


@api_view(["DELETE"])
def delete_attachment(request, pk, attachment_id):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    att = Attachment.objects(id=attachment_id).first()
    if not att:
        return Response({"detail": "Not found."}, status=404)
    task.attachments = [a for a in task.attachments if str(a.id) != attachment_id]
    task.save()
    att.delete()
    return Response(status=204)


# ---------------------------------------------------------------------------
# Module 8: Time tracking
# ---------------------------------------------------------------------------
def _running_log(task, user):
    return TimeLog.objects(task=task, employee=user, is_running=True).first()


def _open_log(task, user):
    """Any not-yet-stopped timer (running OR paused) for this user+task."""
    return TimeLog.objects(task=task, employee=user, end_time=None).first()


@api_view(["POST"])
def timer_start(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    err = require_task_assignee(task, request.user)
    if err:
        return err
    # A closed task's actual time is final — don't let a new timer start
    # against it (the UI disables the controls; enforce it server-side too).
    if task.status in ("completed", "rejected"):
        return Response(
            {"detail": "Task is closed — timer cannot be started."}, status=400
        )
    # Block if ANY open timer exists (running or paused). Previously this only
    # checked for a *running* timer, so pause-then-start created a second open
    # log and double-counted wall-clock time. A paused timer must be *resumed*.
    existing = _open_log(task, request.user)
    if existing:
        msg = ("Timer already running."
               if existing.is_running
               else "Timer is paused — resume it instead of starting a new one.")
        return Response({"detail": msg}, status=400)
    log = TimeLog(task=task, employee=request.user, start_time=utcnow()).save()
    return Response(timelog_repr(log), status=201)


@api_view(["POST"])
def timer_pause(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    err = require_task_assignee(task, request.user)
    if err:
        return err
    log = _running_log(task, request.user)
    if not log:
        return Response({"detail": "No running timer."}, status=400)
    log.accumulated_seconds += running_segment_seconds(log.start_time)
    log.is_running = False
    log.save()
    return Response(timelog_repr(log))


@api_view(["POST"])
def timer_resume(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    err = require_task_assignee(task, request.user)
    if err:
        return err
    if task.status in ("completed", "rejected"):
        return Response(
            {"detail": "Task is closed — timer cannot be resumed."}, status=400
        )
    log = TimeLog.objects(
        task=task, employee=request.user, is_running=False, end_time=None
    ).order_by("-created_at").first()
    if not log:
        return Response({"detail": "No paused timer."}, status=400)
    log.start_time = utcnow()
    log.is_running = True
    log.save()
    return Response(timelog_repr(log))


@api_view(["POST"])
def timer_stop(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    err = require_task_assignee(task, request.user)
    if err:
        return err
    log = TimeLog.objects(
        task=task, employee=request.user, end_time=None
    ).order_by("-created_at").first()
    if not log:
        return Response({"detail": "No active timer."}, status=400)
    if log.is_running:
        log.accumulated_seconds += running_segment_seconds(log.start_time)
        log.is_running = False
    log.end_time = utcnow()
    log.save()
    # task.save() recomputes actual_hours from the task's time logs.
    task.save()
    return Response(timelog_repr(log))


@api_view(["POST"])
def set_actual_hours(request, pk):
    """Manually override (or clear) a task's actual hours.

    Restricted to super-admins and project managers. Send ``actual_hours`` as a
    number to override, or null / empty string to clear the override and fall
    back to the tracked time logs.
    """
    if request.user.role not in ACTUAL_HOURS_EDIT_ROLES:
        return Response({"detail": "Forbidden."}, status=403)
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err

    raw = request.data.get("actual_hours", None)
    if raw in (None, ""):
        task.actual_hours_override = None
        action_msg = "cleared the manual actual-hours override"
    else:
        try:
            hours = float(raw)
        except (TypeError, ValueError):
            return Response({"detail": "actual_hours must be a number."}, status=400)
        if hours < 0:
            return Response({"detail": "actual_hours cannot be negative."}, status=400)
        task.actual_hours_override = hours
        action_msg = f"set actual hours to {hours:g}h"

    task.save()  # recomputes the denormalized actual_hours from actual_seconds
    log_activity(
        actor=request.user,
        task=task,
        verb=ACTIVITY_TASK_UPDATED,
        message=action_msg,
    )
    broadcast_board(task.project.id, "updated", task)
    return Response(
        {
            "total_seconds": task.actual_seconds,
            "actual_hours": task.actual_hours,
            "is_overridden": task.actual_hours_is_overridden,
        }
    )


@api_view(["GET"])
def task_timelogs(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    logs = TimeLog.objects(task=task).order_by("-created_at")
    return Response(
        {
            "total_seconds": sum(t.total_seconds for t in logs),
            "logs": [timelog_repr(t) for t in logs],
        }
    )


# ---------------------------------------------------------------------------
# Module 9: Activity log
# ---------------------------------------------------------------------------
@api_view(["GET"])
def task_activity(request, pk):
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    logs = ActivityLog.objects(task=task).order_by("-created_at")
    return Response([activity_repr(a) for a in logs])
