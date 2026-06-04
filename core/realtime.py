"""Helpers to push messages onto Channels groups from sync code."""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def broadcast(group, event_type, payload):
    """Best-effort realtime push. A broker outage must not break the request."""
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(group, {"type": event_type, "payload": payload})
    except Exception as exc:  # pragma: no cover - depends on broker availability
        logger.warning("Realtime broadcast to %s failed: %s", group, exc)


def kanban_group(project_id):
    return f"kanban_{project_id}"


def user_group(user_id):
    return f"user_{user_id}"
