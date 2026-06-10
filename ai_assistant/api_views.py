from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from ai_assistant import services
from projects.models import Project
from projects.services import can_view_project
from tasks.api_views import get_task_for_user


class AIThrottle(ScopedRateThrottle):
    scope = "ai"


@api_view(["POST"])
@throttle_classes([AIThrottle])
def ai_breakdown(request):
    goal = request.data.get("goal", "").strip()
    if not goal:
        return Response({"detail": "Provide a 'goal'."}, status=400)
    return Response(services.task_breakdown(goal))


@api_view(["POST"])
@throttle_classes([AIThrottle])
def ai_task_summary(request, pk):
    # RBAC: only users who can view the task may request its AI summary.
    task, err = get_task_for_user(request.user, pk)
    if err:
        return err
    return Response(services.task_summary(task))


@api_view(["POST"])
@throttle_classes([AIThrottle])
def ai_project_health(request, pk):
    project = Project.objects(id=pk).first()
    if not project:
        return Response({"detail": "Project not found."}, status=404)
    # RBAC: only users who can view the project may request its AI health check.
    if not can_view_project(request.user, project):
        return Response({"detail": "Forbidden."}, status=403)
    return Response(services.project_health(project))
