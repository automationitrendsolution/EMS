"""Module 12: Report builders. Each returns (title, columns, rows)."""
from accounts.models import User
from core.constants import STATUS_LABELS
from projects.models import Project
from tasks.models import Task, TimeLog


def _fmt(dt):
    return dt.strftime("%Y-%m-%d") if dt else ""


def task_report(filters=None):
    filters = filters or {}
    qs = Task.objects()
    if filters.get("project_id"):
        qs = qs.filter(project=filters["project_id"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    columns = ["Task ID", "Title", "Project", "Assignee", "Status", "Priority",
               "Progress %", "Due Date", "Est. Hrs", "Actual Hrs"]
    rows = []
    for t in qs.order_by("-created_at"):
        rows.append([
            t.task_id, t.title,
            t.project.name if t.project else "",
            t.assigned_to.full_name if t.assigned_to else "Unassigned",
            STATUS_LABELS.get(t.status, t.status), t.priority,
            t.progress, _fmt(t.due_date), t.estimated_hours, t.actual_hours,
        ])
    return "Task Report", columns, rows


def project_report():
    columns = ["Project", "Status", "Priority", "Manager", "Total Tasks",
               "Completed", "Progress %", "Start", "End"]
    rows = []
    for p in Project.objects().order_by("-created_at"):
        tasks = Task.objects(project=p)
        total = tasks.count()
        done = tasks.filter(status="completed").count()
        rows.append([
            p.name, p.status, p.priority,
            p.manager.full_name if p.manager else "",
            total, done, round(done / total * 100) if total else 0,
            _fmt(p.start_date), _fmt(p.end_date),
        ])
    return "Project Report", columns, rows


def employee_report():
    columns = ["Employee ID", "Name", "Role", "Open Tasks", "Completed Tasks",
               "Logged Hours"]
    rows = []
    for u in User.objects(status="active").order_by("full_name"):
        open_t = Task.objects(assigned_to=u, status__nin=["completed", "rejected"]).count()
        done_t = Task.objects(assigned_to=u, status="completed").count()
        secs = sum(t.total_seconds for t in TimeLog.objects(employee=u))
        rows.append([
            u.employee_id, u.full_name, u.role_label, open_t, done_t,
            round(secs / 3600, 2),
        ])
    return "Employee Report", columns, rows


def productivity_report():
    columns = ["Employee", "Completed Tasks", "Logged Hours", "Avg Hrs/Task"]
    rows = []
    for u in User.objects(status="active").order_by("full_name"):
        done_t = Task.objects(assigned_to=u, status="completed").count()
        secs = sum(t.total_seconds for t in TimeLog.objects(employee=u))
        hours = round(secs / 3600, 2)
        rows.append([
            u.full_name, done_t, hours,
            round(hours / done_t, 2) if done_t else 0,
        ])
    rows.sort(key=lambda r: r[1], reverse=True)
    return "Productivity Report", columns, rows


REPORTS = {
    "task": task_report,
    "project": project_report,
    "employee": employee_report,
    "productivity": productivity_report,
}


def build(report_type, filters=None):
    fn = REPORTS.get(report_type)
    if not fn:
        raise ValueError(f"Unknown report type: {report_type}")
    if report_type == "task":
        return fn(filters)
    return fn()
