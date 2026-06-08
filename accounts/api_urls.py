from django.urls import path

from accounts import api_views as v

urlpatterns = [
    path("login/", v.LoginView.as_view(), name="api-login"),
    path("refresh/", v.RefreshView.as_view(), name="api-refresh"),
    path("me/", v.me_view, name="api-me"),
    path("change-password/", v.change_password_view, name="api-change-password"),
    # employees
    path("employees/", v.EmployeeListCreateView.as_view(), name="api-employees"),
    path("employees/<str:pk>/", v.EmployeeDetailView.as_view(), name="api-employee"),
    # org structure
    path("departments/", v.DepartmentListCreateView.as_view(), name="api-departments"),
    path("departments/<str:pk>/", v.DepartmentDetailView.as_view(), name="api-department"),
    path(
        "designations/",
        v.DesignationListCreateView.as_view(),
        name="api-designations",
    ),
    path("teams/", v.TeamListCreateView.as_view(), name="api-teams"),
    # performance goals (KRA / KPI)
    path(
        "performance/",
        v.PerformanceGoalListCreateView.as_view(),
        name="api-performance",
    ),
    path(
        "performance/<str:pk>/",
        v.PerformanceGoalDetailView.as_view(),
        name="api-performance-detail",
    ),
]
