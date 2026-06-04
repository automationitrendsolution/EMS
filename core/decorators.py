"""View decorators for the server-rendered frontend (session auth + RBAC)."""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from core.constants import ROLE_RANK


def login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "current_user", None):
            return redirect(f"/login/?next={request.path}")
        return view(request, *args, **kwargs)

    return wrapper


def roles_required(*allowed_roles):
    """Require that the current user has one of ``allowed_roles``."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, "current_user", None)
            if not user:
                return redirect(f"/login/?next={request.path}")
            if user.role not in allowed_roles:
                messages.error(request, "You do not have permission to view that page.")
                return redirect("/dashboard/")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def min_role_required(min_role):
    """Require at least the privilege rank of ``min_role``."""
    threshold = ROLE_RANK[min_role]

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, "current_user", None)
            if not user:
                return redirect(f"/login/?next={request.path}")
            if ROLE_RANK.get(user.role, 0) < threshold:
                messages.error(request, "Insufficient privileges.")
                return redirect("/dashboard/")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
