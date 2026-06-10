from django.urls import path

from tasks import api_views as v

urlpatterns = [
    # tasks
    path("tasks/", v.TaskListCreateView.as_view(), name="api-tasks"),
    path("tasks/bulk-assign/", v.bulk_assign, name="api-bulk-assign"),
    path("tasks/bulk-status/", v.bulk_status, name="api-bulk-status"),
    path("tasks/<str:pk>/", v.TaskDetailView.as_view(), name="api-task"),
    path("tasks/<str:pk>/assign/", v.assign_task, name="api-task-assign"),
    path("tasks/<str:pk>/clone/", v.clone_task, name="api-task-clone"),
    path("tasks/<str:pk>/move/", v.move_task, name="api-task-move"),
    # subtasks
    path("tasks/<str:pk>/subtasks/", v.add_subtask, name="api-subtask-add"),
    path("tasks/<str:pk>/subtasks/<str:sid>/toggle/", v.toggle_subtask, name="api-subtask-toggle"),
    path("tasks/<str:pk>/subtasks/<str:sid>/", v.delete_subtask, name="api-subtask-delete"),
    # comments
    path("tasks/<str:pk>/comments/", v.CommentListCreateView.as_view(), name="api-comments"),
    path("tasks/<str:pk>/comments/<str:comment_id>/", v.CommentDetailView.as_view(), name="api-comment"),
    # attachments
    path("tasks/<str:pk>/attachments/", v.upload_attachment, name="api-attachment-upload"),
    path("tasks/<str:pk>/attachments/<str:attachment_id>/", v.delete_attachment, name="api-attachment-delete"),
    # time tracking
    path("tasks/<str:pk>/timer/start/", v.timer_start, name="api-timer-start"),
    path("tasks/<str:pk>/timer/pause/", v.timer_pause, name="api-timer-pause"),
    path("tasks/<str:pk>/timer/resume/", v.timer_resume, name="api-timer-resume"),
    path("tasks/<str:pk>/timer/stop/", v.timer_stop, name="api-timer-stop"),
    path("tasks/<str:pk>/timelogs/", v.task_timelogs, name="api-timelogs"),
    path("tasks/<str:pk>/actual-hours/", v.set_actual_hours, name="api-actual-hours"),
    # activity
    path("tasks/<str:pk>/activity/", v.task_activity, name="api-task-activity"),
    # kanban
    path("kanban/<str:project_id>/", v.kanban_board, name="api-kanban"),
]
