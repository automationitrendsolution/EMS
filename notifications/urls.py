from django.urls import path

from notifications import views

urlpatterns = [
    path("", views.notifications_page, name="notifications"),
]
