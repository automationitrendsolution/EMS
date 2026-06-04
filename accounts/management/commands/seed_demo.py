"""Seed the database with demo data covering every role and module."""
import datetime

from django.core.management.base import BaseCommand

from accounts.models import Department, Designation, Team, User
from accounts.services import create_user
from config.mongo import connect_mongo
from projects.models import Project
from tasks.models import Comment, SubTask, Task
from tasks.services import log_activity, next_task_id


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class Command(BaseCommand):
    help = "Seed demo data (idempotent if admin already exists unless --force)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Wipe and reseed.")

    def handle(self, *args, **opts):
        connect_mongo()
        if opts["force"]:
            for model in (Comment, Task, Project, Team, Designation, Department, User):
                model.drop_collection()
            self.stdout.write("Dropped existing collections.")

        if User.objects(email="admin@itrendtasks.local").first() and not opts["force"]:
            self.stdout.write(self.style.WARNING("Demo data exists. Use --force to reseed."))
            return

        # Departments & designations
        eng = Department(name="Engineering", description="Product engineering").save()
        qa = Department(name="Quality Assurance").save()
        senior = Designation(title="Senior Engineer", department=eng).save()
        junior = Designation(title="Engineer", department=eng).save()
        Designation(title="QA Analyst", department=qa).save()

        # Users — one per role
        admin = create_user(full_name="System Admin", email="admin@itrendtasks.local",
                            password="admin12345", role="super_admin",
                            department=eng, designation=senior)
        pm = create_user(full_name="Priya Manager", email="pm@itrendtasks.local",
                         password="pm12345", role="project_manager", department=eng,
                         designation=senior, manager=admin)
        tl = create_user(full_name="Tariq Leader", email="tl@itrendtasks.local",
                         password="tl12345", role="team_leader", department=eng,
                         designation=senior, manager=pm)
        emp1 = create_user(full_name="Rajesh Kumar", email="rajesh@itrendtasks.local",
                           password="emp12345", role="employee", department=eng,
                           designation=junior, manager=tl)
        emp2 = create_user(full_name="Sara Ali", email="sara@itrendtasks.local",
                           password="emp12345", role="employee", department=qa,
                           manager=tl)

        team = Team(name="Core Team", leader=tl, members=[emp1, emp2]).save()
        emp1.team = team; emp1.save()
        emp2.team = team; emp2.save()

        # Projects
        proj = Project(
            name="E-Commerce Platform",
            description="Build a modern e-commerce website with cart and payments.",
            status="active", priority="high", manager=pm,
            team_members=[tl, emp1, emp2], created_by=admin,
            start_date=utcnow(), end_date=utcnow() + datetime.timedelta(days=60),
        ).save()
        Project(
            name="Mobile App Revamp", description="Redesign the customer mobile app.",
            status="planning", priority="medium", manager=pm,
            team_members=[emp1], created_by=admin,
        ).save()

        # Tasks with subtasks + comments, spread across kanban columns
        plan = [
            ("Requirement Analysis", "completed", emp1, ["Interview stakeholders", "Write spec"]),
            ("Design Database Schema", "in_progress", emp1, ["ER diagram", "Index plan"]),
            ("Build Cart Module", "todo", emp2, ["Add to cart API", "Cart UI"]),
            ("Payment Integration", "todo", emp1, ["Gateway research", "Checkout flow"]),
            ("QA Test Suite", "testing", emp2, ["Unit tests", "E2E tests"]),
            ("Deployment Pipeline", "review", tl, ["Dockerize", "CI setup"]),
        ]
        for i, (title, status, assignee, subs) in enumerate(plan):
            t = Task(
                task_id=next_task_id(), title=title, project=proj,
                assigned_to=assignee, reporter=pm, status=status,
                priority=["low", "medium", "high", "critical"][i % 4],
                estimated_hours=8, board_order=i,
                due_date=utcnow() + datetime.timedelta(days=7 + i),
                subtasks=[
                    SubTask(sid=f"s{i}{j}", title=s, is_done=(status == "completed"))
                    for j, s in enumerate(subs)
                ],
                created_by=pm,
            ).save()
            log_activity(actor=pm, task=t, message=f"created task {t.task_id}")
            Comment(task=t, author=tl, body=f"@{assignee.employee_id} please prioritize this.",
                    mentions=[assignee]).save()

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
        self.stdout.write("Login: admin@itrendtasks.local / admin12345")
        self.stdout.write("       pm@itrendtasks.local / pm12345")
        self.stdout.write("       rajesh@itrendtasks.local / emp12345")
