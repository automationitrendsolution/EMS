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
    return Task.objects(
        __raw__={"$or": [{"assigned_to": user.id}, {"reporter": user.id}]}
    )


def _spent_hours(task):
    """Total tracked hours for a task, summed across all of its time logs."""
    secs = sum(tl.total_seconds for tl in TimeLog.objects(task=task))
    return round(secs / 3600, 2)


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

    # Task details table + total spent hours, calculated (grouped) by status.
    task_rows = []
    hours_by_status = {s: 0.0 for s in TASK_STATUSES}
    total_spent = 0.0
    for t in tasks.order_by("-created_at"):
        spent = _spent_hours(t)
        total_spent += spent
        hours_by_status[t.status] = round(hours_by_status[t.status] + spent, 2)
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
                "progress": t.progress,
                "due_date": t.due_date,
                "estimated_hours": t.estimated_hours or 0,
                "spent_hours": spent,
                "is_overdue": t.is_overdue,
            }
        )

    status_hours = [
        {
            "status": s,
            "label": STATUS_LABELS.get(s, s),
            "count": status_counts.get(s, 0),
            "hours": round(hours_by_status.get(s, 0.0), 2),
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
        "total_spent_hours": round(total_spent, 2),
        "employee_workload": workload[:15],
    }
