from django.shortcuts import render

from core.decorators import login_required
from notifications.models import Notification


@login_required
def notifications_page(request):
    notifs = list(
        Notification.objects(recipient=request.current_user).order_by("-created_at").limit(100)
    )
    return render(
        request,
        "notifications/list.html",
        {"active": "notifications", "notifications": notifs},
    )
