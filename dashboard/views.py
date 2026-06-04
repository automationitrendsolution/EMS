from django.shortcuts import render

from core.decorators import login_required
from dashboard.services import build_dashboard


@login_required
def dashboard_page(request):
    data = build_dashboard(request.current_user)
    return render(
        request,
        "dashboard/index.html",
        {"active": "dashboard", "data": data},
    )
