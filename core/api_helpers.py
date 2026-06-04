"""Helpers for paginating MongoEngine querysets inside DRF views."""
from rest_framework.response import Response


def paginate(request, queryset, repr_fn, default_size=20, max_size=100):
    """Paginate a MongoEngine queryset and return a DRF Response.

    Query params: ``page`` (1-based) and ``page_size``.
    """
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(request.query_params.get("page_size", default_size))
    except (TypeError, ValueError):
        size = default_size
    size = max(1, min(size, max_size))

    total = queryset.count()
    start = (page - 1) * size
    items = queryset.skip(start).limit(size)
    results = [repr_fn(obj) for obj in items]
    total_pages = (total + size - 1) // size
    return Response(
        {
            "count": total,
            "page": page,
            "page_size": size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "results": results,
        }
    )
