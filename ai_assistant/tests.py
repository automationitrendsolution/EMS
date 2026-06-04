from accounts.services import create_user
from ai_assistant import services
from core.testutils import MongoTestCase
from projects.models import Project
from tasks.models import Task
from tasks.services import next_task_id


class AIFallbackTests(MongoTestCase):
    """With no OPENAI_API_KEY set, services must degrade to heuristics."""

    def test_breakdown_fallback(self):
        out = services.task_breakdown("Build E-Commerce Website")
        self.assertEqual(out["source"], "fallback")
        self.assertTrue(len(out["tasks"]) >= 5)

    def test_project_health_fallback(self):
        u = create_user(full_name="U", email="u@x.com", password="pw123456")
        p = Project(name="P", manager=u).save()
        for i in range(3):
            Task(task_id=next_task_id(), title=f"T{i}", project=p,
                 status="completed").save()
        out = services.project_health(p)
        self.assertEqual(out["source"], "fallback")
        self.assertIn(out["status"], ["Healthy", "At Risk", "Critical"])
        self.assertEqual(out["metrics"]["total"], 3)
