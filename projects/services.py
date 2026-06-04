"""Project visibility (RBAC scoping) helpers."""
from core.constants import MANAGEMENT_ROLES
from projects.models import Project


def visible_projects(user, include_archived=False):
    """Return a queryset of projects the user is allowed to see."""
    qs = Project.objects()
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if user.role in MANAGEMENT_ROLES:
        return qs
    # Team leaders & employees only see projects they belong to.
    return qs.filter(__raw__={"$or": [{"manager": user.id}, {"team_members": user.id}]})


def can_edit_project(user, project):
    if user.role in MANAGEMENT_ROLES:
        return True
    return project.manager and str(project.manager.id) == str(user.id)


def can_view_project(user, project):
    if user.role in MANAGEMENT_ROLES:
        return True
    return str(user.id) in project.member_ids
