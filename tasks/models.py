"""Modules 3,4,6,7,8,9: Tasks, Subtasks, Comments, Attachments, Time, Activity."""
import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    FloatField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)

from accounts.models import User
from core.constants import (
    ACTIVITY_TASK_CREATED,
    PRIORITIES,
    TASK_STATUSES,
)
from projects.models import Project


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Module 7: Attachment (shared by projects, tasks, comments)
# ---------------------------------------------------------------------------
class Attachment(Document):
    meta = {"collection": "attachments", "indexes": ["uploaded_by", "created_at"]}
    file_path = StringField(required=True)
    original_name = StringField(required=True)
    content_type = StringField()
    size = IntField(default=0)
    uploaded_by = ReferenceField(User)
    created_at = DateTimeField(default=utcnow)

    @property
    def url(self):
        from django.conf import settings

        return settings.MEDIA_URL + self.file_path


# ---------------------------------------------------------------------------
# Module 4: Subtask (embedded inside a Task)
# ---------------------------------------------------------------------------
class SubTask(EmbeddedDocument):
    # Stable client-side id so the UI can target a specific subtask.
    sid = StringField(required=True)
    title = StringField(required=True, max_length=300)
    is_done = BooleanField(default=False)
    assigned_to = ReferenceField(User)
    created_at = DateTimeField(default=utcnow)
    completed_at = DateTimeField()


# ---------------------------------------------------------------------------
# Module 6: Comment
# ---------------------------------------------------------------------------
class Comment(Document):
    meta = {"collection": "comments", "indexes": ["task", "created_at"]}
    task = ReferenceField("Task", required=True)
    author = ReferenceField(User, required=True)
    body = StringField(required=True)
    mentions = ListField(ReferenceField(User))
    attachments = ListField(ReferenceField(Attachment))
    is_edited = BooleanField(default=False)
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)


# ---------------------------------------------------------------------------
# Module 8: Time tracking
# ---------------------------------------------------------------------------
class TimeLog(Document):
    meta = {"collection": "time_logs", "indexes": ["task", "employee", "is_running"]}
    task = ReferenceField("Task", required=True)
    employee = ReferenceField(User, required=True)
    start_time = DateTimeField(required=True, default=utcnow)
    end_time = DateTimeField()
    # Seconds accumulated before the current running segment (for pause/resume).
    accumulated_seconds = IntField(default=0)
    is_running = BooleanField(default=True)
    note = StringField()
    created_at = DateTimeField(default=utcnow)

    @property
    def total_seconds(self):
        # Stopped: timer_stop() already folded the final running segment into
        # accumulated_seconds, so don't add (end - start) again.
        if self.end_time:
            return self.accumulated_seconds or 0
        # Running: previous segments + elapsed time in the current segment.
        if self.is_running and self.start_time:
            return (self.accumulated_seconds or 0) + int(
                (utcnow() - self.start_time).total_seconds()
            )
        # Paused (no end_time, not running): accumulated has all work so far.
        return self.accumulated_seconds or 0


# ---------------------------------------------------------------------------
# Module 9: Activity log
# ---------------------------------------------------------------------------
class ActivityLog(Document):
    meta = {
        "collection": "activity_logs",
        "indexes": ["task", "project", "-created_at"],
        "ordering": ["-created_at"],
    }
    task = ReferenceField("Task")
    project = ReferenceField(Project)
    actor = ReferenceField(User)
    verb = StringField(required=True, default=ACTIVITY_TASK_CREATED)
    message = StringField(required=True)
    created_at = DateTimeField(default=utcnow)


# ---------------------------------------------------------------------------
# Module 3: Task
# ---------------------------------------------------------------------------
class Task(Document):
    meta = {
        "collection": "tasks",
        "indexes": [
            "project",
            "assigned_to",
            "reporter",
            "status",
            "priority",
            "due_date",
            "task_id",
        ],
        "ordering": ["-created_at"],
    }

    task_id = StringField(required=True, unique=True, max_length=32)
    title = StringField(required=True, max_length=300)
    description = StringField()
    project = ReferenceField(Project, required=True)

    assigned_to = ReferenceField(User)
    reporter = ReferenceField(User)

    priority = StringField(choices=PRIORITIES, default="medium")
    status = StringField(choices=TASK_STATUSES, default="todo")

    due_date = DateTimeField()
    estimated_hours = FloatField(default=0)
    actual_hours = FloatField(default=0)
    actual_hours_override = FloatField()
    tags = ListField(StringField())

    subtasks = EmbeddedDocumentListField(SubTask)
    attachments = ListField(ReferenceField(Attachment))

    # Position within its kanban column (for drag & drop ordering).
    board_order = IntField(default=0)

    created_by = ReferenceField(User)
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)
    completed_at = DateTimeField()

    def save(self, *args, **kwargs):
        self.updated_at = utcnow()
        return super().save(*args, **kwargs)

    # ---- Module 4: progress formula ----
    @property
    def progress(self):
        total = len(self.subtasks)
        if not total:
            return 100 if self.status == "completed" else 0
        done = sum(1 for s in self.subtasks if s.is_done)
        return round(done / total * 100)

    @property
    def is_overdue(self):
        if not self.due_date or self.status in ("completed", "rejected"):
            return False
        return self.due_date < utcnow()

    @property
    def actual_seconds(self):
        """Seconds worked on this task. Returns manual override when set."""
        if self.actual_hours_override is not None:
            return int(self.actual_hours_override * 3600)
        return sum(tl.total_seconds for tl in TimeLog.objects(task=self))

    def __str__(self):
        return f"{self.task_id} · {self.title}"
