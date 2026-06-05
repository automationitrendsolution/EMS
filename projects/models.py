"""Module 2: Project Management."""
import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    FloatField,
    ListField,
    ReferenceField,
    StringField,
)

from accounts.models import User
from core.constants import PRIORITIES, PROJECT_STATUSES


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class Project(Document):
    meta = {
        "collection": "projects",
        "indexes": ["status", "priority", "manager", "is_archived", "name"],
        "ordering": ["-created_at"],
    }

    name = StringField(required=True, max_length=200)
    description = StringField()
    start_date = DateTimeField()
    end_date = DateTimeField()
    status = StringField(choices=PROJECT_STATUSES, default="planning")
    priority = StringField(choices=PRIORITIES, default="medium")

    # Planned effort (hours); manually set. Actual effort is computed from the
    # project's tasks (see the ``actual_hours`` property below).
    estimated_hours = FloatField(default=0, min_value=0)

    manager = ReferenceField(User)
    team_members = ListField(ReferenceField(User))

    attachments = ListField(ReferenceField("tasks.Attachment"))

    is_archived = BooleanField(default=False)
    created_by = ReferenceField(User)
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)

    def save(self, *args, **kwargs):
        self.updated_at = utcnow()
        return super().save(*args, **kwargs)

    @property
    def member_ids(self):
        ids = {str(m.id) for m in self.team_members if m}
        if self.manager:
            ids.add(str(self.manager.id))
        return ids

    @property
    def actual_hours(self):
        """Auto-calculated total actual hours for the project: the sum of its
        tasks' ``actual_hours`` (each of which is derived from task time logs).
        """
        # Imported lazily — tasks.models imports this module.
        from tasks.models import Task

        if not self.id:
            return 0.0
        return round(Task.objects(project=self).sum("actual_hours") or 0, 2)

    def __str__(self):
        return self.name
