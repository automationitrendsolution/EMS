from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Guarantee a MongoEngine connection whenever Django boots (runserver,
        # shell, celery worker, tests).
        from config.mongo import connect_mongo

        try:
            connect_mongo()
        except Exception:  # pragma: no cover
            pass
