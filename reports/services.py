"""Module 12: Report builders. Each returns (title, columns, rows)."""
from accounts.models import PerformanceGoal, User
from core.constants import (
    PERF_KIND_LABELS,
    PERF_STATUS_LABELS,
    STATUS_LABELS,
)
from projects.models import Project
from tasks.models import Task, TimeLog


def _fmt(dt):
    return dt.strftime("%Y-%m-%d") if dt else ""


def _hms(hours):
    """Convert float hours to HH:MM:SS string."""
    try:
        total_secs = int(float(hours or 0) * 3600)
    except (TypeError, ValueError):
        return "00:00:00"
    neg = total_secs < 0
    total_secs = abs(total_secs)
    h, rem = divmod(total_secs, 3600)
    m, s = divmod(rem, 60)
    result = f"{h:02d}:{m:02d}:{s:02d}"
    return f"-{result}" if neg else result


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
            t.progress, _fmt(t.due_date), t.estimated_hours, _hms(t.actual_hours),
        ])
    return "Task Report", columns, rows


def project_report():
    columns = ["Project", "Status", "Priority", "Manager", "Total Tasks",
               "Completed", "Progress %", "Est. Hrs", "Actual Hrs",
               "Remaining Hrs", "Start", "End"]
    rows = []
    for p in Project.objects().order_by("-created_at"):
        tasks = Task.objects(project=p)
        total = tasks.count()
        done = tasks.filter(status="completed").count()
        est = p.estimated_hours or 0
        # Actual hours are auto-calculated from the project's task time logs.
        actual = round(tasks.sum("actual_hours") or 0, 2)
        rows.append([
            p.name, p.status, p.priority,
            p.manager.full_name if p.manager else "",
            total, done, round(done / total * 100) if total else 0,
            est, _hms(actual), _hms(est - actual),
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
            _hms(secs / 3600),
        ])
    return "Employee Report", columns, rows


def productivity_report():
    columns = ["Employee", "Completed Tasks", "Logged Hours", "Avg Hrs/Task"]
    rows = []
    for u in User.objects(status="active").order_by("full_name"):
        done_t = Task.objects(assigned_to=u, status="completed").count()
        secs = sum(t.total_seconds for t in TimeLog.objects(employee=u))
        hours = secs / 3600
        rows.append([
            u.full_name, done_t, _hms(hours),
            _hms(hours / done_t) if done_t else "00:00:00",
        ])
    rows.sort(key=lambda r: r[1], reverse=True)
    return "Productivity Report", columns, rows


def performance_report(filters=None):
    """All employees' KRA / KPI goals. Optional filters: employee_id, kind,
    status."""
    filters = filters or {}
    qs = PerformanceGoal.objects()
    if filters.get("employee_id"):
        qs = qs.filter(employee=filters["employee_id"])
    if filters.get("kind"):
        qs = qs.filter(kind=filters["kind"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    columns = ["Employee ID", "Employee", "Department", "Type", "Title",
               "Target", "Weightage %", "Period", "Status", "Score"]
    rows = []
    # Group by employee name, then KRA before KPI, for a readable layout.
    for g in qs.order_by("kind"):
        emp = g.employee
        rows.append([
            emp.employee_id if emp else "",
            emp.full_name if emp else "(deleted)",
            emp.department.name if emp and emp.department else "",
            PERF_KIND_LABELS.get(g.kind, g.kind),
            g.title,
            g.target or "",
            g.weightage or 0,
            g.period or "",
            PERF_STATUS_LABELS.get(g.status, g.status),
            g.score or 0,
        ])
    rows.sort(key=lambda r: (r[1], r[3]))
    return "Performance (KRA/KPI) Report", columns, rows


REPORTS = {
    "task": task_report,
    "project": project_report,
    "employee": employee_report,
    "productivity": productivity_report,
    "performance": performance_report,
}

# Reports that accept a ``filters`` argument.
FILTERED_REPORTS = {"task", "performance"}


def build(report_type, filters=None):
    fn = REPORTS.get(report_type)
    if not fn:
        raise ValueError(f"Unknown report type: {report_type}")
    if report_type in FILTERED_REPORTS:
        return fn(filters)
    return fn()
