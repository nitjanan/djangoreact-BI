from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("car-departments", views.CarDepartmentViewSet)
router.register("car-types", views.CarTypeViewSet)
router.register("cars", views.CarViewSet)

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/report-login/", views.ReportLoginView.as_view(), name="auth-report-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/password-reset/", views.PasswordResetView.as_view(), name="password-reset"),
    path(
        "auth/password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("me/", views.MeView.as_view(), name="me"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("sync/", views.SyncAllView.as_view(), name="sync-all"),
    path("sync/summary/", views.SyncSummaryView.as_view(), name="sync-summary"),
    path("sync/base/", views.SyncBaseView.as_view(), name="sync-base"),
    *router.urls,
]
