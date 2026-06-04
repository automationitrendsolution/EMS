"""Shared test helpers: in-memory Mongo via mongomock + a base TestCase."""
import mongomock
from django.test import TestCase
from mongoengine import connect, disconnect


class MongoTestCase(TestCase):
    """Connects MongoEngine to an in-memory mongomock instance per test."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        disconnect(alias="default")
        connect(
            db="itrendtasks_test",
            alias="default",
            mongo_client_class=mongomock.MongoClient,
            uuidRepresentation="standard",
            tz_aware=True,
        )

    @classmethod
    def tearDownClass(cls):
        disconnect(alias="default")
        super().tearDownClass()

    def setUp(self):
        # Clean every collection between tests.
        from accounts.models import Department, Designation, Team, User
        from notifications.models import Notification
        from projects.models import Project
        from tasks.models import (
            ActivityLog,
            Attachment,
            Comment,
            Task,
            TimeLog,
        )

        for model in (
            User, Department, Designation, Team, Project, Task, Comment,
            Attachment, TimeLog, ActivityLog, Notification,
        ):
            model.drop_collection()
