"""Employee/user creation helpers and id generation."""
from accounts.models import Department, Designation, Team, User


def delete_user(user):
    """Permanently delete an employee and scrub references that would
    otherwise dangle.

    List memberships (teams, project members) and scalar pointers (managers,
    task assignee/reporter, notification actor) are cleared so the rest of the
    app keeps working. The user's own performance goals cascade-delete
    automatically (``reverse_delete_rule=CASCADE``). Authored history such as
    comments and activity logs is intentionally left intact.
    """
    from notifications.models import Notification
    from projects.models import Project
    from tasks.models import Task

    # Remove from any list memberships.
    Team.objects(members=user).update(pull__members=user)
    Project.objects(team_members=user).update(pull__team_members=user)

    # Clear scalar pointers that reference this user.
    Team.objects(leader=user).update(unset__leader=1)
    Project.objects(manager=user).update(unset__manager=1)
    User.objects(manager=user).update(unset__manager=1)
    Task.objects(assigned_to=user).update(unset__assigned_to=1)
    Task.objects(reporter=user).update(unset__reporter=1)

    # Notifications addressed to the user are theirs to remove; for ones where
    # the user was merely the actor, just drop the actor pointer.
    Notification.objects(recipient=user).delete()
    Notification.objects(actor=user).update(unset__actor=1)

    user.delete()


def next_employee_id():
    """Generate the next sequential employee id like EMP0001."""
    last = User.objects.order_by("-employee_id").first()
    n = 1
    if last and last.employee_id and last.employee_id.startswith("EMP"):
        try:
            n = int(last.employee_id[3:]) + 1
        except ValueError:
            n = User.objects.count() + 1
    return f"EMP{n:04d}"


def create_user(
    *,
    full_name,
    email,
    password,
    role="employee",
    phone=None,
    department=None,
    designation=None,
    team=None,
    manager=None,
    status="active",
    employee_id=None,
):
    user = User(
        employee_id=employee_id or next_employee_id(),
        full_name=full_name,
        email=email.lower().strip(),
        phone=phone,
        role=role,
        department=department,
        designation=designation,
        team=team,
        manager=manager,
        status=status,
    )
    user.set_password(password)
    user.save()
    return user
