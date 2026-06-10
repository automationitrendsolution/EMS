from rest_framework import serializers

from core.constants import PRIORITIES, TASK_STATUSES
from core.utils import doc_brief


def subtask_repr(s):
    return {
        "sid": s.sid,
        "title": s.title,
        "is_done": s.is_done,
        "assigned_to": doc_brief(s.assigned_to),
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }


def attachment_repr(a):
    return {
        "id": str(a.id),
        "original_name": a.original_name,
        "url": a.url,
        "size": a.size,
        "content_type": a.content_type,
        "uploaded_by": doc_brief(a.uploaded_by),
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def comment_repr(c):
    return {
        "id": str(c.id),
        "task_id": str(c.task.id) if c.task else None,
        "author": doc_brief(c.author),
        "body": c.body,
        "mentions": [doc_brief(m) for m in c.mentions],
        "attachments": [attachment_repr(a) for a in c.attachments],
        "is_edited": c.is_edited,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def timelog_repr(t):
    return {
        "id": str(t.id),
        "task": str(t.task.id) if t.task else None,
        "employee": doc_brief(t.employee),
        "start_time": t.start_time.isoformat() if t.start_time else None,
        "end_time": t.end_time.isoformat() if t.end_time else None,
        "is_running": t.is_running,
        "total_seconds": t.total_seconds,
        "note": t.note,
    }


def activity_repr(a):
    return {
        "id": str(a.id),
        "actor": doc_brief(a.actor),
        "verb": a.verb,
        "message": a.message,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def task_repr(t, full=False):
    data = {
        "id": str(t.id),
        "task_id": t.task_id,
        "title": t.title,
        "status": t.status,
        "priority": t.priority,
        "progress": t.progress,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "is_overdue": t.is_overdue,
        "project": {"id": str(t.project.id), "name": t.project.name} if t.project else None,
        "assigned_to": doc_brief(t.assigned_to),
        "reporter": doc_brief(t.reporter),
        "tags": list(t.tags or []),
        "estimated_hours": t.estimated_hours,
        "actual_hours": t.actual_hours,
        "board_order": t.board_order,
        "subtask_count": len(t.subtasks),
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
    if full:
        data.update(
            description=t.description,
            subtasks=[subtask_repr(s) for s in t.subtasks],
            attachments=[attachment_repr(a) for a in t.attachments],
        )
    return data


class TaskWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=300)
    description = serializers.CharField(required=False, allow_blank=True)
    project_id = serializers.CharField()
    assigned_to_id = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=PRIORITIES, default="medium")
    status = serializers.ChoiceField(choices=TASK_STATUSES, default="todo")
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    estimated_hours = serializers.FloatField(required=False, default=0)
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class TaskUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    assigned_to_id = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=PRIORITIES, required=False)
    status = serializers.ChoiceField(choices=TASK_STATUSES, required=False)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    estimated_hours = serializers.FloatField(required=False)
    # NOTE: actual_hours is intentionally NOT writable here — it is derived from
    # time logs (and the management-only override endpoint). Letting clients set
    # it directly is what allowed it to diverge from the tracked time.
    tags = serializers.ListField(child=serializers.CharField(), required=False)


class BulkAssignSerializer(serializers.Serializer):
    task_ids = serializers.ListField(child=serializers.CharField())
    assigned_to_id = serializers.CharField()


class BulkStatusSerializer(serializers.Serializer):
    task_ids = serializers.ListField(child=serializers.CharField())
    status = serializers.ChoiceField(choices=TASK_STATUSES)


class SubtaskSerializer(serializers.Serializer):
    title = serializers.CharField()
    assigned_to_id = serializers.CharField(required=False, allow_blank=True)


class CommentSerializer(serializers.Serializer):
    body = serializers.CharField()


class MoveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TASK_STATUSES)
    board_order = serializers.IntegerField(required=False, default=0)
