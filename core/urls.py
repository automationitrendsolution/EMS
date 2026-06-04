from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("settings/", views.settings_page, name="settings"),
]
