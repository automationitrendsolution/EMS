from django.urls import path

from ai_assistant import api_views as v

urlpatterns = [
    path("breakdown/", v.ai_breakdown, name="api-ai-breakdown"),
    path("tasks/<str:pk>/summary/", v.ai_task_summary, name="api-ai-summary"),
    path("projects/<str:pk>/health/", v.ai_project_health, name="api-ai-health"),
]
