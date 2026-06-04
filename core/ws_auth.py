"""WebSocket auth: resolve a JWT (query string ?token= or cookie) to a user."""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async


@database_sync_to_async
def _get_user(token):
    from accounts.auth import decode_token
    from accounts.models import User

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return User.objects(id=payload["sub"], status="active").first()
    except Exception:
        return None


class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        token = None
        query = parse_qs(scope.get("query_string", b"").decode())
        if "token" in query:
            token = query["token"][0]
        if not token:
            for name, value in scope.get("headers", []):
                if name == b"authorization":
                    raw = value.decode()
                    if raw.lower().startswith("bearer "):
                        token = raw[7:]
        scope["user"] = await _get_user(token) if token else None
        return await self.app(scope, receive, send)


def JWTAuthMiddlewareStack(app):
    return JWTAuthMiddleware(app)
