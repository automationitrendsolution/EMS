"""Module 2: Project Management."""
import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
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

    def __str__(self):
        return self.name
