from django.urls import re_path

from notifications.consumers import NotificationConsumer
from tasks.consumers import KanbanConsumer

websocket_urlpatterns = [
    re_path(r"^ws/kanban/(?P<project_id>[0-9a-fA-F]{24})/$", KanbanConsumer.as_asgi()),
    re_path(r"^ws/notifications/$", NotificationConsumer.as_asgi()),
]
