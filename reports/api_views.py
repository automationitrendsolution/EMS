from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.constants import MANAGEMENT_ROLES
from reports import services
from reports.exporters import export


@api_view(["GET"])
def report_data(request, report_type):
    """Return report rows as JSON (for on-screen tables)."""
    if request.user.role not in MANAGEMENT_ROLES and report_type != "task":
        return Response({"detail": "Forbidden."}, status=403)
    try:
        title, columns, rows = services.build(
            report_type, filters=request.query_params
        )
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    return Response({"title": title, "columns": columns, "rows": rows})


@api_view(["GET"])
def report_export(request, report_type, fmt):
    if request.user.role not in MANAGEMENT_ROLES and report_type != "task":
        return Response({"detail": "Forbidden."}, status=403)
    try:
        title, columns, rows = services.build(
            report_type, filters=request.query_params
        )
        return export(fmt, title, columns, rows)
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
