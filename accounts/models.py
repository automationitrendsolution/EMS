"""Module 1: Employee Management — User, Department, Designation, Team."""
import datetime

import bcrypt
from mongoengine import (
    CASCADE,
    BooleanField,
    DateTimeField,
    Document,
    EmailField,
    FloatField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)

from core.constants import (
    EMPLOYEE_STATUSES,
    PERF_KIND_KRA,
    PERF_KINDS,
    PERF_STATUSES,
    ROLE_EMPLOYEE,
    ROLE_LABELS,
    ROLES,
)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class Department(Document):
    meta = {"collection": "departments", "indexes": ["name"]}
    name = StringField(required=True, unique=True, max_length=120)
    description = StringField()
    created_at = DateTimeField(default=utcnow)

    def __str__(self):
        return self.name


class Designation(Document):
    meta = {"collection": "designations", "indexes": ["title"]}
    title = StringField(required=True, unique=True, max_length=120)
    department = ReferenceField(Department)
    created_at = DateTimeField(default=utcnow)

    def __str__(self):
        return self.title


class Team(Document):
    meta = {"collection": "teams", "indexes": ["name"]}
    name = StringField(required=True, max_length=120)
    description = StringField()
    # NULLIFY avoids dangling refs if a leader is removed.
    leader = ReferenceField("User")
    members = ListField(ReferenceField("User"))
    created_at = DateTimeField(default=utcnow)

    def __str__(self):
        return self.name


class User(Document):
    """An employee / system user. Doubles as the auth principal."""

    meta = {
        "collection": "users",
        "indexes": ["email", "employee_id", "role", "status"],
    }

    employee_id = StringField(required=True, unique=True, max_length=32)
    full_name = StringField(required=True, max_length=160)
    email = EmailField(required=True, unique=True)
    phone = StringField(max_length=32)
    password_hash = StringField(required=True)

    role = StringField(choices=ROLES, default=ROLE_EMPLOYEE)
    department = ReferenceField(Department)
    designation = ReferenceField(Designation)
    team = ReferenceField(Team)
    manager = ReferenceField("User")

    profile_image = StringField()  # media-relative path
    status = StringField(choices=EMPLOYEE_STATUSES, default="active")

    last_login = DateTimeField()
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)

    # ---- password helpers ----
    def set_password(self, raw_password):
        self.password_hash = bcrypt.hashpw(
            raw_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, raw_password):
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(
                raw_password.encode("utf-8"), self.password_hash.encode("utf-8")
            )
        except ValueError:
            return False

    # ---- DRF / auth compatibility shims ----
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def pk(self):
        return str(self.id)

    @property
    def role_label(self):
        return ROLE_LABELS.get(self.role, self.role)

    @property
    def profile_image_url(self):
        from django.conf import settings

        if self.profile_image:
            return settings.MEDIA_URL + self.profile_image
        return None

    def save(self, *args, **kwargs):
        self.updated_at = utcnow()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"


class PerformanceGoal(Document):
    """A KRA (Key Result Area) or KPI (Key Performance Indicator) for an employee.

    KRAs and KPIs share the same structure, so a single document with a
    ``kind`` discriminator covers both.
    """

    meta = {
        "collection": "performance_goals",
        "indexes": ["employee", "kind", "status", "period"],
        "ordering": ["kind", "-created_at"],
    }

    # Remove an employee's goals if the employee document is ever deleted.
    employee = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    kind = StringField(choices=PERF_KINDS, default=PERF_KIND_KRA, required=True)
    title = StringField(required=True, max_length=200)
    description = StringField()
    target = StringField(max_length=300)  # the measurable target / metric
    weightage = IntField(default=0, min_value=0, max_value=100)  # percent
    period = StringField(max_length=60)  # e.g. "Q1 2026", "FY2026"
    status = StringField(choices=PERF_STATUSES, default="not_started")
    score = FloatField(default=0.0, min_value=0, max_value=100)  # rating out of 100

    created_by = ReferenceField(User)
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)

    def save(self, *args, **kwargs):
        self.updated_at = utcnow()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.kind.upper()}] {self.title}"
