"""Repair orphaned / runaway time-tracking timers.

A timer that was started but never stopped (browser closed, forgot to hit
stop) stays ``is_running=True`` with no ``end_time``. Because a task's actual
time is computed live from its time logs, that one open log keeps adding real
wall-clock through nights and weekends and inflates the displayed time
(the 5:30:00 -> 48:55:07 bug).

This command stops every still-open timer:

* The current running segment is folded into ``accumulated_seconds`` using the
  same ``running_segment_seconds`` rule the app uses — a segment longer than
  ``settings.STALE_TIMER_SECONDS`` is treated as abandoned and contributes 0,
  so phantom overnight time is discarded and only legitimately tracked work
  (committed via earlier pause/stop) survives.
* ``end_time`` is set so the log is final and can never grow again.
* Each affected task is re-saved so its denormalized ``actual_hours`` matches.

Run once after deploying the timer fix:

    python manage.py repair_timers            # apply the fix
    python manage.py repair_timers --dry-run  # preview only, change nothing
"""
from django.core.management.base import BaseCommand

from config.mongo import connect_mongo
from tasks.models import Task, TimeLog, running_segment_seconds, utcnow


class Command(BaseCommand):
    help = "Stop orphaned/runaway timers and re-sync task actual_hours."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **opts):
        connect_mongo()
        dry = opts["dry_run"]

        open_logs = list(TimeLog.objects(end_time=None))
        if not open_logs:
            self.stdout.write(self.style.SUCCESS("No open timers — nothing to repair."))
            return

        affected_tasks = set()
        fixed = 0
        for log in open_logs:
            before = log.accumulated_seconds or 0
            segment = running_segment_seconds(log.start_time) if log.is_running else 0
            after = before + segment
            discarded = log.is_running and segment == 0

            task = log.task
            tid = task.task_id if task else "<no task>"
            self.stdout.write(
                f"  TimeLog {log.id} (task {tid}): "
                f"{_hms(before)} + segment {_hms(segment)}"
                f"{' [abandoned segment discarded]' if discarded else ''}"
                f" -> {_hms(after)}"
            )

            if not dry:
                log.accumulated_seconds = after
                log.is_running = False
                log.end_time = utcnow()
                log.save()
                if task:
                    affected_tasks.add(task.id)
            fixed += 1

        if dry:
            self.stdout.write(self.style.WARNING(
                f"\nDRY RUN — {fixed} open timer(s) would be stopped. No changes written."
            ))
            return

        # Re-save affected tasks so the denormalized actual_hours is rebuilt
        # from the now-final time logs.
        for task in Task.objects(id__in=list(affected_tasks)):
            task.save()

        self.stdout.write(self.style.SUCCESS(
            f"\nStopped {fixed} open timer(s); re-synced {len(affected_tasks)} task(s)."
        ))


def _hms(seconds):
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
