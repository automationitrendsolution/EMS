"""Central MongoEngine connection bootstrap."""
import logging

from django.conf import settings
from mongoengine import connect, disconnect

logger = logging.getLogger(__name__)
_CONNECTED = False


def connect_mongo():
    """Establish the default MongoEngine connection (idempotent)."""
    global _CONNECTED
    if _CONNECTED:
        return
    cfg = settings.MONGO
    kwargs = {
        "db": cfg["db"],
        "host": cfg["host"],
        "port": cfg["port"],
        "alias": "default",
        "uuidRepresentation": "standard",
        # Return timezone-aware (UTC) datetimes so arithmetic against our
        # tz-aware utcnow() never mixes naive/aware values.
        "tz_aware": True,
        "serverSelectionTimeoutMS": 5000,
    }
    if cfg.get("username"):
        kwargs.update(
            username=cfg["username"],
            password=cfg["password"],
            authentication_source=cfg.get("authentication_source", "admin"),
        )
    disconnect(alias="default")
    connect(**kwargs)
    _CONNECTED = True
    logger.info("Connected to MongoDB '%s' at %s:%s", cfg["db"], cfg["host"], cfg["port"])
