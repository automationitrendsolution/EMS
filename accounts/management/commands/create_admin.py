"""Create or reset the super-admin account without seeding any dummy data."""
from django.core.management.base import BaseCommand

from accounts.models import User
from accounts.services import create_user
from config.mongo import connect_mongo


class Command(BaseCommand):
    help = "Create (or reset password of) the super-admin account."

    def add_arguments(self, parser):
        parser.add_argument("--email",    default="admin@itrend.local")
        parser.add_argument("--password", default="Admin@1234")
        parser.add_argument("--name",     default="System Admin")

    def handle(self, *args, **opts):
        connect_mongo()
        email    = opts["email"].lower().strip()
        password = opts["password"]
        name     = opts["name"]

        existing = User.objects(email=email).first()
        if existing:
            existing.set_password(password)
            existing.status = "active"
            existing.save()
            self.stdout.write(self.style.SUCCESS(
                f"Password reset for existing admin: {email}"
            ))
        else:
            create_user(full_name=name, email=email, password=password, role="super_admin")
            self.stdout.write(self.style.SUCCESS(
                f"Admin created: {email}"
            ))

        self.stdout.write(f"  Email   : {email}")
        self.stdout.write(f"  Password: {password}")
