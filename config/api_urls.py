"""All REST API routes, mounted under /api/v1/."""
from django.urls import include, path

urlpatterns = [
    path("auth/", include("accounts.api_urls")),
    path("projects/", include("projects.api_urls")),
    path("", include("tasks.api_urls")),
    path("notifications/", include("notifications.api_urls")),
    path("reports/", include("reports.api_urls")),
    path("ai/", include("ai_assistant.api_urls")),
    path("dashboard/", include("dashboard.api_urls")),
]
