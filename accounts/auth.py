"""JWT issuance/verification + a DRF authentication class for MongoEngine users."""
import datetime

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _encode(payload):
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def make_access_token(user):
    now = _now()
    payload = {
        "sub": str(user.id),
        "type": "access",
        "role": user.role,
        "email": user.email,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=settings.JWT_ACCESS_MINUTES),
    }
    return _encode(payload)


def make_refresh_token(user):
    now = _now()
    payload = {
        "sub": str(user.id),
        "type": "refresh",
        "iat": now,
        "exp": now + datetime.timedelta(days=settings.JWT_REFRESH_DAYS),
    }
    return _encode(payload)


def make_token_pair(user):
    return {
        "access": make_access_token(user),
        "refresh": make_refresh_token(user),
        "expires_in": settings.JWT_ACCESS_MINUTES * 60,
    }


def decode_token(token):
    return jwt.decode(
        token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )


class SessionUserAuthentication(BaseAuthentication):
    """Authenticate DRF requests using the frontend signed-cookie session.

    Lets browser downloads (``window.open``) and the server-rendered UI reuse
    the REST API without a Bearer header. Returns None (not an error) when no
    session user is present so other authenticators get a turn.
    """

    def authenticate(self, request):
        # Only honor the session for safe methods so state-changing requests
        # cannot be driven cross-site via the cookie (CSRF). Mutations must
        # carry a Bearer token.
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            return None
        user_id = request.session.get("user_id") if hasattr(request, "session") else None
        if not user_id:
            return None
        from accounts.models import User

        user = User.objects(id=user_id, status="active").first()
        if not user:
            return None
        return (user, None)


class JWTAuthentication(BaseAuthentication):
    """Reads ``Authorization: Bearer <access-token>`` and loads the User doc."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(self.keyword + " "):
            return None
        token = header[len(self.keyword) + 1 :].strip()
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expired.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token.")

        if payload.get("type") != "access":
            raise AuthenticationFailed("Invalid token type.")

        from accounts.models import User

        user = User.objects(id=payload["sub"]).first()
        if not user or user.status != "active":
            raise AuthenticationFailed("User inactive or not found.")
        return (user, token)

    def authenticate_header(self, request):
        return self.keyword
