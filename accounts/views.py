"""Server-rendered auth + employee management pages."""
import datetime

from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.models import (
    Department,
    Designation,
    EmployeeError,
    PerformanceGoal,
    Team,
    User,
)
from accounts.services import create_user
from core.constants import (
    ERROR_SEVERITIES,
    ERROR_SEVERITY_LABELS,
    ERROR_STATUS_LABELS,
    ERROR_STATUSES,
    MANAGEMENT_ROLES,
    PERF_KINDS,
    PERF_KIND_FULL_LABELS,
    PERF_KIND_LABELS,
    PERF_STATUS_LABELS,
    PERF_STATUSES,
    ROLE_LABELS,
    ROLE_SUPER_ADMIN,
    ROLES,
)
from core.decorators import login_required, roles_required
from core.utils import save_upload


def login_page(request):
    if getattr(request, "current_user", None):
        return redirect("/dashboard/")
    if request.method == "POST":
        email = (request.POST.get("email") or "").lower().strip()
        password = request.POST.get("password") or ""
        user = User.objects(email=email).first()
        if user and user.check_password(password) and user.status == "active":
            request.session["user_id"] = str(user.id)
            user.last_login = datetime.datetime.now(datetime.timezone.utc)
            user.save()
            nxt = request.GET.get("next") or "/dashboard/"
            return redirect(nxt)
        messages.error(request, "Invalid email or password.")
    return render(request, "auth/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("/login/")


@login_required
def profile_page(request):
    user = request.current_user
    if request.method == "POST":
        user.full_name = request.POST.get("full_name", user.full_name)
        user.phone = request.POST.get("phone", user.phone)
        new_pw = request.POST.get("new_password")
        if new_pw:
            user.set_password(new_pw)
        if request.FILES.get("profile_image"):
            try:
                path, *_ = save_upload(request.FILES["profile_image"], "avatars")
                user.profile_image = path
            except ValueError as e:
                messages.error(request, str(e))
        user.save()
        messages.success(request, "Profile updated.")
        return redirect("/profile/")
    return render(request, "auth/profile.html", {"active": "profile", "profile": user})


@login_required
@roles_required(*MANAGEMENT_ROLES)
def departments_page(request):
    departments = list(Department.objects().order_by("name"))
    return render(request, "departments/list.html", {
        "active": "departments",
        "departments": departments,
    })


@login_required
@roles_required(*MANAGEMENT_ROLES)
def department_create(request):
    if request.method != "POST":
        return redirect("/departments/")
    name = (request.POST.get("name") or "").strip()
    description = (request.POST.get("description") or "").strip()
    if not name:
        messages.error(request, "Department name is required.")
        return redirect("/departments/")
    if Department.objects(name=name).first():
        messages.error(request, "A department with that name already exists.")
        return redirect("/departments/")
    Department(name=name, description=description).save()
    messages.success(request, f"Department '{name}' created.")
    return redirect("/departments/")


@login_required
@roles_required(*MANAGEMENT_ROLES)
def department_edit(request, pk):
    if request.method != "POST":
        return redirect("/departments/")
    dept = Department.objects(id=pk).first()
    if not dept:
        messages.error(request, "Department not found.")
        return redirect("/departments/")
    name = (request.POST.get("name") or "").strip()
    description = (request.POST.get("description") or "").strip()
    if not name:
        messages.error(request, "Department name is required.")
        return redirect("/departments/")
    existing = Department.objects(name=name).first()
    if existing and str(existing.id) != pk:
        messages.error(request, "A department with that name already exists.")
        return redirect("/departments/")
    dept.name = name
    dept.description = description
    dept.save()
    messages.success(request, f"Department '{name}' updated.")
    return redirect("/departments/")


@login_required
@roles_required(*MANAGEMENT_ROLES)
def employees_page(request):
    search = request.GET.get("search", "")
    qs = User.objects()
    if search:
        qs = qs.filter(full_name__icontains=search)
    employees = list(qs.order_by("full_name"))
    return render(
        request,
        "employees/list.html",
        {
            "active": "employees",
            "employees": employees,
            "search": search,
            "departments": list(Department.objects()),
            "designations": list(Designation.objects()),
            "teams": list(Team.objects()),
            "roles": [(r, ROLE_LABELS[r]) for r in ROLES],
        },
    )


@login_required
@roles_required(*MANAGEMENT_ROLES)
def employee_create(request):
    if request.method != "POST":
        return redirect("/employees/")
    email = (request.POST.get("email") or "").lower().strip()
    if User.objects(email=email).first():
        messages.error(request, "Email already exists.")
        return redirect("/employees/")
    try:
        create_user(
            full_name=request.POST.get("full_name"),
            email=email,
            password=request.POST.get("password") or "changeme123",
            role=request.POST.get("role", "employee"),
            phone=request.POST.get("phone"),
            department=Department.objects(id=request.POST.get("department_id")).first()
            if request.POST.get("department_id")
            else None,
            designation=Designation.objects(
                id=request.POST.get("designation_id")
            ).first()
            if request.POST.get("designation_id")
            else None,
            team=Team.objects(id=request.POST.get("team_id")).first()
            if request.POST.get("team_id")
            else None,
        )
        messages.success(request, "Employee created.")
    except Exception as e:  # noqa
        messages.error(request, f"Could not create employee: {e}")
    return redirect("/employees/")


@login_required
@roles_required(*MANAGEMENT_ROLES)
def employee_edit(request, pk):
    if request.method != "POST":
        return redirect("/employees/")
    employee = User.objects(id=pk).first()
    if not employee:
        messages.error(request, "Employee not found.")
        return redirect("/employees/")
    full_name = (request.POST.get("full_name") or "").strip()
    email = (request.POST.get("email") or "").lower().strip()
    if not full_name or not email:
        messages.error(request, "Name and email are required.")
        return redirect("/employees/")
    existing = User.objects(email=email).first()
    if existing and str(existing.id) != pk:
        messages.error(request, "That email is already used by another employee.")
        return redirect("/employees/")
    employee.full_name = full_name
    employee.email = email
    employee.phone = (request.POST.get("phone") or "").strip() or None
    employee.role = request.POST.get("role") or employee.role
    employee.department = (
        Department.objects(id=request.POST.get("department_id")).first()
        if request.POST.get("department_id")
        else None
    )
    employee.designation = (
        Designation.objects(id=request.POST.get("designation_id")).first()
        if request.POST.get("designation_id")
        else None
    )
    employee.team = (
        Team.objects(id=request.POST.get("team_id")).first()
        if request.POST.get("team_id")
        else None
    )
    new_password = (request.POST.get("new_password") or "").strip()
    if new_password:
        if len(new_password) < 6:
            messages.error(request, "New password must be at least 6 characters.")
            return redirect("/employees/")
        employee.set_password(new_password)
    employee.save()
    messages.success(request, f"Employee '{full_name}' updated.")
    return redirect("/employees/")


# ---------------------------------------------------------------------------
# Performance: KRA (Key Result Area) / KPI (Key Performance Indicator)
# ---------------------------------------------------------------------------
def _performance_context(employee, *, can_edit, self_view):
    """Build the shared template context for a performance page."""
    goals = list(
        PerformanceGoal.objects(employee=employee.id).order_by("kind", "-created_at")
    )
    kras = [g for g in goals if g.kind == "kra"]
    kpis = [g for g in goals if g.kind == "kpi"]

    # Weighted average score: use weightage as weights; fall back to simple average.
    total_weight = sum(g.weightage or 0 for g in goals)
    if total_weight > 0:
        weighted_score = sum((g.score or 0) * (g.weightage or 0) for g in goals) / total_weight
    elif goals:
        weighted_score = sum(g.score or 0 for g in goals) / len(goals)
    else:
        weighted_score = 0
    avg_score = round(weighted_score, 1)

    kra_weight_total = sum(g.weightage or 0 for g in kras)
    kpi_weight_total = sum(g.weightage or 0 for g in kpis)

    return {
        "active": "performance" if self_view else "employees",
        "employee": employee,
        "self_view": self_view,
        "can_edit": can_edit,
        "kras": kras,
        "kpis": kpis,
        "goal_count": len(goals),
        "avg_score": avg_score,
        "kra_weight_total": kra_weight_total,
        "kpi_weight_total": kpi_weight_total,
        "kinds": [(k, PERF_KIND_LABELS[k], PERF_KIND_FULL_LABELS[k]) for k in PERF_KINDS],
        "statuses": [(s, PERF_STATUS_LABELS[s]) for s in PERF_STATUSES],
    }


@login_required
@roles_required(ROLE_SUPER_ADMIN)
def employee_errors_page(request):
    """Super-admin-only log of employee errors, with filters."""
    import datetime

    def _parse(val, *, end=False):
        if not val:
            return None
        try:
            d = datetime.datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            return None
        if end:
            d = d.replace(hour=23, minute=59, second=59)
        return d.replace(tzinfo=datetime.timezone.utc)

    search = request.GET.get("search", "")
    employee_id = request.GET.get("employee_id", "")
    severity = request.GET.get("severity", "")
    status_f = request.GET.get("status", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    qs = EmployeeError.objects()
    if search:
        qs = qs.filter(title__icontains=search)
    if employee_id:
        qs = qs.filter(employee=employee_id)
    if severity:
        qs = qs.filter(severity=severity)
    if status_f:
        qs = qs.filter(status=status_f)
    df = _parse(date_from)
    dt = _parse(date_to, end=True)
    if df:
        qs = qs.filter(created_at__gte=df)
    if dt:
        qs = qs.filter(created_at__lte=dt)

    errors = list(qs.order_by("-created_at"))
    return render(
        request,
        "employees/errors.html",
        {
            "active": "employee_errors",
            "errors": errors,
            "employees": list(User.objects(status="active").order_by("full_name")),
            "severities": [(s, ERROR_SEVERITY_LABELS[s]) for s in ERROR_SEVERITIES],
            "statuses": [(s, ERROR_STATUS_LABELS[s]) for s in ERROR_STATUSES],
            "filters": {
                "search": search,
                "employee_id": employee_id,
                "severity": severity,
                "status": status_f,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


@login_required
def my_performance_page(request):
    """The logged-in employee's own KRAs / KPIs (read-only definitions)."""
    ctx = _performance_context(
        request.current_user,
        can_edit=request.current_user.role in MANAGEMENT_ROLES,
        self_view=True,
    )
    return render(request, "performance/list.html", ctx)


@login_required
@roles_required(*MANAGEMENT_ROLES)
def employee_performance_page(request, pk):
    """Management view of a specific employee's KRAs / KPIs (full edit)."""
    employee = User.objects(id=pk).first()
    if not employee:
        messages.error(request, "Employee not found.")
        return redirect("/employees/")
    ctx = _performance_context(employee, can_edit=True, self_view=False)
    return render(request, "performance/list.html", ctx)
