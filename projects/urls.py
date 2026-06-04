from django.urls import path

from projects import views

urlpatterns = [
    path("", views.project_list, name="projects"),
    path("<str:pk>/", views.project_detail, name="project-detail"),
    path("<str:pk>/board/", views.project_board, name="project-board"),
]
