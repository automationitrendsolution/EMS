from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="iTrendTASKS API",
        default_version="v1",
        description="Employee Task & Project Management REST API",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # ---- REST API ----
    path("api/v1/", include("config.api_urls")),
    # ---- Swagger / Redoc ----
    path("api/docs/", schema_view.with_ui("swagger", cache_timeout=0), name="swagger"),
    path("api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="redoc"),
    path(
        "api/swagger.json",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    # ---- Server-rendered frontend ----
    path("", include("core.urls")),
    path("", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("projects/", include("projects.urls")),
    path("tasks/", include("tasks.urls")),
    path("reports/", include("reports.urls")),
    path("notifications/", include("notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
