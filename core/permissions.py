"""DRF permission classes for RBAC over MongoEngine users."""
from rest_framework.permissions import BasePermission

from core.constants import MANAGEMENT_ROLES, ROLE_RANK


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return getattr(request, "user", None) is not None


class HasRole(BasePermission):
    """View must declare ``allowed_roles`` (iterable of role strings)."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user:
            return False
        allowed = getattr(view, "allowed_roles", None)
        if not allowed:
            return True
        return user.role in allowed


class IsManagement(BasePermission):
    """Super Admin / Admin / Project Manager only."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.role in MANAGEMENT_ROLES)


class MinRole(BasePermission):
    """View declares ``min_role``; user must meet/exceed its rank."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        min_role = getattr(view, "min_role", None)
        if not user:
            return False
        if not min_role:
            return True
        return ROLE_RANK.get(user.role, 0) >= ROLE_RANK[min_role]
