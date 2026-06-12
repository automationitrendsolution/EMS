import datetime

from accounts.auth import make_token_pair
from accounts.services import create_user
from core.testutils import MongoTestCase
from projects.models import Project
from tasks.models import SubTask, Task, TimeLog
from tasks.services import next_task_id


def _utc(**delta):
    now = datetime.datetime.now(datetime.timezone.utc)
    return now - datetime.timedelta(**delta) if delta else now


class TaskModelTests(MongoTestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(full_name="U", email="u@x.com", password="pw123456")
        self.project = Project(name="P", manager=self.user).save()

    def test_progress_with_subtasks(self):
        t = Task(
            task_id=next_task_id(), title="T", project=self.project,
            subtasks=[
                SubTask(sid="1", title="a", is_done=True),
                SubTask(sid="2", title="b", is_done=False),
            ],
        ).save()
        self.assertEqual(t.progress, 50)

    def test_progress_no_subtasks(self):
        t = Task(task_id=next_task_id(), title="T", project=self.project,
                 status="completed").save()
        self.assertEqual(t.progress, 100)

    def test_overdue(self):
        past = _utc(days=1)
        t = Task(task_id=next_task_id(), title="T", project=self.project,
                 due_date=past, status="todo").save()
        self.assertTrue(t.is_overdue)


class TimerStaleTests(MongoTestCase):
    """A timer left running must not inflate a task's actual time."""

    def setUp(self):
        super().setUp()
        self.user = create_user(full_name="U", email="u@x.com", password="pw123456")
        self.project = Project(name="P", manager=self.user).save()

    def test_abandoned_running_timer_contributes_zero(self):
        # Timer started ~2 days ago and never stopped: the runaway segment is
        # treated as abandoned, so only previously-accumulated work counts.
        t = Task(task_id=next_task_id(), title="T", project=self.project).save()
        log = TimeLog(
            task=t, employee=self.user,
            start_time=_utc(days=2), is_running=True,
            accumulated_seconds=19800,  # 5:30:00 already legitimately tracked
        ).save()
        # Without the guard this would be ~48h+; with it, just the 5:30:00.
        self.assertEqual(log.total_seconds, 19800)
        self.assertEqual(t.actual_seconds, 19800)

    def test_normal_running_timer_still_counts_live(self):
        # A timer running for a sane duration keeps counting live.
        t = Task(task_id=next_task_id(), title="T", project=self.project).save()
        log = TimeLog(
            task=t, employee=self.user,
            start_time=_utc(minutes=30), is_running=True,
            accumulated_seconds=0,
        ).save()
        self.assertGreaterEqual(log.total_seconds, 29 * 60)
        self.assertLessEqual(log.total_seconds, 31 * 60)


class TaskAPITests(MongoTestCase):
    def setUp(self):
        super().setUp()
        self.admin = create_user(full_name="A", email="a@x.com",
                                 password="pw123456", role="admin")
        self.project = Project(name="P", manager=self.admin,
                               team_members=[self.admin]).save()
        self.auth = {
            "HTTP_AUTHORIZATION": f"Bearer {make_token_pair(self.admin)['access']}"
        }

    def test_create_and_list_task(self):
        res = self.client.post(
            "/api/v1/tasks/",
            data={"title": "New Task", "project_id": str(self.project.id)},
            content_type="application/json", **self.auth,
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["title"], "New Task")

        listed = self.client.get("/api/v1/tasks/", **self.auth)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 1)

    def test_move_task_changes_status(self):
        t = Task(task_id=next_task_id(), title="T", project=self.project,
                 reporter=self.admin).save()
        res = self.client.post(
            f"/api/v1/tasks/{t.id}/move/",
            data={"status": "in_progress", "board_order": 0},
            content_type="application/json", **self.auth,
        )
        self.assertEqual(res.status_code, 200)
        t.reload()
        self.assertEqual(t.status, "in_progress")

    def test_timer_start_then_stop(self):
        t = Task(task_id=next_task_id(), title="T", project=self.project,
                 reporter=self.admin, assigned_to=self.admin).save()
        start = self.client.post(
            f"/api/v1/tasks/{t.id}/timer/start/", content_type="application/json",
            **self.auth,
        )
        self.assertEqual(start.status_code, 201)
        stop = self.client.post(
            f"/api/v1/tasks/{t.id}/timer/stop/", content_type="application/json",
            **self.auth,
        )
        self.assertEqual(stop.status_code, 200, stop.content)
        self.assertFalse(stop.json()["is_running"])

    def test_timer_start_blocked_on_closed_task(self):
        t = Task(task_id=next_task_id(), title="T", project=self.project,
                 reporter=self.admin, assigned_to=self.admin,
                 status="completed").save()
        res = self.client.post(
            f"/api/v1/tasks/{t.id}/timer/start/", content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 400, res.content)

    def test_timer_blocked_for_non_assignee(self):
        # Only the assigned person may run a task's timer. A task assigned to
        # someone else (here: nobody) must reject the start with 403.
        other = create_user(full_name="B", email="b@x.com",
                            password="pw123456", role="employee")
        t = Task(task_id=next_task_id(), title="T", project=self.project,
                 reporter=self.admin, assigned_to=other).save()
        res = self.client.post(
            f"/api/v1/tasks/{t.id}/timer/start/", content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 403, res.content)

    def test_kanban_board_columns(self):
        Task(task_id=next_task_id(), title="T", project=self.project,
             status="todo", reporter=self.admin).save()
        res = self.client.get(f"/api/v1/kanban/{self.project.id}/", **self.auth)
        self.assertEqual(res.status_code, 200)
        cols = {c["key"]: c for c in res.json()["columns"]}
        self.assertEqual(len(cols["todo"]["tasks"]), 1)

    def test_kanban_board_role_scoped(self):
        # Two employees, one task each, both members of the project.
        from accounts.services import create_user

        emp1 = create_user(full_name="E1", email="e1@x.com", password="pw123456")
        emp2 = create_user(full_name="E2", email="e2@x.com", password="pw123456")
        self.project.team_members = [emp1, emp2]
        self.project.save()
        Task(task_id=next_task_id(), title="A", project=self.project,
             status="todo", assigned_to=emp1).save()
        Task(task_id=next_task_id(), title="B", project=self.project,
             status="todo", assigned_to=emp2).save()

        # Admin sees both; scope label "All tasks".
        res = self.client.get(f"/api/v1/kanban/{self.project.id}/", **self.auth)
        todo = [c for c in res.json()["columns"] if c["key"] == "todo"][0]
        self.assertEqual(len(todo["tasks"]), 2)
        self.assertEqual(res.json()["scope"], "All tasks")

        # Employee 1 sees only their own card; scope label "Your tasks".
        e1_auth = {"HTTP_AUTHORIZATION": f"Bearer {make_token_pair(emp1)['access']}"}
        res = self.client.get(f"/api/v1/kanban/{self.project.id}/", **e1_auth)
        todo = [c for c in res.json()["columns"] if c["key"] == "todo"][0]
        self.assertEqual(len(todo["tasks"]), 1)
        self.assertEqual(todo["tasks"][0]["title"], "A")
        self.assertEqual(res.json()["scope"], "Your tasks")
