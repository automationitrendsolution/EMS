from django.shortcuts import render

from core.decorators import login_required


@login_required
def reports_page(request):
    return render(request, "reports/index.html", {"active": "reports"})
