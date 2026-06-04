from django.urls import path

from tasks import views

urlpatterns = [
    path("mine/", views.my_tasks, name="my-tasks"),
    path("team/", views.team_tasks, name="team-tasks"),
    path("<str:pk>/", views.task_detail, name="task-detail"),
]
