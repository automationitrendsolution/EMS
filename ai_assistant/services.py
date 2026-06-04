"""Module 13: AI Task Assistant powered by OpenAI (with offline fallback).

If ``OPENAI_API_KEY`` is unset, deterministic heuristic responses are returned
so the feature degrades gracefully in dev / CI.
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _client():
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI

        return OpenAI(api_key=settings.OPENAI_API_KEY)
    except Exception as e:  # pragma: no cover
        logger.warning("OpenAI client unavailable: %s", e)
        return None


def _chat(system, user, json_mode=False):
    client = _client()
    if client is None:
        return None
    kwargs = {
        "model": settings.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# AI Task Breakdown
# ---------------------------------------------------------------------------
def task_breakdown(goal):
    content = _chat(
        "You are a senior project manager. Break a high-level goal into 5-10 "
        'concrete, ordered task titles. Respond as JSON: {"tasks": ["...", ...]}.',
        f"Goal: {goal}",
        json_mode=True,
    )
    if content:
        try:
            data = json.loads(content)
            return {"source": "openai", "tasks": data.get("tasks", [])}
        except json.JSONDecodeError:
            pass
    # Fallback heuristic
    return {
        "source": "fallback",
        "tasks": [
            "Requirement Analysis",
            "Design & Architecture",
            f"Core Implementation: {goal}",
            "Integration",
            "Testing & QA",
            "Documentation",
            "Deployment",
        ],
    }


# ---------------------------------------------------------------------------
# AI Task Summary
# ---------------------------------------------------------------------------
def task_summary(task):
    from tasks.models import Comment

    comments = Comment.objects(task=task).order_by("created_at")
    comment_text = "\n".join(f"- {c.author.full_name}: {c.body}" for c in comments)
    context = (
        f"Title: {task.title}\n"
        f"Status: {task.status}\n"
        f"Progress: {task.progress}%\n"
        f"Description: {task.description or 'N/A'}\n"
        f"Comments:\n{comment_text or 'None'}"
    )
    content = _chat(
        "Summarize the task status in 3-4 concise sentences for a manager.",
        context,
    )
    if content:
        return {"source": "openai", "summary": content.strip()}
    return {
        "source": "fallback",
        "summary": (
            f"'{task.title}' is currently {task.status} at {task.progress}% complete "
            f"with {comments.count()} comment(s)."
        ),
    }


# ---------------------------------------------------------------------------
# AI Project Health Analysis
# ---------------------------------------------------------------------------
def project_health(project):
    from tasks.models import Task

    tasks = Task.objects(project=project)
    total = tasks.count()
    completed = tasks.filter(status="completed").count()
    overdue = tasks.filter(
        due_date__ne=None, status__nin=["completed", "rejected"]
    ).filter(__raw__={"due_date": {"$lt": _now()}}).count()
    pending = tasks.filter(status__nin=["completed", "rejected"]).count()

    metrics = (
        f"Project: {project.name}\nTotal: {total}\nCompleted: {completed}\n"
        f"Pending: {pending}\nOverdue: {overdue}"
    )
    content = _chat(
        "You are a project risk analyst. Given metrics, output JSON: "
        '{"status": "Healthy|At Risk|Critical", "reason": "...", "suggestion": "..."}.',
        metrics,
        json_mode=True,
    )
    if content:
        try:
            data = json.loads(content)
            data["source"] = "openai"
            data["metrics"] = {"total": total, "completed": completed,
                               "pending": pending, "overdue": overdue}
            return data
        except json.JSONDecodeError:
            pass

    # Fallback heuristic risk model.
    if overdue >= 10 or (total and overdue / total > 0.3):
        status, reason = "At Risk", f"{overdue} tasks overdue."
        suggestion = "Allocate additional resources and re-prioritize the backlog."
    elif overdue > 0:
        status, reason = "At Risk", f"{overdue} task(s) overdue."
        suggestion = "Review overdue items in the next standup."
    else:
        status, reason = "Healthy", "No overdue tasks."
        suggestion = "Maintain current pace."
    return {
        "source": "fallback",
        "status": status,
        "reason": reason,
        "suggestion": suggestion,
        "metrics": {"total": total, "completed": completed,
                    "pending": pending, "overdue": overdue},
    }


def _now():
    import datetime

    return datetime.datetime.now(datetime.timezone.utc)
