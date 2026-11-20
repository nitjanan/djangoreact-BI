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
        fields = ["id", "code", "name", "car_dep", "car_type", "start_year", "brand", "car_model"]


# ------------------------------------------------------------- dashboard


class DashboardQuerySerializer(serializers.Serializer):
    company = serializers.CharField(help_text='รหัสบริษัท (BaseBranchCompany.code) หรือ "ALL"')
    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    month_from = serializers.IntegerField(
        required=False, allow_null=True, default=None, min_value=1, max_value=12
    )
    month_to = serializers.IntegerField(
        required=False, allow_null=True, default=None, min_value=1, max_value=12
    )
    car_dep = serializers.IntegerField(required=False, default=1)
    car_type = serializers.IntegerField(required=False, allow_null=True, default=None)
    car_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    branch_company_id = serializers.CharField(required=False, allow_null=True, default=None)


class DashboardFiltersSerializer(serializers.Serializer):
    company = serializers.CharField()
    year = serializers.IntegerField()
    month_from = serializers.IntegerField()
    month_to = serializers.IntegerField()
    years = serializers.ListField(child=serializers.IntegerField())
    car_dep = serializers.IntegerField()
    fuel_field = serializers.ChoiceField(
        choices=["fuel_rate", "liter_per_km"],
        help_text="ค่าที่ใช้เป็นอัตราการใช้น้ำมันของแผนกนี้ (รถบรรทุก = ลิตร/กม.)",
    )
    fuel_unit = serializers.CharField()
    unit_noun = serializers.CharField(help_text="ชื่อแผนกที่เลือก ใช้แทนคำว่า รถ บนหน้าเว็บ")
    car_type = serializers.IntegerField(allow_null=True)
    car_id = serializers.IntegerField(allow_null=True)
    branch_company_id = serializers.CharField(allow_null=True)


class CarRowSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    branch_company_id = serializers.CharField()
    branch_company_name = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    start_year = serializers.IntegerField(allow_null=True, help_text="ปีที่เริ่มใช้งาน (ค.ศ.)")
    brand = serializers.CharField(allow_null=True)
    car_model = serializers.CharField(allow_null=True)
    age = serializers.IntegerField(allow_null=True, help_text="อายุ (ปี) ณ ปีที่เลือก")
    car_type_id = serializers.IntegerField(allow_null=True)
    car_type_name = serializers.CharField(allow_null=True)
    percent_ma = serializers.FloatField()
    avg_work_per_day = serializers.FloatField()
    work_total = serializers.FloatField()
    oil_total = serializers.FloatField()
    fuel_rate = serializers.FloatField()
    km_total = serializers.FloatField(help_text="กม. จากเลขไมล์ในเดือนที่เติมน้ำมัน")
    liter_per_km = serializers.FloatField()
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
    km_total = serializers.FloatField(help_text="กม. จากเลขไมล์ในเดือนที่เติมน้ำมัน")
    liter_per_km = serializers.FloatField()
    repair_total = serializers.FloatField()
    repair_cost_per_hr = serializers.FloatField()
    failure_count = serializers.IntegerField()
    mtbf = serializers.FloatField(allow_null=True)
    mttr = serializers.FloatField(allow_null=True)


class CompareSerializer(serializers.Serializer):
    """ช่วงเดียวกันของปีก่อน"""

    year = serializers.IntegerField()
    month_from = serializers.IntegerField()
    month_to = serializers.IntegerField()
    has_data = serializers.BooleanField()
    repair_total = serializers.FloatField()
    totals = CarTotalsSerializer(allow_null=True)


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
    car_id = serializers.IntegerField(allow_null=True)
    branch_company_id = serializers.CharField(allow_null=True)
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


WATCH_REASONS = ["stale", "cost", "replace", "repeat", "failure", "fuel"]


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


class InsightCompareSerializer(serializers.Serializer):
    """ตัวเลข 2 ค่าแสดงคู่กัน: ค่าที่ผิดปกติ vs ค่าปกติ"""

    value = serializers.FloatField()
    baseline = serializers.FloatField()
    value_text = serializers.CharField()
    baseline_text = serializers.CharField()
    value_label = serializers.CharField()
    baseline_label = serializers.CharField()


class InsightCarSerializer(serializers.Serializer):
    name = serializers.CharField()
    company = serializers.CharField()
    value = serializers.CharField()
    target = InsightTargetSerializer(allow_null=True)


class InsightItemSerializer(serializers.Serializer):
    severity = serializers.ChoiceField(choices=["high", "medium", "good", "info"])
    kind = serializers.ChoiceField(choices=["urgent", "anomaly", "efficiency", "trend", "data"])
    title = serializers.CharField()
    detail = serializers.CharField()
    target = InsightTargetSerializer(allow_null=True)
    action = serializers.CharField(allow_null=True)
    compare = InsightCompareSerializer(allow_null=True)
    cars = InsightCarSerializer(many=True)
    points = serializers.ListField(child=serializers.CharField())
    hint = serializers.CharField(allow_blank=True)


class OverviewFactSerializer(serializers.Serializer):
    """ตัวเลขสรุป 1 ช่อง: หัวข้อสั้น + ตัวเลขใหญ่ + คำอธิบาย"""

    label = serializers.CharField()
    value = serializers.CharField()
    note = serializers.CharField(allow_blank=True)
    share = serializers.FloatField(allow_null=True, help_text="สัดส่วน 0-100 แสดงเป็นแถบ")
    tone = serializers.ChoiceField(choices=["bad", "good"], allow_null=True)


class InsightsSerializer(serializers.Serializer):
    overview = OverviewFactSerializer(many=True)
    items = InsightItemSerializer(many=True)


class JobItemSerializer(serializers.Serializer):
    job = serializers.CharField()
    hours = serializers.FloatField()
    km = serializers.FloatField()
    trips = serializers.IntegerField()
    cars = serializers.IntegerField()


class JobDepartmentSerializer(serializers.Serializer):
    name = serializers.CharField()
    assigned = serializers.BooleanField(help_text="false = ไม่ได้ระบุแผนกค่าใช้จ่ายในบันทึก")
    hours = serializers.FloatField()
    km = serializers.FloatField()
    trips = serializers.IntegerField()
    cars = serializers.IntegerField()
    jobs = JobItemSerializer(many=True)


class JobsSerializer(serializers.Serializer):
    """งานที่ทำจากบันทึกการใช้รถ แยกตามแผนกค่าใช้จ่าย"""

    hours = serializers.FloatField()
    km = serializers.FloatField()
    trips = serializers.IntegerField()
    departments = JobDepartmentSerializer(many=True)


class ModelComparisonRowSerializer(serializers.Serializer):
    car_type_id = serializers.IntegerField(allow_null=True)
    car_type_name = serializers.CharField()
    brand = serializers.CharField()
    car_model = serializers.CharField(allow_null=True)
    cars = serializers.IntegerField()
    avg_age = serializers.FloatField(allow_null=True, help_text="เฉลี่ยเฉพาะคันที่รู้ปีที่เริ่มใช้งาน")
    work_total = serializers.FloatField(help_text="ชั่วโมงรวมของคันที่ชั่วโมง > 0 (ใช้คิดค่าต่อชั่วโมง)")
    repair_total = serializers.FloatField()
    repair_cost_per_hr = serializers.FloatField(allow_null=True)
    type_repair_cost_per_hr = serializers.FloatField(
        allow_null=True, help_text="ต้นทุนซ่อม/ชม. ของทั้งชนิดรถนี้ (รวมคันที่ไม่ได้กรอกยี่ห้อ)"
    )
    vs_type = serializers.FloatField(
        allow_null=True, help_text="ต้นทุนซ่อม/ชม. ของรุ่นนี้ ÷ ของทั้งชนิดรถ (1 = เท่ากัน)"
    )
    fuel = serializers.FloatField(allow_null=True, help_text="หน่วยตาม filters.fuel_unit")
    failure_count = serializers.IntegerField()
    mtbf = serializers.FloatField(allow_null=True)
    percent_ma = serializers.FloatField(allow_null=True)


class ModelComparisonSerializer(serializers.Serializer):
    """เทียบยี่ห้อ/รุ่นภายในชนิดรถเดียวกัน"""

    rows = ModelComparisonRowSerializer(many=True)
    min_cars = serializers.IntegerField(help_text="รุ่นที่มีรถน้อยกว่านี้ยังสรุปไม่ได้")
    total_cars = serializers.IntegerField()
    missing_cars = serializers.IntegerField(help_text="คันที่ยังไม่ได้กรอกยี่ห้อใน webstock")


class BenchmarkMetricsSerializer(serializers.Serializer):
    cars = serializers.IntegerField()
    avg_age = serializers.FloatField(allow_null=True)
    repair_cost_per_hr = serializers.FloatField(allow_null=True)
    fuel = serializers.FloatField(allow_null=True, help_text="หน่วยตาม filters.fuel_unit")
    mtbf = serializers.FloatField(allow_null=True)
    percent_ma = serializers.FloatField(allow_null=True)


class ModelBenchmarkSerializer(serializers.Serializer):
    """รถที่เลือก เทียบกับคันอื่นรุ่นเดียวกัน / ชนิดเดียวกัน (ไม่รวมคันนี้)"""

    brand = serializers.CharField()
    car_model = serializers.CharField(allow_null=True)
    car_type_name = serializers.CharField()
    car = BenchmarkMetricsSerializer()
    model = BenchmarkMetricsSerializer(allow_null=True, help_text="null = ไม่มีคันอื่นรุ่นนี้")
    type = BenchmarkMetricsSerializer(allow_null=True)


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
    jobs = JobsSerializer()
    watchlist = WatchlistSerializer()
    model_comparison = ModelComparisonSerializer()
    model_benchmark = ModelBenchmarkSerializer(
        allow_null=True, help_text="null = ไม่ได้เลือกรถ หรือรถคันนี้ยังไม่ได้กรอกยี่ห้อ"
    )
    compare = CompareSerializer()
    insights = InsightsSerializer()
    last_synced_at = serializers.DateTimeField(
        allow_null=True, help_text="เวลาที่อัปเดตข้อมูลจาก webstock ครั้งล่าสุด"
    )


# ------------------------------------------------------------------ sync


class SyncResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    result = serializers.DictField()
