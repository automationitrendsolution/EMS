from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.models import User
from core.constants import MANAGEMENT_ROLES, PRIORITIES, PROJECT_STATUSES
from core.decorators import login_required
from projects.api_views import project_stats
from projects.models import Project
from projects.services import can_view_project, visible_projects
from tasks.models import Task


@login_required
def project_list(request):
    qs = visible_projects(request.current_user)
    search = request.GET.get("search", "")
    if search:
        qs = qs.filter(name__icontains=search)
    status_f = request.GET.get("status")
    if status_f:
        qs = qs.filter(status=status_f)
    projects = []
    for p in qs.order_by("-created_at"):
        projects.append({"obj": p, "stats": project_stats(p)})
    return render(
        request,
        "projects/list.html",
        {
            "active": "projects",
            "projects": projects,
            "search": search,
            "statuses": PROJECT_STATUSES,
            "priorities": PRIORITIES,
            "managers": list(User.objects(status="active")),
            "employees": list(User.objects(status="active")),
            "can_manage": request.current_user.role in MANAGEMENT_ROLES,
        },
    )


@login_required
def project_detail(request, pk):
    project = Project.objects(id=pk).first()
    if not project:
        messages.error(request, "Project not found.")
        return redirect("/projects/")
    if not can_view_project(request.current_user, project):
        messages.error(request, "You cannot view that project.")
        return redirect("/projects/")
    tasks = list(Task.objects(project=project).order_by("-created_at"))
    return render(
        request,
        "projects/detail.html",
        {
            "active": "projects",
            "project": project,
            "stats": project_stats(project),
            "tasks": tasks,
            "employees": list(User.objects(status="active")),
            "priorities": PRIORITIES,
            "can_manage": request.current_user.role in MANAGEMENT_ROLES,
        },
    )


@login_required
def project_board(request, pk):
    project = Project.objects(id=pk).first()
    if not project or not can_view_project(request.current_user, project):
        messages.error(request, "Project not available.")
        return redirect("/projects/")
    return render(
        request,
        "projects/board.html",
        {
            "active": "projects",
            "project": project,
            "employees": list(User.objects(status="active")),
        },
    )
