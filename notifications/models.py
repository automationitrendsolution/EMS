"""Module 11: Notifications."""
import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    ReferenceField,
    StringField,
)

from accounts.models import User
from core.constants import NOTIF_TASK_ASSIGNED


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class Notification(Document):
    meta = {
        "collection": "notifications",
        "indexes": ["recipient", "is_read", "-created_at"],
        "ordering": ["-created_at"],
    }
    recipient = ReferenceField(User, required=True)
    actor = ReferenceField(User)
    notif_type = StringField(default=NOTIF_TASK_ASSIGNED)
    title = StringField(required=True)
    message = StringField()
    link = StringField()  # frontend URL to open
    is_read = BooleanField(default=False)
    created_at = DateTimeField(default=utcnow)
