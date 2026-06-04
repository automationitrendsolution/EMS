"""Create notifications and push them in realtime via Channels."""
import datetime

from core.realtime import broadcast, user_group
from notifications.models import Notification


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def notify(recipient, *, title, message="", notif_type="task_assigned", actor=None, link=None):
    """Persist a notification and push it to the recipient's WS group."""
    if recipient is None:
        return None
    # Don't notify yourself about your own action.
    if actor and str(actor.id) == str(recipient.id):
        return None
    n = Notification(
        recipient=recipient,
        actor=actor,
        notif_type=notif_type,
        title=title,
        message=message,
        link=link,
    ).save()
    broadcast(
        user_group(str(recipient.id)),
        "notify",
        {
            "id": str(n.id),
            "title": title,
            "message": message,
            "type": notif_type,
            "link": link,
            "created_at": n.created_at.isoformat(),
        },
    )
    return n


def notify_many(recipients, **kwargs):
    seen = set()
    for r in recipients:
        if r and str(r.id) not in seen:
            seen.add(str(r.id))
            notify(r, **kwargs)


def dispatch_due_date_reminders():
    """Notify assignees of tasks due within the next 24h (Module 11)."""
    from tasks.models import Task

    now = utcnow()
    soon = now + datetime.timedelta(hours=24)
    qs = Task.objects(
        due_date__gte=now,
        due_date__lte=soon,
        status__nin=["completed", "rejected"],
        assigned_to__ne=None,
    )
    count = 0
    for task in qs:
        notify(
            task.assigned_to,
            title="Task due soon",
            message=f"'{task.title}' is due {task.due_date:%Y-%m-%d %H:%M} UTC.",
            notif_type="due_date_reminder",
            link=f"/tasks/{task.id}/",
        )
        count += 1
    return f"Dispatched {count} due-date reminders"
