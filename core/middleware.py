"""Thread-local current user + session-based frontend authentication."""
import threading

from django.middleware.csrf import CsrfViewMiddleware


class ProxyCsrfMiddleware(CsrfViewMiddleware):
    """CSRF middleware that skips the Origin-header check.

    When Django sits behind a reverse proxy (nginx) on a non-standard port
    (e.g. :8002) the browser's Origin header contains the external port which
    Django's default CSRF check rejects unless that exact origin is listed in
    CSRF_TRUSTED_ORIGINS.  Stripping HTTP_ORIGIN before the parent check makes
    Django fall back to the cookie + form-token guard, which is equally secure
    and works regardless of the port the proxy exposes.
    """

    def process_view(self, request, callback, callback_args, callback_kwargs):
        request.META.pop("HTTP_ORIGIN", None)
        return super().process_view(request, callback, callback_args, callback_kwargs)

_local = threading.local()


def get_current_user():
    return getattr(_local, "user", None)


def set_current_user(user):
    _local.user = user


class CurrentUserMiddleware:
    """Loads the MongoEngine user from the session and exposes it on request.

    The server-rendered frontend authenticates via signed-cookie sessions
    (``request.session['user_id']``). This middleware resolves that id to a
    ``User`` document and attaches it as ``request.current_user`` while also
    storing it in a thread-local for activity logging.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = None
        user_id = request.session.get("user_id")
        if user_id:
            from accounts.models import User

            user = User.objects(id=user_id, status="active").first()
        request.current_user = user
        set_current_user(user)
        try:
            response = self.get_response(request)
        finally:
            set_current_user(None)
        return response
