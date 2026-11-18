from django.contrib.auth import get_user_model
from rest_framework import serializers

from dbapp.models import BaseBranchCompany, BaseCar, BaseCarDepartment, BaseCarType

# ------------------------------------------------------------------ auth / me


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"}, trim_whitespace=False)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "username", "first_name", "last_name", "email", "is_staff"]


class CompanySerializer(serializers.ModelSerializer):
    affiliated_name_sh = serializers.CharField(
        source="affiliated.name_sh", default=None, allow_null=True
    )

    class Meta:
        model = BaseBranchCompany
        fields = ["id", "code", "name", "affiliated_name_sh"]


class MeSerializer(serializers.Serializer):
    """แทน context processor เดิม (companyVisibleTab / userVisibleTab)"""

    user = UserSerializer()
    companies = CompanySerializer(many=True)
    visible_tabs = serializers.ListField(child=serializers.CharField())
    default_company = serializers.CharField(allow_null=True)


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()


# --------------------------------------------------------------- lookups


class CarDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseCarDepartment
        fields = ["id", "name"]


class CarTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseCarType
        fields = ["id", "name"]


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseCar
        fields = ["id", "code", "name", "car_dep", "car_type"]


# ------------------------------------------------------------- dashboard


class DashboardQuerySerializer(serializers.Serializer):
    company = serializers.CharField(help_text='รหัสบริษัท (BaseBranchCompany.code) หรือ "ALL"')
    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    car_dep = serializers.IntegerField(required=False, default=1)
    car_type = serializers.IntegerField(required=False, allow_null=True, default=None)
    car_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    branch_company_id = serializers.CharField(required=False, allow_null=True, default=None)


class DashboardFiltersSerializer(serializers.Serializer):
    company = serializers.CharField()
    year = serializers.IntegerField()
    car_dep = serializers.IntegerField()
    car_type = serializers.IntegerField(allow_null=True)
    car_id = serializers.IntegerField(allow_null=True)
    branch_company_id = serializers.CharField(allow_null=True)


class CarRowSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    branch_company_id = serializers.CharField()
    branch_company_name = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    percent_ma = serializers.FloatField()
    avg_work_per_day = serializers.FloatField()
    work_total = serializers.FloatField()
    oil_total = serializers.FloatField()
    fuel_rate = serializers.FloatField()
    repair_total = serializers.FloatField()
    repair_cost_per_hr = serializers.FloatField()
    failure_count = serializers.IntegerField()
    mtbf = serializers.FloatField(allow_null=True)
    mttr = serializers.FloatField(allow_null=True)


class CarTotalsSerializer(serializers.Serializer):
    percent_ma = serializers.FloatField()
    avg_work_per_day = serializers.FloatField()
    work_total = serializers.FloatField()
    oil_total = serializers.FloatField()
    fuel_rate = serializers.FloatField()
    repair_total = serializers.FloatField()
    repair_cost_per_hr = serializers.FloatField()
    failure_count = serializers.IntegerField()
    mtbf = serializers.FloatField(allow_null=True)
    mttr = serializers.FloatField(allow_null=True)


class CarTableSerializer(serializers.Serializer):
    rows = CarRowSerializer(many=True)
    totals = CarTotalsSerializer()


def _floats():
    return serializers.ListField(child=serializers.FloatField())


def _labels():
    return serializers.ListField(child=serializers.CharField())


class SeriesChartSerializer(serializers.Serializer):
    labels = _labels()
    series = _floats()


class SeriesTotalChartSerializer(SeriesChartSerializer):
    total = serializers.FloatField()


class OilChartSerializer(serializers.Serializer):
    labels = _labels()
    liters = _floats()
    liter_per_km = _floats()


class WorkChartSerializer(serializers.Serializer):
    labels = _labels()
    hours = _floats()
    percent = _floats()


class RepairVsWorkChartSerializer(serializers.Serializer):
    labels = _labels()
    repair = _floats()
    work = _floats()


class ChartsSerializer(serializers.Serializer):
    repair_by_type = SeriesTotalChartSerializer()
    repair_by_car_type = SeriesTotalChartSerializer()
    repair_by_month = SeriesChartSerializer()
    repair_by_car = SeriesTotalChartSerializer()
    oil_by_month = OilChartSerializer()
    work_by_month = WorkChartSerializer()
    repair_vs_work = RepairVsWorkChartSerializer()


class ReliabilityTrendSerializer(serializers.Serializer):
    labels = _labels()
    count = serializers.ListField(child=serializers.IntegerField())
    mttr = serializers.ListField(child=serializers.FloatField(allow_null=True))


class TopCarsSerializer(serializers.Serializer):
    labels = _labels()
    count = serializers.ListField(child=serializers.IntegerField())


class ReliabilitySerializer(serializers.Serializer):
    failure_count = serializers.IntegerField()
    repair_closed = serializers.IntegerField()
    mtbf = serializers.FloatField(allow_null=True)
    mttr = serializers.FloatField(allow_null=True)
    availability = serializers.FloatField(allow_null=True)
    trend = ReliabilityTrendSerializer()
    top_cars = TopCarsSerializer()


class DashboardSerializer(serializers.Serializer):
    filters = DashboardFiltersSerializer()
    car_types = CarTypeSerializer(many=True)
    selected_car = CarRowSerializer(allow_null=True)
    car_table = CarTableSerializer()
    charts = ChartsSerializer()
    reliability = ReliabilitySerializer()


# ------------------------------------------------------------------ sync


class SyncResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    result = serializers.DictField()
