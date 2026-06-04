from django.urls import path

from projects import api_views as v

urlpatterns = [
    path("", v.ProjectListCreateView.as_view(), name="api-projects"),
    path("<str:pk>/", v.ProjectDetailView.as_view(), name="api-project"),
    path("<str:pk>/archive/", v.ProjectArchiveView.as_view(), name="api-project-archive"),
]
