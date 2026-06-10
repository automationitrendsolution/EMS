from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts.models import Department, PerformanceGoal, User
from core.constants import (
    MANAGEMENT_ROLES,
    PERF_KIND_LABELS,
    PERF_STATUS_LABELS,
    PRIORITIES,
    PROJECT_STATUSES,
    ROLE_LABELS,
    ROLES,
    STATUS_LABELS,
    TASK_STATUSES,
)
from projects.models import Project
from reports import services
from reports.exporters import export
from tasks.models import Task


@api_view(["GET"])
def filter_options(request):
    """Return all dropdown data needed to populate report filter panels."""
    # Projects
    projects = [{"id": str(p.id), "name": p.name}
                for p in Project.objects().order_by("name")]

    # Employees (active)
    employees = [{"id": str(u.id), "name": u.full_name}
                 for u in User.objects(status="active").order_by("full_name")]

    # All employees for name-search dropdowns (value = full_name for icontains match)
    employee_names = [{"value": u.full_name, "label": u.full_name}
                      for u in User.objects(status="active").order_by("full_name")]

    # Departments
    departments = [{"id": str(d.id), "name": d.name}
                   for d in Department.objects().order_by("name")]

    # Managers (management roles only)
    managers = [{"id": str(u.id), "name": u.full_name}
                for u in User.objects(
                    status="active", role__in=MANAGEMENT_ROLES
                ).order_by("full_name")]

    # Tasks (for task report name-search dropdown)
    tasks = [
        {"value": t.title, "label": f"{t.task_id}: {t.title}"}
        for t in Task.objects().order_by("task_id").only("task_id", "title")
    ]

    # Project names (for project report name-search dropdown)
    project_names = [{"value": p["name"], "label": p["name"]} for p in projects]

    # Performance goal titles (distinct)
    _goal_titles = sorted({
        g.title for g in PerformanceGoal.objects().only("title") if g.title
    })
    goal_titles = [{"value": t, "label": t} for t in _goal_titles]

    # Performance periods (distinct, sorted)
    _periods = sorted({
        g.period for g in PerformanceGoal.objects().only("period") if g.period
    })
    periods = [{"value": p, "label": p} for p in _periods]

    return Response({
        "projects": projects,
        "project_names": project_names,
        "employees": employees,
        "employee_names": employee_names,
        "departments": departments,
        "managers": managers,
        "tasks": tasks,
        "goal_titles": goal_titles,
        "periods": periods,
        "priorities": [{"value": p, "label": p.capitalize()} for p in PRIORITIES],
        "task_statuses": [{"value": k, "label": v} for k, v in STATUS_LABELS.items()
                          if k in TASK_STATUSES],
        "project_statuses": [{"value": s, "label": s.replace("_", " ").title()}
                             for s in PROJECT_STATUSES],
        "employee_statuses": [
            {"value": "active", "label": "Active"},
            {"value": "inactive", "label": "Inactive"},
            {"value": "suspended", "label": "Suspended"},
        ],
        "roles": [{"value": r, "label": ROLE_LABELS[r]} for r in ROLES],
        "perf_kinds": [{"value": k, "label": v} for k, v in PERF_KIND_LABELS.items()],
        "perf_statuses": [{"value": k, "label": v} for k, v in PERF_STATUS_LABELS.items()],
    })


@api_view(["GET"])
def report_data(request, report_type):
    """Return report rows as JSON (for on-screen tables)."""
    if request.user.role not in MANAGEMENT_ROLES and report_type != "task":
        return Response({"detail": "Forbidden."}, status=403)
    try:
        title, columns, rows = services.build(
            report_type, filters=request.query_params
        )
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    return Response({"title": title, "columns": columns, "rows": rows})


@api_view(["GET"])
def report_export(request, report_type, fmt):
    if request.user.role not in MANAGEMENT_ROLES and report_type != "task":
        return Response({"detail": "Forbidden."}, status=403)
    try:
        title, columns, rows = services.build(
            report_type, filters=request.query_params
        )
        return export(fmt, title, columns, rows)
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
