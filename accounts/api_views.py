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
from accounts.models import Department, Designation, Team, User
from accounts.serializers import (
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeCreateSerializer,
    EmployeeUpdateSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    RefreshSerializer,
    TeamSerializer,
    department_repr,
    designation_repr,
    team_repr,
    user_repr,
)
from accounts.services import create_user
from core.constants import MANAGEMENT_ROLES
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
        # Soft-deactivate rather than hard delete to preserve references.
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
