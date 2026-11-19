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
        fields = ["id", "username", "first_name", "last_name", "email", "is_staff", "is_superuser"]


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


class CarSeriesChartSerializer(SeriesTotalChartSerializer):
    companies = _labels()


class HeatmapRowSerializer(serializers.Serializer):
    name = serializers.CharField()
    company = serializers.CharField()
    data = _floats()


class HeatmapChartSerializer(serializers.Serializer):
    labels = _labels()
    rows = HeatmapRowSerializer(many=True)


class ChartsSerializer(serializers.Serializer):
    repair_by_type = SeriesTotalChartSerializer()
    repair_by_car_type = SeriesTotalChartSerializer()
    repair_by_month = SeriesChartSerializer()
    repair_by_car = CarSeriesChartSerializer()
    oil_by_month = OilChartSerializer()
    work_by_month = WorkChartSerializer()
    repair_vs_work = RepairVsWorkChartSerializer()
    repair_heatmap = HeatmapChartSerializer()


class ReliabilityTrendSerializer(serializers.Serializer):
    labels = _labels()
    count = serializers.ListField(child=serializers.IntegerField())
    mttr = serializers.ListField(child=serializers.FloatField(allow_null=True))


class TopCarsSerializer(serializers.Serializer):
    labels = _labels()
    companies = _labels()
    count = serializers.ListField(child=serializers.IntegerField())


class ReliabilitySerializer(serializers.Serializer):
    failure_count = serializers.IntegerField()
    repair_closed = serializers.IntegerField()
    mtbf = serializers.FloatField(allow_null=True)
    mttr = serializers.FloatField(allow_null=True)
    availability = serializers.FloatField(allow_null=True)
    trend = ReliabilityTrendSerializer()
    top_cars = TopCarsSerializer()


class UnmatchedRowSerializer(serializers.Serializer):
    remark = serializers.CharField()
    branch_company_name = serializers.CharField()
    repair_amount = serializers.FloatField()
    oil_qty = serializers.FloatField()


class UnmatchedSerializer(serializers.Serializer):
    rows = UnmatchedRowSerializer(many=True)
    repair_total = serializers.FloatField()
    oil_total = serializers.FloatField()


class OpenJobBucketSerializer(serializers.Serializer):
    label = serializers.CharField()
    count = serializers.IntegerField()


class OpenJobStageSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class OpenJobDocumentSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["RQ", "PO"])
    ref_no = serializers.CharField(allow_blank=True, allow_null=True)


class PartSerializer(serializers.Serializer):
    docnum = serializers.CharField()
    docdat = serializers.DateField(allow_null=True)
    stkcod = serializers.CharField()
    name = serializers.CharField(allow_blank=True)
    qty = serializers.FloatField()
    unit = serializers.CharField(allow_blank=True)
    amount = serializers.FloatField()


class OpenJobSerializer(serializers.Serializer):
    ext_id = serializers.IntegerField()
    ref_no = serializers.CharField(allow_blank=True)
    car_id = serializers.IntegerField(allow_null=True)
    branch_company_id = serializers.CharField(allow_blank=True)
    branch_company_name = serializers.CharField(allow_blank=True)
    code = serializers.CharField(allow_blank=True)
    name = serializers.CharField(allow_null=True)
    reported_at = serializers.DateTimeField()
    days = serializers.IntegerField()
    immobile = serializers.BooleanField()
    broke_reason = serializers.CharField(allow_blank=True)
    stage = serializers.CharField()
    stage_label = serializers.CharField()
    stage_days = serializers.IntegerField(allow_null=True)
    po_due = serializers.DateField(allow_null=True)
    po_overdue = serializers.BooleanField()
    documents = OpenJobDocumentSerializer(many=True)
    parts = PartSerializer(many=True)
    parts_amount = serializers.FloatField()


class OpenJobsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    car_count = serializers.IntegerField()
    immobile_car_count = serializers.IntegerField()
    stale_count = serializers.IntegerField()
    stale_days = serializers.IntegerField()
    has_process = serializers.BooleanField()
    buckets = OpenJobBucketSerializer(many=True)
    stages = OpenJobStageSerializer(many=True)
    jobs = OpenJobSerializer(many=True)


class TopPartSerializer(serializers.Serializer):
    stkcod = serializers.CharField()
    name = serializers.CharField(allow_blank=True)
    unit = serializers.CharField(allow_blank=True)
    qty = serializers.FloatField()
    amount = serializers.FloatField()
    jobs = serializers.IntegerField()


class PartsJobSerializer(serializers.Serializer):
    ext_id = serializers.IntegerField()
    ref_no = serializers.CharField(allow_blank=True)
    reported_at = serializers.DateTimeField()
    broke_reason = serializers.CharField(allow_blank=True)
    closed = serializers.BooleanField()
    amount = serializers.FloatField()
    parts = PartSerializer(many=True)


WATCH_REASONS = ["stale", "cost", "repeat", "failure", "fuel"]


class WatchReasonSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=WATCH_REASONS)
    label = serializers.CharField()
    detail = serializers.CharField()


class WatchCarSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    branch_company_id = serializers.CharField()
    branch_company_name = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    repair_total = serializers.FloatField()
    failure_count = serializers.IntegerField()
    reasons = WatchReasonSerializer(many=True)


class WatchReasonCountSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=WATCH_REASONS)
    label = serializers.CharField()
    count = serializers.IntegerField()


class WatchlistSerializer(serializers.Serializer):
    car_count = serializers.IntegerField()
    compared = serializers.BooleanField()
    reasons = WatchReasonCountSerializer(many=True)
    cars = WatchCarSerializer(many=True)


class PartsSerializer(serializers.Serializer):
    job_count = serializers.IntegerField()
    jobs_with_parts = serializers.IntegerField()
    amount = serializers.FloatField()
    amount_per_job = serializers.FloatField(allow_null=True)
    top = TopPartSerializer(many=True)
    jobs = PartsJobSerializer(many=True)


class InsightTargetSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    branch_company_id = serializers.CharField()


class InsightItemSerializer(serializers.Serializer):
    severity = serializers.ChoiceField(choices=["high", "medium", "good", "info"])
    kind = serializers.ChoiceField(choices=["urgent", "anomaly", "efficiency", "trend", "data"])
    title = serializers.CharField()
    detail = serializers.CharField()
    target = InsightTargetSerializer(allow_null=True)
    action = serializers.CharField(allow_null=True)


class InsightsSerializer(serializers.Serializer):
    overview = serializers.ListField(child=serializers.CharField())
    items = InsightItemSerializer(many=True)


class DashboardSerializer(serializers.Serializer):
    filters = DashboardFiltersSerializer()
    car_types = CarTypeSerializer(many=True)
    selected_car = CarRowSerializer(allow_null=True)
    car_table = CarTableSerializer()
    charts = ChartsSerializer()
    reliability = ReliabilitySerializer()
    unmatched = UnmatchedSerializer()
    open_jobs = OpenJobsSerializer()
    parts = PartsSerializer()
    watchlist = WatchlistSerializer()
    insights = InsightsSerializer()


# ------------------------------------------------------------------ sync


class SyncResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    result = serializers.DictField()
