"""Auth + employee/department/designation/team REST endpoints."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.auth import (
    decode_token,
    make_access_token,
    make_token_pair,
)
from accounts.models import (
    Department,
    Designation,
    EmployeeError,
    PerformanceGoal,
    Team,
    User,
)
from accounts.serializers import (
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeCreateSerializer,
    EmployeeUpdateSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PerformanceGoalCreateSerializer,
    PerformanceGoalUpdateSerializer,
    RefreshSerializer,
    TeamSerializer,
    department_repr,
    designation_repr,
    performance_goal_repr,
    team_repr,
    user_repr,
)
from accounts.services import create_user, delete_user
from core.constants import (
    ERROR_SEVERITIES,
    ERROR_STATUSES,
    MANAGEMENT_ROLES,
    ROLE_SUPER_ADMIN,
)
from core.api_helpers import paginate


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data["email"].lower().strip()
        user = User.objects(email=email).first()
        if not user or not user.check_password(s.validated_data["password"]):
            return Response(
                {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
            )
        if user.status != "active":
            return Response(
                {"detail": "Account is not active."}, status=status.HTTP_403_FORBIDDEN
            )
        import datetime

        user.last_login = datetime.datetime.now(datetime.timezone.utc)
        user.save()
        tokens = make_token_pair(user)
        return Response({**tokens, "user": user_repr(user, full=True)})


class RefreshView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        s = RefreshSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            payload = decode_token(s.validated_data["refresh"])
        except Exception:
            return Response(
                {"detail": "Invalid refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if payload.get("type") != "refresh":
            return Response(
                {"detail": "Not a refresh token."}, status=status.HTTP_401_UNAUTHORIZED
            )
        user = User.objects(id=payload["sub"], status="active").first()
        if not user:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_401_UNAUTHORIZED
            )
        return Response({"access": make_access_token(user)})


@api_view(["GET"])
def me_view(request):
    return Response(user_repr(request.user, full=True))


@api_view(["POST"])
def change_password_view(request):
    s = PasswordChangeSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = request.user
    if not user.check_password(s.validated_data["old_password"]):
        return Response(
            {"detail": "Old password incorrect."}, status=status.HTTP_400_BAD_REQUEST
        )
    user.set_password(s.validated_data["new_password"])
    user.save()
    return Response({"detail": "Password updated."})


# ---------------------------------------------------------------------------
# Employees (Module 1)
# ---------------------------------------------------------------------------
def _resolve_ref(model, ref_id):
    if not ref_id:
        return None
    return model.objects(id=ref_id).first()


class EmployeeListCreateView(APIView):
    def get(self, request):
        qs = User.objects()
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(full_name__icontains=search)
        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        status_f = request.query_params.get("status")
        if status_f:
            qs = qs.filter(status=status_f)
        dept = request.query_params.get("department_id")
        if dept:
            qs = qs.filter(department=dept)
        qs = qs.order_by("full_name")
        return paginate(request, qs, lambda u: user_repr(u, full=True))

    def post(self, request):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        s = EmployeeCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        if User.objects(email=data["email"].lower().strip()).first():
            return Response({"detail": "Email already exists."}, status=400)
        user = create_user(
            full_name=data["full_name"],
            email=data["email"],
            password=data["password"],
            role=data["role"],
            phone=data.get("phone"),
            status=data["status"],
            department=_resolve_ref(Department, data.get("department_id")),
            designation=_resolve_ref(Designation, data.get("designation_id")),
            team=_resolve_ref(Team, data.get("team_id")),
            manager=_resolve_ref(User, data.get("manager_id")),
        )
        return Response(user_repr(user, full=True), status=201)


class EmployeeDetailView(APIView):
    def get_object(self, pk):
        return User.objects(id=pk).first()

    def get(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({"detail": "Not found."}, status=404)
        return Response(user_repr(user, full=True))

    def patch(self, request, pk):
        if request.user.role not in MANAGEMENT_ROLES and str(request.user.id) != pk:
            return Response({"detail": "Forbidden."}, status=403)
        user = self.get_object(pk)
        if not user:
            return Response({"detail": "Not found."}, status=404)
        s = EmployeeUpdateSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        for field in ("full_name", "phone", "status"):
            if field in d:
                setattr(user, field, d[field])
        # Only management may change roles.
        if "role" in d and request.user.role in MANAGEMENT_ROLES:
            user.role = d["role"]
        if "department_id" in d:
            user.department = _resolve_ref(Department, d["department_id"])
        if "designation_id" in d:
            user.designation = _resolve_ref(Designation, d["designation_id"])
        if "team_id" in d:
            user.team = _resolve_ref(Team, d["team_id"])
        if "manager_id" in d:
            user.manager = _resolve_ref(User, d["manager_id"])
        user.save()
        return Response(user_repr(user, full=True))

    def delete(self, request, pk):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        user = self.get_object(pk)
        if not user:
            return Response({"detail": "Not found."}, status=404)
        if str(user.id) == str(request.user.id):
            return Response(
                {"detail": "You cannot delete your own account."}, status=400
            )
        # ?hard=1 permanently removes the user (and scrubs references);
        # otherwise we soft-deactivate to preserve history.
        hard = str(request.query_params.get("hard", "")).lower() in ("1", "true", "yes")
        if hard:
            delete_user(user)
        else:
            user.status = "inactive"
            user.save()
        return Response(status=204)


# ---------------------------------------------------------------------------
# Departments / Designations / Teams
# ---------------------------------------------------------------------------
class DepartmentListCreateView(APIView):
    def get(self, request):
        return Response([department_repr(d) for d in Department.objects()])

    def post(self, request):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        s = DepartmentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = Department(**s.validated_data).save()
        return Response(department_repr(d), status=201)


class DepartmentDetailView(APIView):
    def _get(self, pk):
        d = Department.objects(id=pk).first()
        if not d:
            from rest_framework.exceptions import NotFound
            raise NotFound()
        return d

    def patch(self, request, pk):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        d = self._get(pk)
        s = DepartmentSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        for k, v in s.validated_data.items():
            setattr(d, k, v)
        d.save()
        return Response(department_repr(d))

    def delete(self, request, pk):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        self._get(pk).delete()
        return Response(status=204)


class DesignationListCreateView(APIView):
    def get(self, request):
        return Response([designation_repr(d) for d in Designation.objects()])

    def post(self, request):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        s = DesignationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        dept = _resolve_ref(Department, s.validated_data.get("department_id"))
        d = Designation(title=s.validated_data["title"], department=dept).save()
        return Response(designation_repr(d), status=201)


class TeamListCreateView(APIView):
    def get(self, request):
        return Response([team_repr(t) for t in Team.objects()])

    def post(self, request):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        s = TeamSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        team = Team(
            name=d["name"],
            description=d.get("description"),
            leader=_resolve_ref(User, d.get("leader_id")),
            members=[
                m for m in (_resolve_ref(User, mid) for mid in d.get("member_ids", []))
                if m
            ],
        ).save()
        return Response(team_repr(team), status=201)


# ---------------------------------------------------------------------------
# Performance goals — KRA (Key Result Area) / KPI (Key Performance Indicator)
# ---------------------------------------------------------------------------
# Fields an employee (the goal owner, but not management) is allowed to update
# themselves — they can report progress but not redefine or re-score the goal.
_PERF_OWNER_FIELDS = {"status"}


class PerformanceGoalListCreateView(APIView):
    def get(self, request):
        qs = PerformanceGoal.objects()
        if request.user.role not in MANAGEMENT_ROLES:
            # Non-management users only ever see their own goals.
            qs = qs.filter(employee=str(request.user.id))
        else:
            emp = request.query_params.get("employee_id")
            if emp:
                qs = qs.filter(employee=emp)
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        status_f = request.query_params.get("status")
        if status_f:
            qs = qs.filter(status=status_f)
        qs = qs.order_by("kind", "-created_at")
        return paginate(request, qs, performance_goal_repr)

    def post(self, request):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        s = PerformanceGoalCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        employee = _resolve_ref(User, d["employee_id"])
        if not employee:
            return Response({"detail": "Employee not found."}, status=400)
        goal = PerformanceGoal(
            employee=employee,
            kind=d["kind"],
            title=d["title"],
            description=d.get("description"),
            target=d.get("target"),
            weightage=d.get("weightage", 0),
            period=d.get("period"),
            status=d["status"],
            score=d.get("score", 0),
            created_by=request.user,
        ).save()
        return Response(performance_goal_repr(goal), status=201)


class PerformanceGoalDetailView(APIView):
    def get_object(self, pk):
        return PerformanceGoal.objects(id=pk).first()

    def _owns(self, request, goal):
        return goal.employee and str(goal.employee.id) == str(request.user.id)

    def get(self, request, pk):
        goal = self.get_object(pk)
        if not goal:
            return Response({"detail": "Not found."}, status=404)
        if request.user.role not in MANAGEMENT_ROLES and not self._owns(request, goal):
            return Response({"detail": "Forbidden."}, status=403)
        return Response(performance_goal_repr(goal))

    def patch(self, request, pk):
        goal = self.get_object(pk)
        if not goal:
            return Response({"detail": "Not found."}, status=404)
        is_mgmt = request.user.role in MANAGEMENT_ROLES
        if not is_mgmt and not self._owns(request, goal):
            return Response({"detail": "Forbidden."}, status=403)
        s = PerformanceGoalUpdateSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        for field in (
            "kind", "title", "description", "target",
            "weightage", "period", "status", "score",
        ):
            if field not in d:
                continue
            # Owners who aren't management may only touch progress fields.
            if not is_mgmt and field not in _PERF_OWNER_FIELDS:
                continue
            setattr(goal, field, d[field])
        goal.save()
        return Response(performance_goal_repr(goal))

    def delete(self, request, pk):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        goal = self.get_object(pk)
        if not goal:
            return Response({"detail": "Not found."}, status=404)
        goal.delete()
        return Response(status=204)


# ---------------------------------------------------------------------------
# Employee Errors (super-admin only)
# ---------------------------------------------------------------------------
def _parse_date(val):
    import datetime

    if not val:
        return None
    try:
        d = datetime.datetime.strptime(val, "%Y-%m-%d")
        return d.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def _parse_date_end(val):
    import datetime

    if not val:
        return None
    try:
        d = datetime.datetime.strptime(val, "%Y-%m-%d")
        return d.replace(
            hour=23, minute=59, second=59, tzinfo=datetime.timezone.utc
        )
    except ValueError:
        return None


def employee_error_repr(e):
    return {
        "id": str(e.id),
        "employee_id": str(e.employee.id) if e.employee else None,
        "employee_name": e.employee.full_name if e.employee else "(deleted)",
        "title": e.title,
        "description": e.description or "",
        "severity": e.severity,
        "severity_label": e.severity_label,
        "status": e.status,
        "status_label": e.status_label,
        "created_by": e.created_by.full_name if e.created_by else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _require_super_admin(request):
    return request.user.role == ROLE_SUPER_ADMIN


def _filter_employee_errors(params):
    qs = EmployeeError.objects()
    if params.get("employee_id"):
        qs = qs.filter(employee=params["employee_id"])
    if params.get("severity"):
        qs = qs.filter(severity=params["severity"])
    if params.get("status"):
        qs = qs.filter(status=params["status"])
    if params.get("search"):
        qs = qs.filter(title__icontains=params["search"])
    date_from = _parse_date(params.get("date_from"))
    date_to = _parse_date_end(params.get("date_to"))
    if date_from:
        qs = qs.filter(created_at__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__lte=date_to)
    return qs.order_by("-created_at")


class EmployeeErrorListCreateView(APIView):
    def get(self, request):
        if not _require_super_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        qs = _filter_employee_errors(request.query_params)
        return paginate(request, qs, employee_error_repr)

    def post(self, request):
        if not _require_super_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        d = request.data
        employee = _resolve_ref(User, d.get("employee_id"))
        if not employee:
            return Response({"detail": "Employee is required."}, status=400)
        title = (d.get("title") or "").strip()
        if not title:
            return Response({"detail": "Title is required."}, status=400)
        severity = d.get("severity") or "medium"
        if severity not in ERROR_SEVERITIES:
            return Response({"detail": "Invalid severity."}, status=400)
        status_val = d.get("status") or "open"
        if status_val not in ERROR_STATUSES:
            return Response({"detail": "Invalid status."}, status=400)
        err = EmployeeError(
            employee=employee,
            title=title,
            description=(d.get("description") or "").strip() or None,
            severity=severity,
            status=status_val,
            created_by=request.user,
        ).save()
        return Response(employee_error_repr(err), status=201)


class EmployeeErrorDetailView(APIView):
    def get_object(self, pk):
        return EmployeeError.objects(id=pk).first()

    def patch(self, request, pk):
        if not _require_super_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        err = self.get_object(pk)
        if not err:
            return Response({"detail": "Not found."}, status=404)
        d = request.data
        if "employee_id" in d:
            employee = _resolve_ref(User, d.get("employee_id"))
            if not employee:
                return Response({"detail": "Employee not found."}, status=400)
            err.employee = employee
        if "title" in d:
            title = (d.get("title") or "").strip()
            if not title:
                return Response({"detail": "Title is required."}, status=400)
            err.title = title
        if "description" in d:
            err.description = (d.get("description") or "").strip() or None
        if "severity" in d:
            if d["severity"] not in ERROR_SEVERITIES:
                return Response({"detail": "Invalid severity."}, status=400)
            err.severity = d["severity"]
        if "status" in d:
            if d["status"] not in ERROR_STATUSES:
                return Response({"detail": "Invalid status."}, status=400)
            err.status = d["status"]
        err.save()
        return Response(employee_error_repr(err))

    def delete(self, request, pk):
        if not _require_super_admin(request):
            return Response({"detail": "Forbidden."}, status=403)
        err = self.get_object(pk)
        if not err:
            return Response({"detail": "Not found."}, status=404)
        err.delete()
        return Response(status=204)
