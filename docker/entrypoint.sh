#!/usr/bin/env bash
set -e

echo "Waiting for MongoDB at ${MONGO_HOST}:${MONGO_PORT}..."
python - <<'PY'
import os, time, sys
from pymongo import MongoClient
host = os.environ.get("MONGO_HOST", "mongodb")
port = int(os.environ.get("MONGO_PORT", "27017"))
user = os.environ.get("MONGO_USERNAME")
pwd = os.environ.get("MONGO_PASSWORD")
for i in range(30):
    try:
        kw = dict(serverSelectionTimeoutMS=2000)
        if user:
            kw.update(username=user, password=pwd, authSource=os.environ.get("MONGO_AUTH_SOURCE", "admin"))
        MongoClient(host, port, **kw).admin.command("ping")
        print("MongoDB is up.")
        break
    except Exception as e:
        print(f"  ...not ready ({e}); retry {i+1}/30")
        time.sleep(2)
else:
    print("MongoDB never became available.", file=sys.stderr)
    sys.exit(1)
PY

# Django internal (sqlite) migrations for django_celery_beat scheduler tables.
python manage.py migrate --noinput || true

if [ "${COLLECT_STATIC:-1}" = "1" ]; then
  python manage.py collectstatic --noinput || true
fi

if [ "${RUN_SEED:-0}" = "1" ]; then
  python manage.py seed_demo || true
fi

exec "$@"
