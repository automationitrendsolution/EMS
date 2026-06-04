from django.urls import path

from accounts import views

urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_page, name="profile"),
    path("employees/", views.employees_page, name="employees"),
    path("employees/create/", views.employee_create, name="employee-create"),
]
