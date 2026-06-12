from django.urls import path

from accounts import views

urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_page, name="profile"),
    path("departments/", views.departments_page, name="departments"),
    path("departments/create/", views.department_create, name="department-create"),
    path("departments/<str:pk>/edit/", views.department_edit, name="department-edit"),
    path("employees/", views.employees_page, name="employees"),
    path("employees/create/", views.employee_create, name="employee-create"),
    path("employees/<str:pk>/edit/", views.employee_edit, name="employee-edit"),
    path(
        "employees/<str:pk>/performance/",
        views.employee_performance_page,
        name="employee-performance",
    ),
    path("performance/", views.my_performance_page, name="my-performance"),
    path("employee-errors/", views.employee_errors_page, name="employee-errors"),
]
