from rest_framework.decorators import api_view
from rest_framework.response import Response

from dashboard.services import build_dashboard


@api_view(["GET"])
def dashboard_stats(request):
    return Response(build_dashboard(request.user))
