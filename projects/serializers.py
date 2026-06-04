from rest_framework import serializers

from core.constants import PRIORITIES, PROJECT_STATUSES
from core.utils import doc_brief


def project_repr(p, stats=None):
    data = {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "status": p.status,
        "priority": p.priority,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "end_date": p.end_date.isoformat() if p.end_date else None,
        "manager": doc_brief(p.manager),
        "team_members": [doc_brief(m) for m in p.team_members],
        "is_archived": p.is_archived,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
    if stats:
        data["stats"] = stats
    return data


class ProjectWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=PROJECT_STATUSES, default="planning")
    priority = serializers.ChoiceField(choices=PRIORITIES, default="medium")
    manager_id = serializers.CharField(required=False, allow_blank=True)
    team_member_ids = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
