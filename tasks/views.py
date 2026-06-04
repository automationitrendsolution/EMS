from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.models import User
from core.constants import MANAGEMENT_ROLES, PRIORITIES, TASK_STATUSES
from core.decorators import login_required
from projects.models import Project
from projects.services import can_view_project, visible_projects
from tasks.api_views import get_task_for_user, visible_tasks
from tasks.models import ActivityLog, Comment, Task, TimeLog


@login_required
def my_tasks(request):
    tasks = list(
        Task.objects(assigned_to=request.current_user).order_by("-created_at")
    )
    return render(
        request,
        "tasks/my_tasks.html",
        {"active": "my_tasks", "tasks": tasks, "statuses": TASK_STATUSES},
    )


@login_required
def team_tasks(request):
    qs = visible_tasks(request.current_user)
    status_f = request.GET.get("status")
    if status_f:
        qs = qs.filter(status=status_f)
    search = request.GET.get("search")
    if search:
        qs = qs.filter(title__icontains=search)
    tasks = list(qs.order_by("-created_at").limit(200))
    return render(
        request,
        "tasks/team_tasks.html",
        {
            "active": "team_tasks",
            "tasks": tasks,
            "statuses": TASK_STATUSES,
            "search": search or "",
            "status_f": status_f or "",
            "projects": list(visible_projects(request.current_user)),
            "employees": list(User.objects(status="active")),
            "priorities": PRIORITIES,
            "can_manage": request.current_user.role in MANAGEMENT_ROLES,
        },
    )


@login_required
def task_detail(request, pk):
    task, err = get_task_for_user(request.current_user, pk)
    if err is not None:
        messages.error(request, "Task not available.")
        return redirect("/tasks/mine/")
    comments = list(Comment.objects(task=task).order_by("created_at"))
    activity = list(ActivityLog.objects(task=task).order_by("-created_at").limit(50))
    timelogs = list(TimeLog.objects(task=task).order_by("-created_at"))
    total_secs = sum(t.total_seconds for t in timelogs)

    # Current user's active (not yet stopped) timer, so the page can resume the
    # live ticking display on load. Running -> still counting; paused -> frozen.
    active_log = (
        TimeLog.objects(task=task, employee=request.current_user, end_time=None)
        .order_by("-created_at")
        .first()
    )
    active_timer = None
    if active_log:
        active_timer = {
            "elapsed": active_log.total_seconds,
            "is_running": active_log.is_running,
        }

    # A task may be deleted by management or by its reporter (mirrors the API).
    me = request.current_user
    can_delete_task = me.role in MANAGEMENT_ROLES or (
        task.reporter and str(task.reporter.id) == str(me.id)
    )
    return render(
        request,
        "tasks/detail.html",
        {
            "active": "my_tasks",
            "task": task,
            "comments": comments,
            "activity": activity,
            "timelogs": timelogs,
            "total_hours": round(total_secs / 3600, 2),
            "active_timer": active_timer,
            "can_delete_task": can_delete_task,
            "statuses": TASK_STATUSES,
            "priorities": PRIORITIES,
            "employees": list(User.objects(status="active")),
        },
    )
