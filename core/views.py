from django.shortcuts import redirect

from core.decorators import login_required


def home(request):
    if getattr(request, "current_user", None):
        return redirect("/dashboard/")
    return redirect("/login/")


@login_required
def settings_page(request):
    from django.shortcuts import render

    return render(request, "settings.html", {"active": "settings"})
