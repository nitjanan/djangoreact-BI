import ipaddress
from datetime import date

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import HttpResponse
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from dbapp.models import BaseCar, BaseCarDepartment, BaseCarType
from dbapp.services import sync
from dbapp.services.car_history import CarNotFound, build_car_history
from dbapp.services.dashboard import (
    OTHER_CAR_DEP,
    CompanyAccessDenied,
    DashboardFilters,
    build_dashboard,
    user_companies,
    user_visible_tabs,
)
from dbapp.services.external_api import WebstockNotConfigured

from . import serializers as s

# ---------------------------------------------------------------- auth


def me_payload(user):
    companies = list(user_companies(user).select_related("affiliated"))
    return s.MeSerializer(
        {
            "user": user,
            "companies": companies,
            "visible_tabs": user_visible_tabs(user),
            # เดิม: ตอน login เลือกบริษัทแรกของ user ไว้ใน session
            "default_company": companies[0].code if companies else None,
        }
    ).data


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """เรียกครั้งแรกตอนเปิดแอป เพื่อให้ browser ได้ cookie fleet_csrftoken"""

    permission_classes = [AllowAny]

    @extend_schema(responses=s.DetailSerializer)
    def get(self, request):
        return Response({"detail": "CSRF cookie set"})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=s.LoginSerializer, responses={200: s.MeSerializer})
    def post(self, request):
        ser = s.LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = authenticate(request, **ser.validated_data)
        if user is None:
            return Response({"detail": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response(me_payload(user))


@method_decorator(csrf_protect, name="dispatch")
class ReportLoginView(APIView):
    """เข้าสู่ระบบจากลิงก์ในอีเมลรายงาน (หน้า /auto-login ส่ง token มา) ใช้ได้ครั้งเดียว"""

    permission_classes = [AllowAny]

    @extend_schema(request=s.ReportLoginSerializer, responses={200: s.MeSerializer})
    def post(self, request):
        from dbapp.reports.login_link import check_token

        ser = s.ReportLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = check_token(ser.validated_data["token"])
        if user is None:
            return Response(
                {"detail": "ลิงก์เข้าสู่ระบบหมดอายุหรือถูกใช้ไปแล้ว กรุณาเข้าสู่ระบบด้วยรหัสผ่าน"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # login() อัปเดต last_login -> token นี้ใช้ซ้ำไม่ได้
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(me_payload(user))


class LogoutView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    @extend_schema(responses=s.MeSerializer)
    def get(self, request):
        return Response(me_payload(request.user))


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetView(APIView):
    """ส่งลิงก์ไปที่หน้า React: {FRONTEND_URL}/reset-password/{uid}/{token}"""

    permission_classes = [AllowAny]

    @extend_schema(request=s.PasswordResetSerializer, responses=s.DetailSerializer)
    def post(self, request):
        ser = s.PasswordResetSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        for user in PasswordResetForm().get_users(ser.validated_data["email"]):
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
            send_mail(
                "ตั้งรหัสผ่านใหม่ - STG Dashboard",
                f"คลิกลิงก์นี้เพื่อตั้งรหัสผ่านใหม่ของบัญชี {user.get_username()}\n\n{link}\n",
                None,
                [user.email],
            )

        # ตอบเหมือนกันเสมอ ไม่บอกว่าอีเมลมีในระบบหรือไม่
        return Response({"detail": "หากอีเมลนี้มีในระบบ เราได้ส่งลิงก์ตั้งรหัสผ่านใหม่ให้แล้ว"})


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=s.PasswordResetConfirmSerializer, responses=s.DetailSerializer)
    def post(self, request):
        ser = s.PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        user_model = get_user_model()
        try:
            user = user_model.objects.get(pk=force_str(urlsafe_base64_decode(data["uid"])))
        except (ValueError, TypeError, OverflowError, user_model.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, data["token"]):
            return Response(
                {"detail": "ลิงก์ตั้งรหัสผ่านไม่ถูกต้องหรือหมดอายุแล้ว"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        form = SetPasswordForm(
            user, {"new_password1": data["new_password"], "new_password2": data["new_password"]}
        )
        if not form.is_valid():
            return Response(
                {"new_password": form.errors.get("new_password2", form.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        form.save()
        return Response({"detail": "ตั้งรหัสผ่านใหม่เรียบร้อยแล้ว"})


# ------------------------------------------------------------- lookups


class CarDepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    # id 4 ไม่แสดงในตัวเลือกแผนก (เหมือนหน้าเดิม)
    queryset = BaseCarDepartment.objects.exclude(id=4)
    serializer_class = s.CarDepartmentSerializer
    pagination_class = None

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # แท็บสุดท้าย: ข้อมูลที่ไม่มีแผนก (รถที่ยังไม่ได้ตั้งแผนก + รายการที่จับคู่กับรถไม่ได้)
        response.data = [*response.data, {"id": OTHER_CAR_DEP, "name": "อื่นๆ"}]
        return response


class CarTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BaseCarType.objects.all()
    serializer_class = s.CarTypeSerializer
    pagination_class = None


class CarViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BaseCar.objects.all()
    serializer_class = s.CarSerializer
    filterset_fields = ["car_dep", "car_type", "code"]
    pagination_class = None


# ----------------------------------------------------------- dashboard


class DashboardView(APIView):
    @extend_schema(parameters=[s.DashboardQuerySerializer], responses=s.DashboardSerializer)
    def get(self, request):
        query = s.DashboardQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data

        filters = DashboardFilters(
            company=params["company"],
            year=params.get("year") or date.today().year,
            month_from=params["month_from"],
            month_to=params["month_to"],
            car_dep=params["car_dep"],
            car_type=params["car_type"],
            brand=params["brand"] or None,
            car_id=params["car_id"],
            branch_company_id=params["branch_company_id"],
        )
        try:
            data = build_dashboard(request.user, filters)
        except CompanyAccessDenied as exc:
            raise PermissionDenied("คุณไม่มีสิทธิ์ดูข้อมูลของบริษัทนี้") from exc

        return Response(s.DashboardSerializer(data).data)


class CarHistoryView(APIView):
    """ประวัติรถรายคัน (หน้า /car/:car_id) — ทุกช่วงที่ sync มา ไม่กรองปี"""

    @extend_schema(parameters=[s.CarHistoryQuerySerializer], responses=s.CarHistorySerializer)
    def get(self, request, car_id):
        query = s.CarHistoryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        try:
            data = build_car_history(
                request.user, car_id, query.validated_data["branch_company_id"]
            )
        except CompanyAccessDenied as exc:
            raise PermissionDenied("คุณไม่มีสิทธิ์ดูข้อมูลของบริษัทนี้") from exc
        except CarNotFound as exc:
            raise NotFound("ไม่พบรถคันนี้") from exc
        return Response(s.CarHistorySerializer(data).data)


# ---------------------------------------------------------------- sync


class IsSuperUser(BasePermission):
    """ปุ่มอัปเดตข้อมูลในหน้าเดิมแสดงเฉพาะ superuser"""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class SyncAllView(APIView):
    permission_classes = [IsSuperUser]

    """ปุ่ม "อัปเดตข้อมูล": base + summary ตั้งแต่ต้นปี (เดิม: updateValueAPI)"""

    @extend_schema(request=None, responses=s.SyncResultSerializer)
    def post(self, request):
        return Response({"status": "ok", "result": sync.run_full_sync()})


class SyncSummaryView(APIView):
    permission_classes = [IsSuperUser]

    """summary ย้อนหลัง 3 เดือน (เดิม: update_summary_from_api)"""

    @extend_schema(request=None, responses=s.SyncResultSerializer)
    def post(self, request):
        return Response({"status": "ok", "result": sync.run_recent_summary_sync()})


def _is_local_request(request):
    """เรียกจากเครื่อง server เอง (127.0.0.1/::1) และไม่ได้ผ่าน reverse proxy

    reverse proxy บนเครื่องเดียวกันทำให้ทุกคำขอดูเหมือนมาจาก 127.0.0.1
    จึงถือว่าไม่ใช่ local ถ้ามี header ที่ proxy ใส่มา (X-Forwarded-For / Forwarded)
    """
    if request.headers.get("X-Forwarded-For") or request.headers.get("Forwarded"):
        return False
    try:
        return ipaddress.ip_address(request.META.get("REMOTE_ADDR", "")).is_loopback
    except ValueError:
        return False


def update_summary_from_api(request):
    """งานอัปเดตอัตโนมัติทุกวัน (Task Scheduler/cron เรียก): base + ข้อมูลสรุปย้อนหลัง 3 เดือน

    เรียกได้ 2 แบบ (เหมือนระบบเดิมที่เปิด URL บนเครื่อง server ได้เลย):
    - จากเครื่อง server เอง: http://127.0.0.1:8003/update_summary_from_api/ ไม่ต้องใส่รหัส
      (เฉพาะเมื่อตั้ง ALLOW_LOCAL_SYNC_WITHOUT_TOKEN=true ใน .env ค่าเริ่มต้นปิด)
    - จากเครื่องอื่น: ส่งรหัส SYNC_TOKEN ใน header X-Sync-Token เท่านั้น
      (ไม่รับใน URL เพราะจะติดไปใน log/ประวัติเบราว์เซอร์ และไม่ใช้ session login
      เพราะเป็น GET: เว็บอื่นแค่ฝังลิงก์ก็สั่ง sync แทน superuser ได้ — ปุ่มบน dashboard ใช้ /api/sync/)
    แต่ละขั้นที่ดึงไม่ได้จะข้ามไป (ดู sync_summary) ตอบเป็นข้อความธรรมดา
    """
    token = request.headers.get("X-Sync-Token", "")
    has_token = bool(settings.SYNC_TOKEN) and constant_time_compare(token, settings.SYNC_TOKEN)
    local_ok = settings.ALLOW_LOCAL_SYNC_WITHOUT_TOKEN and _is_local_request(request)
    if not (has_token or local_ok):
        return HttpResponse("forbidden", status=403, content_type="text/plain; charset=utf-8")
    try:
        result = sync.run_daily_sync()
    except WebstockNotConfigured:
        # ส่งข้อความคงที่ ไม่ใช่ str(exception) กันรายละเอียดภายในหลุดออกไป (CodeQL py/stack-trace-exposure)
        return HttpResponse(
            str(WebstockNotConfigured.default_detail),
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    steps = {**result["base"], **result["summary"]}
    if not any(steps.values()):
        # ไม่ได้ข้อมูลเลยสักขั้น (webstock ล่ม/login ไม่ได้) ให้ scheduler เห็นว่าไม่สำเร็จ
        return HttpResponse(
            f"update summary from api failed: {', '.join(steps)}",
            status=502,
            content_type="text/plain; charset=utf-8",
        )
    return HttpResponse("update summary from api success")


class SyncBaseView(APIView):
    permission_classes = [IsSuperUser]

    """ข้อมูลหลัก รถ/ชนิด/แผนก/ประเภทซ่อม (เดิม: update_base_from_api)"""

    @extend_schema(request=None, responses=s.SyncResultSerializer)
    def post(self, request):
        return Response({"status": "ok", "result": sync.sync_base_data()})
