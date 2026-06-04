"""Server-rendered auth + employee management pages."""
import datetime

from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.models import Department, Designation, Team, User
from accounts.services import create_user
from core.constants import MANAGEMENT_ROLES, ROLE_LABELS, ROLES
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
