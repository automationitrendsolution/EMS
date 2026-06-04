"""Input validation + output representation for accounts."""
from rest_framework import serializers

from core.constants import EMPLOYEE_STATUSES, ROLES
from core.utils import doc_brief


# ---- output helpers ----
def department_repr(d):
    if not d:
        return None
    return {"id": str(d.id), "name": d.name, "description": d.description}


def designation_repr(d):
    if not d:
        return None
    return {"id": str(d.id), "title": d.title}


def team_repr(t):
    if not t:
        return None
    return {
        "id": str(t.id),
        "name": t.name,
        "leader": doc_brief(t.leader),
        "members": [doc_brief(m) for m in t.members],
    }


def user_repr(u, full=False):
    if not u:
        return None
    base = doc_brief(u)
    if full:
        base.update(
            phone=u.phone,
            status=u.status,
            role_label=u.role_label,
            department=department_repr(u.department),
            designation=designation_repr(u.designation),
            team=team_repr(u.team) if u.team else None,
            manager=doc_brief(u.manager),
            last_login=u.last_login.isoformat() if u.last_login else None,
            created_at=u.created_at.isoformat() if u.created_at else None,
        )
    return base


# ---- input serializers ----
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class EmployeeCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6)
    phone = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=ROLES, default="employee")
    department_id = serializers.CharField(required=False, allow_blank=True)
    designation_id = serializers.CharField(required=False, allow_blank=True)
    team_id = serializers.CharField(required=False, allow_blank=True)
    manager_id = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=EMPLOYEE_STATUSES, default="active")


class EmployeeUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=ROLES, required=False)
    department_id = serializers.CharField(required=False, allow_blank=True)
    designation_id = serializers.CharField(required=False, allow_blank=True)
    team_id = serializers.CharField(required=False, allow_blank=True)
    manager_id = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=EMPLOYEE_STATUSES, required=False)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=6)


class DepartmentSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)


class DesignationSerializer(serializers.Serializer):
    title = serializers.CharField()
    department_id = serializers.CharField(required=False, allow_blank=True)


class TeamSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    leader_id = serializers.CharField(required=False, allow_blank=True)
    member_ids = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
