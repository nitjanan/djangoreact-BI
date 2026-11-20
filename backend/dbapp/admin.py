from django.contrib import admin, messages
from django.db import models
from django.forms import CheckboxSelectMultiple
from import_export.admin import ImportExportModelAdmin

from dbapp.forms import BaseCarAdminForm
from dbapp.models import (
    BaseAffiliatedCompany,
    BaseAPI,
    BaseBranchCompany,
    BaseCar,
    BaseCarDepartment,
    BaseCarType,
    BaseRepairType,
    BaseVisible,
    ReportSubscription,
    SummaryCarDep,
    SummaryCarJob,
    SummaryOil,
    SummaryRepair,
    SummaryWork,
    UserProfile,
)


# Register your models here.
class BaseAffiliatedCompanyAdmin(ImportExportModelAdmin):
    list_display = ["id", "name", "name_th"]  # แสดงรายการสินค้าในรูปแบบตาราง
    list_per_page = 20  # แสดงผล 20 รายการต่อ 1 หน้า


class BaseBranchCompanyAdmin(ImportExportModelAdmin):
    list_display = ["id", "code", "affiliated", "name"]  # แสดงรายการสินค้าในรูปแบบตาราง
    list_per_page = 20  # แสดงผล 20 รายการต่อ 1 หน้า


class BaseVisibleAdmin(ImportExportModelAdmin):
    list_display = ("name",)


class UserProfileAdmin(ImportExportModelAdmin):
    formfield_overrides = {
        models.ManyToManyField: {"widget": CheckboxSelectMultiple},
    }
    autocomplete_fields = ["user"]

    list_display = ["user"]  # แสดงรายการสินค้าในรูปแบบตาราง
    list_per_page = 20  # แสดงผล 20 รายการต่อ 1 หน้า
    search_fields = ["user__first_name"]

    class Media:
        js = ("dbapp/js/select_all.js",)


class BaseCarTypeAdmin(ImportExportModelAdmin):
    list_display = ["id", "name"]  # แสดงรายการสินค้าในรูปแบบตาราง
    search_fields = [
        "name",
    ]


class BaseCarDepartmentAdmin(ImportExportModelAdmin):
    list_display = ["id", "name"]  # แสดงรายการสินค้าในรูปแบบตาราง
    search_fields = [
        "name",
    ]


class BaseCarAdmin(ImportExportModelAdmin):
    autocomplete_fields = [
        "car_type",
    ]

    list_display = [
        "id", "code", "name", "car_dep", "car_type", "start_year", "brand", "car_model",
    ]  # fmt: skip
    search_fields = ["code", "name", "car_type__name", "car_dep__name"]
    form = BaseCarAdminForm


class BaseRepairTypeAdmin(ImportExportModelAdmin):
    list_display = ["id", "name"]  # แสดงรายการสินค้าในรูปแบบตาราง
    search_fields = ["name"]


class BaseAPIAdmin(ImportExportModelAdmin):
    list_display = ["id", "url", "apiname", "username", "password"]  # แสดงรายการสินค้าในรูปแบบตาราง
    list_per_page = 20  # แสดงผล 20 รายการต่อ 1 หน้า


class SummaryCarDepAdmin(ImportExportModelAdmin):
    list_display = ["id", "ext_id", "code", "name", "branch_company", "car_dep", "v_stamp"]
    list_filter = ["branch_company", "car_dep"]
    search_fields = ["code", "name"]
    list_per_page = 20  # แสดงผล 20 รายการต่อ 1 หน้า


class SummaryRepairAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "summary_date",
        "year",
        "month_th",
        "repair_id",
        "repair_name",
        "amount",
        "branch_company",
        "car_dep",
        "car_code",
    ]
    list_filter = ["year", "month", "branch_company", "car_dep"]
    search_fields = ["repair_name", "car_code", "car__name"]
    list_per_page = 20  # แสดงผล 20 รายการต่อ 1 หน้า


class SummaryOilAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "summary_date",
        "year",
        "month_th",
        "sum_liter",
        "sum_km",
        "liter_per_km",
        "branch_company",
        "car_dep",
        "car",
    ]
    list_filter = ["year", "month", "branch_company", "car_dep"]
    search_fields = ["car__code", "car__name"]
    list_per_page = 20  # แสดงผล 20 รายการต่อ 1 หน้า


class SummaryWorkAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "summary_date",
        "year",
        "month_th",
        "sum_diff_mile",
        "count_diff_time",
        "percent",
        "branch_company",
        "car_dep",
        "car",
    ]
    list_filter = ["year", "month", "branch_company", "car_dep"]
    search_fields = ["car__code", "car__name"]
    list_per_page = 20  # แสดงผล 20 รายการต่อ 1 หน้า


class SummaryCarJobAdmin(ImportExportModelAdmin):
    list_display = [
        "id",
        "summary_date",
        "car",
        "expense_dept_name",
        "job",
        "hours",
        "km",
        "trips",
        "branch_company",
        "car_dep",
    ]
    list_filter = ["year", "month", "branch_company", "car_dep", "expense_dept_name"]
    search_fields = ["car__code", "car__name", "job", "expense_dept_name"]
    list_per_page = 20


class ReportSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "name",
        "weekly",
        "monthly",
        "company_names",
        "is_active",
        "auto_login",
        "login_user",
        "last_weekly_period",
        "last_monthly_period",
    ]
    list_filter = ["is_active", "weekly", "monthly", "auto_login"]
    search_fields = ["email", "name"]
    formfield_overrides = {
        models.ManyToManyField: {"widget": CheckboxSelectMultiple},
    }
    readonly_fields = ["last_weekly_period", "last_monthly_period"]
    actions = ["send_weekly_now", "send_monthly_now"]

    @admin.display(description="user ที่ใช้ลิงก์อัตโนมัติ")
    def login_user(self, obj):
        from dbapp.reports.login_link import user_for_email

        if not obj.auto_login:
            return "ปิด"
        user = user_for_email(obj.email)
        return user.get_username() if user else "ไม่มี (ต้อง login เอง)"

    @admin.display(description="บริษัท")
    def company_names(self, obj):
        return ", ".join(c.name or c.code for c in obj.companies.all()) or "ทุกบริษัท"

    def _send_now(self, request, queryset, frequency):
        from dbapp.reports.send import send_reports

        result = send_reports(frequency, subscriptions=queryset, force=True)
        label = f"{result.period.title} {result.period.label}"
        if result.sent:
            self.message_user(request, f"ส่ง{label} ให้ {len(result.sent)} คนแล้ว")
        for email, error in result.failed:
            self.message_user(request, f"ส่งให้ {email} ไม่สำเร็จ: {error}", messages.ERROR)

    @admin.action(description="ส่งรายงานรายสัปดาห์ (สัปดาห์ที่แล้ว) ตอนนี้")
    def send_weekly_now(self, request, queryset):
        self._send_now(request, queryset, "weekly")

    @admin.action(description="ส่งรายงานรายเดือน (เดือนที่แล้ว) ตอนนี้")
    def send_monthly_now(self, request, queryset):
        self._send_now(request, queryset, "monthly")


admin.site.register(BaseAffiliatedCompany, BaseAffiliatedCompanyAdmin)
admin.site.register(BaseBranchCompany, BaseBranchCompanyAdmin)
admin.site.register(BaseVisible, BaseVisibleAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(BaseCarType, BaseCarTypeAdmin)
admin.site.register(BaseCarDepartment, BaseCarDepartmentAdmin)
admin.site.register(BaseCar, BaseCarAdmin)
admin.site.register(BaseRepairType, BaseRepairTypeAdmin)
admin.site.register(BaseAPI, BaseAPIAdmin)
admin.site.register(SummaryCarDep, SummaryCarDepAdmin)
admin.site.register(SummaryRepair, SummaryRepairAdmin)
admin.site.register(SummaryOil, SummaryOilAdmin)
admin.site.register(SummaryWork, SummaryWorkAdmin)
admin.site.register(SummaryCarJob, SummaryCarJobAdmin)
admin.site.register(ReportSubscription, ReportSubscriptionAdmin)
