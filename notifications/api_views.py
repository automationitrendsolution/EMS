from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.api_helpers import paginate
from core.utils import doc_brief
from notifications.models import Notification


def notif_repr(n):
    return {
        "id": str(n.id),
        "title": n.title,
        "message": n.message,
        "type": n.notif_type,
        "link": n.link,
        "is_read": n.is_read,
        "actor": doc_brief(n.actor),
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@api_view(["GET"])
def list_notifications(request):
    qs = Notification.objects(recipient=request.user)
    if request.query_params.get("unread") == "true":
        qs = qs.filter(is_read=False)
    qs = qs.order_by("-created_at")
    return paginate(request, qs, notif_repr)


@api_view(["GET"])
def unread_count(request):
    return Response(
        {"count": Notification.objects(recipient=request.user, is_read=False).count()}
    )


@api_view(["POST"])
def mark_read(request, pk):
    n = Notification.objects(id=pk, recipient=request.user).first()
    if not n:
        return Response({"detail": "Not found."}, status=404)
    n.is_read = True
    n.save()
    return Response(notif_repr(n))


@api_view(["POST"])
def mark_all_read(request):
    Notification.objects(recipient=request.user, is_read=False).update(set__is_read=True)
    return Response({"detail": "All marked read."})
