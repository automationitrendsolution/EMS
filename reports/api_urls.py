from django.urls import path

from reports import api_views as v

urlpatterns = [
    path("<str:report_type>/", v.report_data, name="api-report"),
    path("<str:report_type>/export/<str:fmt>/", v.report_export, name="api-report-export"),
]
