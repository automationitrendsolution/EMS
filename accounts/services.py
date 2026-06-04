"""Employee/user creation helpers and id generation."""
from accounts.models import Department, Designation, Team, User


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
