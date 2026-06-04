import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.mongo import connect_mongo  # noqa: E402

connect_mongo()
application = get_wsgi_application()
