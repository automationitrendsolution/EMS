from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.api_helpers import paginate
from core.constants import MANAGEMENT_ROLES
from projects.models import Project
from projects.serializers import ProjectWriteSerializer, project_repr
from projects.services import can_edit_project, can_view_project, visible_projects
from tasks.models import Task


def project_stats(project):
    tasks = Task.objects(project=project)
    total = tasks.count()
    completed = tasks.filter(status="completed").count()
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "progress": round(completed / total * 100) if total else 0,
    }


def _members(ids):
    return [u for u in (User.objects(id=i).first() for i in ids) if u]


class ProjectListCreateView(APIView):
    def get(self, request):
        qs = visible_projects(
            request.user,
            include_archived=request.query_params.get("archived") == "true",
        )
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        for f in ("status", "priority"):
            val = request.query_params.get(f)
            if val:
                qs = qs.filter(**{f: val})
        ordering = request.query_params.get("ordering", "-created_at")
        qs = qs.order_by(ordering)
        return paginate(
            request, qs, lambda p: project_repr(p, stats=project_stats(p))
        )

    def post(self, request):
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        s = ProjectWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        manager = User.objects(id=d["manager_id"]).first() if d.get("manager_id") else None
        p = Project(
            name=d["name"],
            description=d.get("description"),
            start_date=d.get("start_date"),
            end_date=d.get("end_date"),
            status=d["status"],
            priority=d["priority"],
            manager=manager,
            team_members=_members(d.get("team_member_ids", [])),
            created_by=request.user,
        ).save()
        return Response(project_repr(p, stats=project_stats(p)), status=201)


class ProjectDetailView(APIView):
    def get_obj(self, pk):
        return Project.objects(id=pk).first()

    def get(self, request, pk):
        p = self.get_obj(pk)
        if not p:
            return Response({"detail": "Not found."}, status=404)
        if not can_view_project(request.user, p):
            return Response({"detail": "Forbidden."}, status=403)
        return Response(project_repr(p, stats=project_stats(p)))

    def patch(self, request, pk):
        p = self.get_obj(pk)
        if not p:
            return Response({"detail": "Not found."}, status=404)
        if not can_edit_project(request.user, p):
            return Response({"detail": "Forbidden."}, status=403)
        s = ProjectWriteSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        for f in ("name", "description", "start_date", "end_date", "status", "priority"):
            if f in d:
                setattr(p, f, d[f])
        if "manager_id" in d:
            p.manager = User.objects(id=d["manager_id"]).first() if d["manager_id"] else None
        if "team_member_ids" in d:
            p.team_members = _members(d["team_member_ids"])
        p.save()
        return Response(project_repr(p, stats=project_stats(p)))

    def delete(self, request, pk):
        p = self.get_obj(pk)
        if not p:
            return Response({"detail": "Not found."}, status=404)
        if request.user.role not in MANAGEMENT_ROLES:
            return Response({"detail": "Forbidden."}, status=403)
        Task.objects(project=p).delete()
        p.delete()
        return Response(status=204)


class ProjectArchiveView(APIView):
    def post(self, request, pk):
        p = Project.objects(id=pk).first()
        if not p:
            return Response({"detail": "Not found."}, status=404)
        if not can_edit_project(request.user, p):
            return Response({"detail": "Forbidden."}, status=403)
        p.is_archived = not p.is_archived
        p.save()
        return Response({"id": str(p.id), "is_archived": p.is_archived})
