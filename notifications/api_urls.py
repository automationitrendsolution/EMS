from django.urls import path

from notifications import api_views as v

urlpatterns = [
    path("", v.list_notifications, name="api-notifications"),
    path("unread-count/", v.unread_count, name="api-notif-unread"),
    path("read-all/", v.mark_all_read, name="api-notif-read-all"),
    path("<str:pk>/read/", v.mark_read, name="api-notif-read"),
]
