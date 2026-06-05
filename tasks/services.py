"""Task domain services: id generation, activity logging, realtime board sync."""
import datetime

from core.constants import ACTIVITY_TASK_CREATED
from core.realtime import broadcast, kanban_group
from tasks.models import ActivityLog, Task


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def board_scope(user, project):
    """Role-based task queryset for a project's Kanban board.

    * Management (Super Admin / Admin / Project Manager): all project tasks.
    * Team Leader: tasks of their team members (+ their own / reported).
    * Employee: only tasks assigned to or reported by them.

    Returns ``(queryset, scope_label)``.
    """
    from core.constants import MANAGEMENT_ROLES, ROLE_TEAM_LEADER
    from tasks.models import Task

    base = Task.objects(project=project)
    if user.role in MANAGEMENT_ROLES:
        return base, "All tasks"

    if user.role == ROLE_TEAM_LEADER:
        from accounts.models import Team

        member_ids = {user.id}
        for team in Team.objects(leader=user):
            member_ids.update(m.id for m in team.members if m)
        return (
            base.filter(
                __raw__={
                    "$or": [
                        {"assigned_to": {"$in": list(member_ids)}},
                        {"reporter": user.id},
                    ]
                }
            ),
            "Your team's tasks",
        )

    # Employee
    return (
        base.filter(__raw__={"$or": [{"assigned_to": user.id}, {"reporter": user.id}]}),
        "Your tasks",
    )


def next_task_id():
    last = Task.objects.order_by("-created_at").first()
    n = Task.objects.count() + 1
    # Best effort sequential; fall back to count if parsing fails.
    if last and last.task_id and last.task_id.startswith("TASK-"):
        try:
            n = max(n, int(last.task_id.split("-")[1]) + 1)
        except (ValueError, IndexError):
            pass
    return f"TASK-{n:05d}"


def log_activity(*, actor, message, verb=ACTIVITY_TASK_CREATED, task=None, project=None):
    return ActivityLog(
        actor=actor,
        message=message,
        verb=verb,
        task=task,
        project=project or (task.project if task else None),
    ).save()


def task_card(task):
    """Compact representation used by the kanban board + WS events."""
    from core.utils import doc_brief

    return {
        "id": str(task.id),
        "task_id": task.task_id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "progress": task.progress,
        "board_order": task.board_order,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "is_overdue": task.is_overdue,
        "assigned_to": doc_brief(task.assigned_to),
        "tags": list(task.tags or []),
        "subtask_count": len(task.subtasks),
        "project_id": str(task.project.id) if task.project else None,
    }


def broadcast_board(project_id, event, task=None, extra=None):
    """Push a kanban event to everyone watching the project board."""
    payload = {"event": event}
    if task is not None:
        payload["task"] = task_card(task)
    if extra:
        payload.update(extra)
    broadcast(kanban_group(str(project_id)), "board_event", payload)
