from accounts.auth import make_token_pair
from accounts.services import create_user
from core.testutils import MongoTestCase
from projects.models import Project
from tasks.models import SubTask, Task
from tasks.services import next_task_id


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
        import datetime
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
        t = Task(task_id=next_task_id(), title="T", project=self.project,
                 due_date=past, status="todo").save()
        self.assertTrue(t.is_overdue)


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
                 reporter=self.admin).save()
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

    def test_kanban_board_columns(self):
        Task(task_id=next_task_id(), title="T", project=self.project,
             status="todo", reporter=self.admin).save()
        res = self.client.get(f"/api/v1/kanban/{self.project.id}/", **self.auth)
        self.assertEqual(res.status_code, 200)
        cols = {c["key"]: c for c in res.json()["columns"]}
        self.assertEqual(len(cols["todo"]["tasks"]), 1)
