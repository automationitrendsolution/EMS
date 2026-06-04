from django.urls import path

from reports import views

urlpatterns = [
    path("", views.reports_page, name="reports"),
]
