"""Thread-local current user + session-based frontend authentication."""
import threading

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
