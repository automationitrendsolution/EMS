import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("itrendtasks")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Hourly scan for due-date reminders.
    sender.add_periodic_task(
        crontab(minute=0),
        send_due_date_reminders.s(),
        name="hourly-due-date-reminders",
    )


@app.task
def send_due_date_reminders():
    from notifications.services import dispatch_due_date_reminders

    return dispatch_due_date_reminders()
