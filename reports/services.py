"""Module 12: Report builders. Each returns (title, columns, rows)."""
import datetime

from mongoengine.queryset.visitor import Q

from accounts.models import Department, PerformanceGoal, User
from core.constants import (
    PERF_KIND_LABELS,
    PERF_STATUS_LABELS,
    PRIORITY_LABELS,
    PROJECT_STATUS_LABELS,
    STATUS_LABELS,
)
from projects.models import Project
from tasks.models import Task, TimeLog


def _fmt(dt):
    return dt.strftime("%Y-%m-%d") if dt else ""


def _hms_secs(total_secs):
    """Convert whole seconds to an HH:MM:SS string (no float rounding loss)."""
    try:
        total_secs = int(total_secs or 0)
    except (TypeError, ValueError):
        return "00:00:00"
    neg = total_secs < 0
    total_secs = abs(total_secs)
    h, rem = divmod(total_secs, 3600)
    m, s = divmod(rem, 60)
    result = f"{h:02d}:{m:02d}:{s:02d}"
    return f"-{result}" if neg else result


def _hms(hours):
    """Convert float hours to HH:MM:SS string."""
    try:
        return _hms_secs(int(round(float(hours or 0) * 3600)))
    except (TypeError, ValueError):
        return "00:00:00"


def _parse_date(val):
    """Parse YYYY-MM-DD string to timezone-aware datetime (start of day UTC)."""
    if not val:
        return None
    try:
        d = datetime.datetime.strptime(val, "%Y-%m-%d")
        return d.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def _parse_date_end(val):
    """Parse YYYY-MM-DD string to end-of-day UTC datetime."""
    if not val:
        return None
    try:
        d = datetime.datetime.strptime(val, "%Y-%m-%d")
        return d.replace(hour=23, minute=59, second=59, tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def task_report(filters=None, user=None):
    filters = filters or {}
    # RBAC: management sees everything; everyone else is scoped to the tasks
    # they're allowed to see (assigned/reported/own-project), mirroring the
    # task list and API. Without this, the report leaked every task.
    from core.constants import MANAGEMENT_ROLES

    if user is not None and user.role not in MANAGEMENT_ROLES:
        from tasks.api_views import visible_tasks
        qs = visible_tasks(user)
    else:
        qs = Task.objects()

    # Text search across title and task_id
    if filters.get("search"):
        s = filters["search"]
        qs = qs.filter(Q(title__icontains=s) | Q(task_id__icontains=s))

    if filters.get("project_id"):
        qs = qs.filter(project=filters["project_id"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("assigned_to"):
        qs = qs.filter(assigned_to=filters["assigned_to"])
    if filters.get("priority"):
        qs = qs.filter(priority=filters["priority"])

    due_from = _parse_date(filters.get("due_date_from"))
    due_to = _parse_date_end(filters.get("due_date_to"))
    if due_from:
        qs = qs.filter(due_date__gte=due_from)
    if due_to:
        qs = qs.filter(due_date__lte=due_to)

    created_from = _parse_date(filters.get("created_from"))
    created_to = _parse_date_end(filters.get("created_to"))
    if created_from:
        qs = qs.filter(created_at__gte=created_from)
    if created_to:
        qs = qs.filter(created_at__lte=created_to)

    try:
        prog_min = int(filters["progress_min"]) if filters.get("progress_min") else None
        prog_max = int(filters["progress_max"]) if filters.get("progress_max") else None
    except (ValueError, TypeError):
        prog_min = prog_max = None
    if prog_min is not None:
        qs = qs.filter(progress__gte=prog_min)
    if prog_max is not None:
        qs = qs.filter(progress__lte=prog_max)

    columns = ["Task ID", "Title", "Project", "Assignee", "Status", "Priority",
               "Progress %", "Due Date", "Created", "Est. Hrs", "Actual Hrs"]
    rows = []
    for t in qs.order_by("-created_at"):
        est_secs = int(round((t.estimated_hours or 0) * 3600))
        rows.append([
            t.task_id, t.title,
            t.project.name if t.project else "",
            t.assigned_to.full_name if t.assigned_to else "Unassigned",
            STATUS_LABELS.get(t.status, t.status),
            PRIORITY_LABELS.get(t.priority, t.priority),
            t.progress, _fmt(t.due_date), _fmt(t.created_at),
            _hms_secs(est_secs), _hms_secs(t.actual_seconds),
        ])
    return "Task Report", columns, rows


def project_report(filters=None, user=None):
    filters = filters or {}
    qs = Project.objects()

    # Text search by project name
    if filters.get("search"):
        qs = qs.filter(name__icontains=filters["search"])

    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("priority"):
        qs = qs.filter(priority=filters["priority"])
    if filters.get("manager_id"):
        qs = qs.filter(manager=filters["manager_id"])

    start_from = _parse_date(filters.get("start_date_from"))
    start_to = _parse_date_end(filters.get("start_date_to"))
    if start_from:
        qs = qs.filter(start_date__gte=start_from)
    if start_to:
        qs = qs.filter(start_date__lte=start_to)

    end_from = _parse_date(filters.get("end_date_from"))
    end_to = _parse_date_end(filters.get("end_date_to"))
    if end_from:
        qs = qs.filter(end_date__gte=end_from)
    if end_to:
        qs = qs.filter(end_date__lte=end_to)

    columns = ["Project", "Status", "Priority", "Manager", "Total Tasks",
               "Completed", "Progress %", "Est. Hrs", "Actual Hrs",
               "Remaining Hrs", "Start", "End"]
    rows = []
    for p in qs.order_by("-created_at"):
        tasks = Task.objects(project=p)
        total = tasks.count()
        done = tasks.filter(status="completed").count()
        est_secs = int(round((p.estimated_hours or 0) * 3600))
        actual_secs = sum(t.actual_seconds for t in tasks)
        rows.append([
            p.name,
            PROJECT_STATUS_LABELS.get(p.status, p.status),
            PRIORITY_LABELS.get(p.priority, p.priority),
            p.manager.full_name if p.manager else "",
            total, done, round(done / total * 100) if total else 0,
            _hms_secs(est_secs), _hms_secs(actual_secs),
            _hms_secs(est_secs - actual_secs),
            _fmt(p.start_date), _fmt(p.end_date),
        ])
    return "Project Report", columns, rows


def employee_report(filters=None, user=None):
    filters = filters or {}
    qs = User.objects()

    # Text search by name or employee ID
    if filters.get("search"):
        s = filters["search"]
        qs = qs.filter(Q(full_name__icontains=s) | Q(employee_id__icontains=s))

    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    else:
        qs = qs.filter(status="active")

    if filters.get("role"):
        qs = qs.filter(role=filters["role"])
    if filters.get("department_id"):
        qs = qs.filter(department=filters["department_id"])

    columns = ["Employee ID", "Name", "Department", "Role", "Status",
               "Open Tasks", "Completed Tasks", "Logged Hours"]
    rows = []
    for u in qs.order_by("full_name"):
        open_t = Task.objects(assigned_to=u, status__nin=["completed", "rejected"]).count()
        done_t = Task.objects(assigned_to=u, status="completed").count()
        secs = sum(t.total_seconds for t in TimeLog.objects(employee=u))
        rows.append([
            u.employee_id, u.full_name,
            u.department.name if u.department else "",
            u.role_label, u.status,
            open_t, done_t,
            _hms_secs(secs),
        ])
    return "Employee Report", columns, rows


def productivity_report(filters=None, user=None):
    filters = filters or {}
    qs = User.objects(status="active")

    # Text search by name
    if filters.get("search"):
        qs = qs.filter(full_name__icontains=filters["search"])

    if filters.get("role"):
        qs = qs.filter(role=filters["role"])
    if filters.get("department_id"):
        qs = qs.filter(department=filters["department_id"])

    columns = ["Employee", "Department", "Completed Tasks", "Logged Hours", "Avg Hrs/Task"]
    rows = []
    for u in qs.order_by("full_name"):
        done_t = Task.objects(assigned_to=u, status="completed").count()
        secs = sum(t.total_seconds for t in TimeLog.objects(employee=u))
        rows.append([
            u.full_name,
            u.department.name if u.department else "",
            done_t, _hms_secs(secs),
            _hms_secs(secs // done_t) if done_t else "00:00:00",
        ])
    rows.sort(key=lambda r: r[2], reverse=True)
    return "Productivity Report", columns, rows


def performance_report(filters=None, user=None):
    """All employees' KRA / KPI goals with advanced filters."""
    filters = filters or {}
    qs = PerformanceGoal.objects()

    # Text search by goal title
    if filters.get("search"):
        qs = qs.filter(title__icontains=filters["search"])

    if filters.get("employee_id"):
        qs = qs.filter(employee=filters["employee_id"])
    if filters.get("kind"):
        qs = qs.filter(kind=filters["kind"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("period"):
        qs = qs.filter(period__icontains=filters["period"])

    # Department filter: fetch matching employee IDs first
    if filters.get("department_id"):
        emp_ids = [u.id for u in User.objects(department=filters["department_id"])]
        qs = qs.filter(employee__in=emp_ids)

    columns = ["Employee ID", "Employee", "Department", "Type", "Title",
               "Target", "Weightage %", "Period", "Status", "Score"]
    rows = []
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

FILTERED_REPORTS = set(REPORTS.keys())


def build(report_type, filters=None, user=None):
    fn = REPORTS.get(report_type)
    if not fn:
        raise ValueError(f"Unknown report type: {report_type}")
    return fn(filters, user=user)
