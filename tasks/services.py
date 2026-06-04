"""Task domain services: id generation, activity logging, realtime board sync."""
import datetime

from core.constants import ACTIVITY_TASK_CREATED
from core.realtime import broadcast, kanban_group
from tasks.models import ActivityLog, Task


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def next_task_id():
    last = Task.objects.order_by("-created_at").first()
    n = Task.objects.count() + 1
    # Best effort sequential; fall back to count if parsing fails.
    if last and last.task_id and last.task_id.startswith("TASK-"):
        try:
            n = max(n, int(last.task_id.split("-")[1]) + 1)
        except (ValueError, IndexError):
            pass
    return f"TASK-{n:05d}"


def log_activity(*, actor, message, verb=ACTIVITY_TASK_CREATED, task=None, project=None):
    return ActivityLog(
        actor=actor,
        message=message,
        verb=verb,
        task=task,
        project=project or (task.project if task else None),
    ).save()


def task_card(task):
    """Compact representation used by the kanban board + WS events."""
    from core.utils import doc_brief

    return {
        "id": str(task.id),
        "task_id": task.task_id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "progress": task.progress,
        "board_order": task.board_order,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "is_overdue": task.is_overdue,
        "assigned_to": doc_brief(task.assigned_to),
        "tags": list(task.tags or []),
        "subtask_count": len(task.subtasks),
        "project_id": str(task.project.id) if task.project else None,
    }


def broadcast_board(project_id, event, task=None, extra=None):
    """Push a kanban event to everyone watching the project board."""
    payload = {"event": event}
    if task is not None:
        payload["task"] = task_card(task)
    if extra:
        payload.update(extra)
    broadcast(kanban_group(str(project_id)), "board_event", payload)
