"""Modules 3,4,6,7,8,9: Tasks, Subtasks, Comments, Attachments, Time, Activity."""
import datetime

from mongoengine import (
    CASCADE,
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
    PRIORITY_LABELS,
    STATUS_LABELS,
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
    # NOTE: cascade-on-task-delete is registered after Task is defined (below),
    # because Task is declared later in this module and isn't in the registry
    # yet at class-creation time.
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
    task = ReferenceField("Task", required=True)  # cascade registered below
    employee = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
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
    task = ReferenceField("Task")  # cascade registered below (Task defined later)
    project = ReferenceField(Project, reverse_delete_rule=CASCADE)
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
    project = ReferenceField(Project, required=True, reverse_delete_rule=CASCADE)

    assigned_to = ReferenceField(User)
    reporter = ReferenceField(User)

    priority = StringField(choices=PRIORITIES, default="medium")
    status = StringField(choices=TASK_STATUSES, default="todo")

    due_date = DateTimeField()
    estimated_hours = FloatField(default=0)
    # Denormalized cache of tracked time (hours). Always kept in sync with
    # ``actual_seconds`` in save(); never written directly by clients.
    actual_hours = FloatField(default=0)
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
        # Keep the denormalized ``actual_hours`` field in lock-step with the
        # authoritative ``actual_seconds`` (summed from live time logs). This
        # guarantees every reader of the field — the task serializer, project
        # roll-ups, reports — sees one consistent value that can never go stale
        # after a timer is started, paused, or stopped.
        if self.id is not None:
            self.actual_hours = round(self.actual_seconds / 3600, 2)
        # (New, unsaved tasks have no id yet and therefore no time logs; their
        #  actual_hours stays at the default 0 until the first save after work.)
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
    def status_label(self):
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def priority_label(self):
        return PRIORITY_LABELS.get(self.priority, self.priority)

    @property
    def actual_seconds(self):
        """Seconds worked on this task, summed from its time logs."""
        return sum(tl.total_seconds for tl in TimeLog.objects(task=self))

    def __str__(self):
        return f"{self.task_id} · {self.title}"


# ---------------------------------------------------------------------------
# Cascade rules for documents that reference Task by forward (string) name.
# These can't be declared inline on Comment/TimeLog/ActivityLog because Task is
# defined after them in this module (not yet in the registry at that point), so
# we register them here once Task exists. Deleting a Task now also deletes its
# comments, time logs, and activity entries — no orphaned documents.
# ---------------------------------------------------------------------------
Task.register_delete_rule(Comment, "task", CASCADE)
Task.register_delete_rule(TimeLog, "task", CASCADE)
Task.register_delete_rule(ActivityLog, "task", CASCADE)
