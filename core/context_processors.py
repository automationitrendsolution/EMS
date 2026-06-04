def current_user(request):
    user = getattr(request, "current_user", None)
    unread = 0
    api_token = None
    is_management = False
    if user:
        from accounts.auth import make_access_token
        from core.constants import MANAGEMENT_ROLES
        from notifications.models import Notification

        unread = Notification.objects(recipient=user, is_read=False).count()
        # Mint a short-lived access token so frontend JS can call the REST API
        # / open authenticated WebSockets while using session-based pages.
        api_token = make_access_token(user)
        is_management = user.role in MANAGEMENT_ROLES
    return {
        "current_user": user,
        "unread_notifications": unread,
        "api_token": api_token,
        "is_management": is_management,
    }
