"""Module 10: Dashboard aggregations."""
import datetime

from accounts.models import User
from core.constants import MANAGEMENT_ROLES, STATUS_LABELS, TASK_STATUSES
from projects.models import Project
from tasks.models import Task, TimeLog


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _task_scope(user):
    if user.role in MANAGEMENT_ROLES:
        return Task.objects()
    # Mirror tasks.api_views.visible_tasks so the dashboard's totals match the
    # task list and kanban: include tasks in projects the user can see, not just
    # ones they're personally assigned to or reported.
    from projects.services import visible_projects

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


def _spent_secs(task):
    """Total tracked seconds for a task (summed from its time logs)."""
    return task.actual_seconds


def build_dashboard(user):
    tasks = _task_scope(user)
    projects = Project.objects() if user.role in MANAGEMENT_ROLES else Project.objects(
        __raw__={"$or": [{"manager": user.id}, {"team_members": user.id}]}
    )
    now = utcnow()

    status_counts = {s: tasks.filter(status=s).count() for s in TASK_STATUSES}
    overdue = tasks.filter(
        due_date__lt=now, status__nin=["completed", "rejected"]
    ).count()

    cards = {
        "total_projects": projects.count(),
        "active_projects": projects.filter(status="active").count(),
        "total_tasks": tasks.count(),
        "pending_tasks": tasks.filter(status__nin=["completed", "rejected"]).count(),
        "completed_tasks": status_counts.get("completed", 0),
        "overdue_tasks": overdue,
    }

    # Task details table + total spent time, grouped by status. Work in whole
    # seconds throughout (templates format via secs_to_hms) so summing many
    # tasks never accumulates float-rounding drift.
    task_rows = []
    secs_by_status = {s: 0 for s in TASK_STATUSES}
    total_spent_secs = 0
    for t in tasks.order_by("-created_at"):
        spent = _spent_secs(t)
        total_spent_secs += spent
        secs_by_status[t.status] += spent
        task_rows.append(
            {
                "id": str(t.id),
                "task_id": t.task_id,
                "title": t.title,
                "project": t.project.name if t.project else "—",
                "assignee": t.assigned_to.full_name if t.assigned_to else "Unassigned",
                "status": t.status,
                "status_label": STATUS_LABELS.get(t.status, t.status),
                "priority": t.priority,
                "priority_label": t.priority_label,
                "progress": t.progress,
                "due_date": t.due_date,
                "estimated_secs": int(round((t.estimated_hours or 0) * 3600)),
                "spent_secs": spent,
                "is_overdue": t.is_overdue,
            }
        )

    status_hours = [
        {
            "status": s,
            "label": STATUS_LABELS.get(s, s),
            "count": status_counts.get(s, 0),
            "secs": secs_by_status.get(s, 0),
        }
        for s in TASK_STATUSES
    ]

    # Employee workload (management only): open tasks per assignee.
    workload = []
    if user.role in MANAGEMENT_ROLES:
        for emp in User.objects(status="active"):
            open_count = Task.objects(
                assigned_to=emp, status__nin=["completed", "rejected"]
            ).count()
            done_count = Task.objects(assigned_to=emp, status="completed").count()
            if open_count or done_count:
                workload.append(
                    {
                        "employee": emp.full_name,
                        "open_tasks": open_count,
                        "completed_tasks": done_count,
                    }
                )
        workload.sort(key=lambda x: x["open_tasks"], reverse=True)

    return {
        "cards": cards,
        "tasks": task_rows,
        "status_hours": status_hours,
        "total_spent_secs": total_spent_secs,
        "employee_workload": workload[:15],
    }
