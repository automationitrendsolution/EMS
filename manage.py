#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable?"
        ) from exc

    # Ensure MongoEngine is connected for management commands too.
    from config.mongo import connect_mongo

    try:
        connect_mongo()
    except Exception as exc:  # pragma: no cover - best effort for offline cmds
        sys.stderr.write(f"[warn] MongoDB connection skipped: {exc}\n")

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
