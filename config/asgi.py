import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialise Django (and the HTTP app) before importing anything that touches
# models / channel routing.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from config.mongo import connect_mongo  # noqa: E402
from core.ws_auth import JWTAuthMiddlewareStack  # noqa: E402
import core.routing  # noqa: E402

connect_mongo()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(
            URLRouter(core.routing.websocket_urlpatterns)
        ),
    }
)
