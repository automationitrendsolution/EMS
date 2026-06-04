from django.urls import path

from dashboard import api_views as v

urlpatterns = [
    path("stats/", v.dashboard_stats, name="api-dashboard-stats"),
]
