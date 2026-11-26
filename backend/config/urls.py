from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from dbapp.api.views import update_summary_from_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("dbapp.api.urls")),
    # path เดียวกับระบบเดิม (djangodashboard) ให้ Task Scheduler ที่ตั้งไว้เปลี่ยนแค่พอร์ต
    path(
        "update_summary_from_api/", update_summary_from_api, name="update-summary-from-api-legacy"
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
