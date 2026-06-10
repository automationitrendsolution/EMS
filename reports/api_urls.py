from django.urls import path

from reports import api_views as v

urlpatterns = [
    path("filter-options/", v.filter_options, name="api-report-filter-options"),
    path("<str:report_type>/", v.report_data, name="api-report"),
    path("<str:report_type>/export/<str:fmt>/", v.report_export, name="api-report-export"),
]
