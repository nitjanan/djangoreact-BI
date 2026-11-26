from django.contrib.auth import get_user_model
from rest_framework import serializers

from dbapp.models import BaseBranchCompany, BaseCar, BaseCarDepartment, BaseCarType

# ------------------------------------------------------------------ auth / me


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"}, trim_whitespace=False)


class ReportLoginSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="token จากลิงก์ในอีเมลรายงาน")


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
    brand = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None, max_length=100
    )
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
    brand = serializers.CharField(allow_null=True, help_text="key ของยี่ห้อที่เลือก (BrandOption.key)")
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
    downtime_hours = serializers.FloatField(help_text="ชั่วโมงหยุดซ่อมรวม (ใบซ่อมที่ปิดงานแล้ว)")


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
    downtime_hours = serializers.FloatField(help_text="ชั่วโมงหยุดซ่อมรวม (ใบซ่อมที่ปิดงานแล้ว)")


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
    pm = serializers.ListField(child=serializers.IntegerField(), help_text="ใบ PM ต่อเดือน")
    downtime = _floats()


class TopCarsSerializer(serializers.Serializer):
    labels = _labels()
    companies = _labels()
    count = serializers.ListField(child=serializers.IntegerField())


class TopDowntimeSerializer(serializers.Serializer):
    labels = _labels()
    companies = _labels()
    hours = _floats()


class ReliabilitySerializer(serializers.Serializer):
    failure_count = serializers.IntegerField()
    doc_failure_count = serializers.IntegerField(
        help_text="ส่วนของ failure_count ที่นับจากใบจ่ายอะไหล่ (รถที่ไม่มีใบแจ้งซ่อม)"
    )
    doc_pm_count = serializers.IntegerField(
        help_text="ส่วนของ pm_count ที่นับจากใบจ่ายอะไหล่ประเภท PM (รถที่ไม่มีใบแจ้งซ่อม)"
    )
    repair_closed = serializers.IntegerField()
    mtbf = serializers.FloatField(allow_null=True)
    mttr = serializers.FloatField(allow_null=True)
    availability = serializers.FloatField(allow_null=True)
    downtime_hours = serializers.FloatField(help_text="ชั่วโมงหยุดซ่อมรวม (ใบซ่อมที่ปิดงานแล้ว)")
    pm_count = serializers.IntegerField()
    pm_ratio = serializers.FloatField(allow_null=True, help_text="% PM ในงาน PM + ซ่อม")
    trend = ReliabilityTrendSerializer()
    top_cars = TopCarsSerializer()
    top_downtime = TopDowntimeSerializer()


class BranchCompareSerializer(serializers.Serializer):
    branch_company_id = serializers.CharField()
    branch_company_name = serializers.CharField()
    car_count = serializers.IntegerField()
    repair_total = serializers.FloatField()
    work_total = serializers.FloatField()
    repair_cost_per_hr = serializers.FloatField(allow_null=True)
    percent_ma = serializers.FloatField(allow_null=True)
    failure_count = serializers.IntegerField()
    mtbf = serializers.FloatField(allow_null=True)
    downtime_hours = serializers.FloatField()


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
    po_overdue_count = serializers.IntegerField(help_text="ใบที่ PO เลยกำหนดรับของแล้ว")
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


WATCH_REASONS = [
    "stale",
    "cost",
    "replace",
    "repeat",
    "failure",
    "fuel",
    "fuel_spike",
    "low_use",
]


class WatchReasonSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=WATCH_REASONS)
    label = serializers.CharField()
    detail = serializers.CharField()
    value = serializers.CharField(help_text="ค่าหลักแบบสั้น (แสดงในตาราง/ป้าย)")
    note = serializers.CharField(allow_blank=True, help_text="คำอธิบายรองของค่าหลัก")
    sort = serializers.FloatField(help_text="ใช้เรียงในตัวกรองเหตุผลนี้ (มากไปน้อย)")


class WatchReplaceSignalSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=["old", "costly", "failure", "downtime", "rising"])
    label = serializers.CharField()
    value = serializers.CharField()


class WatchReplaceSerializer(serializers.Serializer):
    signals = WatchReplaceSignalSerializer(many=True, help_text="เฉพาะสัญญาณที่ยังไม่มีป้ายของตัวเอง")
    covered = serializers.ListField(
        child=serializers.CharField(), help_text="ป้ายอื่นของคันนี้ที่นับรวมเป็นสัญญาณด้วย"
    )
    annual_repair = serializers.FloatField(allow_null=True)


class WatchCarSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    branch_company_id = serializers.CharField()
    branch_company_name = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    repair_total = serializers.FloatField()
    failure_count = serializers.IntegerField()
    reasons = WatchReasonSerializer(many=True)
    age = serializers.IntegerField(allow_null=True)
    car_type_name = serializers.CharField(allow_blank=True)
    monthly = serializers.ListField(
        child=serializers.FloatField(), help_text="ค่าซ่อมรายเดือน ตรงกับ months"
    )
    replace = WatchReplaceSerializer(allow_null=True, help_text="มีเฉพาะคันที่ควรพิจารณาเปลี่ยน")


class WatchReasonCountSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=WATCH_REASONS)
    label = serializers.CharField()
    count = serializers.IntegerField()


class WatchlistSerializer(serializers.Serializer):
    car_count = serializers.IntegerField()
    months = serializers.ListField(child=serializers.CharField(), help_text="เดือนที่จบแล้ว")
    compared = serializers.BooleanField()
    reasons = WatchReasonCountSerializer(many=True)
    cars = WatchCarSerializer(many=True)


class PartsSerializer(serializers.Serializer):
    job_count = serializers.IntegerField()
    jobs_with_parts = serializers.IntegerField()
    doc_count = serializers.IntegerField()  # การซ่อมจากใบจ่ายอะไหล่ (รถที่ไม่มีใบแจ้งซ่อม)
    doc_amount = serializers.FloatField()
    amount = serializers.FloatField()
    amount_per_job = serializers.FloatField(allow_null=True)
    top = TopPartSerializer(many=True)


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
    chart = serializers.ChoiceField(
        choices=["repair_by_month", "reliability"],
        allow_null=True,
        help_text="กราฟที่เกี่ยวข้อง: กด hint แล้วเลื่อนไปที่กราฟนั้น",
    )


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


class BrandOptionSerializer(serializers.Serializer):
    key = serializers.CharField(help_text="ยี่ห้อที่ตัดช่องว่าง/ขีดออก ใช้เป็นค่าตัวกรอง brand")
    label = serializers.CharField()
    count = serializers.IntegerField(help_text="จำนวนคันในตารางรถ")


class FleetCarSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    branch_company_id = serializers.CharField()
    label = serializers.CharField()
    company = serializers.CharField(allow_blank=True)


class DowntimeSpanSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    open = serializers.BooleanField()
    ref_no = serializers.CharField(allow_blank=True)
    broke_reason = serializers.CharField(allow_blank=True)


class DowntimeCarSerializer(FleetCarSerializer):
    hours = serializers.FloatField()
    open = serializers.BooleanField()
    spans = DowntimeSpanSerializer(many=True)


class DowntimeSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    car_count = serializers.IntegerField()
    open_car_count = serializers.IntegerField()
    hours = serializers.FloatField()
    daily = serializers.ListField(
        child=serializers.IntegerField(), help_text="จำนวนรถที่หยุดในแต่ละวัน เริ่มที่ start"
    )
    peak = serializers.IntegerField()
    peak_date = serializers.DateField(allow_null=True)
    cars = DowntimeCarSerializer(many=True)


class PartPriceSerializer(serializers.Serializer):
    stkcod = serializers.CharField()
    name = serializers.CharField(allow_blank=True)
    unit = serializers.CharField(allow_blank=True)
    first_date = serializers.DateField()
    first_price = serializers.FloatField()
    last_date = serializers.DateField()
    last_price = serializers.FloatField()
    change = serializers.FloatField(help_text="%")
    period_qty = serializers.FloatField()
    impact = serializers.FloatField()
    prices = serializers.ListField(child=serializers.FloatField())


class PartPricesSerializer(serializers.Serializer):
    compared = serializers.IntegerField()
    up_count = serializers.IntegerField()
    down_count = serializers.IntegerField()
    impact = serializers.FloatField()
    min_change = serializers.FloatField()
    up = PartPriceSerializer(many=True)
    down = PartPriceSerializer(many=True)


class ForecastSeriesSerializer(serializers.Serializer):
    expected = serializers.FloatField()
    low = serializers.FloatField()
    high = serializers.FloatField()
    month_to_date = serializers.FloatField()
    history = serializers.ListField(child=serializers.FloatField(), help_text="ตรงกับ labels")


class ForecastSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField(), help_text="เดือนที่จบแล้ว")
    current_label = serializers.CharField()
    next_label = serializers.CharField()
    day = serializers.IntegerField()
    days_in_month = serializers.IntegerField()
    base_months = serializers.IntegerField()
    range_months = serializers.IntegerField()
    repair = ForecastSeriesSerializer()
    oil = ForecastSeriesSerializer()


class DashboardSerializer(serializers.Serializer):
    filters = DashboardFiltersSerializer()
    car_types = CarTypeSerializer(many=True)
    brands = BrandOptionSerializer(many=True)
    selected_car = CarRowSerializer(allow_null=True)
    car_table = CarTableSerializer()
    charts = ChartsSerializer()
    reliability = ReliabilitySerializer()
    unmatched = UnmatchedSerializer()
    open_jobs = OpenJobsSerializer()
    parts = PartsSerializer()
    jobs = JobsSerializer()
    watchlist = WatchlistSerializer()
    downtime = DowntimeSerializer()
    part_prices = PartPricesSerializer()
    forecast = ForecastSerializer(
        allow_null=True, help_text="null = ไม่ได้ดูปีปัจจุบันถึงเดือนปัจจุบัน หรือข้อมูลไม่ถึง 3 เดือน"
    )
    model_comparison = ModelComparisonSerializer()
    branch_compare = BranchCompareSerializer(many=True, help_text="ว่าง = ดูบริษัทเดียวหรือเลือกรถคันเดียว")
    model_benchmark = ModelBenchmarkSerializer(
        allow_null=True, help_text="null = ไม่ได้เลือกรถ หรือรถคันนี้ยังไม่ได้กรอกยี่ห้อ"
    )
    compare = CompareSerializer()
    insights = InsightsSerializer()
    last_synced_at = serializers.DateTimeField(
        allow_null=True, help_text="เวลาที่อัปเดตข้อมูลจาก webstock ครั้งล่าสุด"
    )


# ------------------------------------------------------------ car history


class CarHistoryQuerySerializer(serializers.Serializer):
    branch_company_id = serializers.CharField()


class CarHistoryCarSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    brand = serializers.CharField(allow_null=True)
    car_model = serializers.CharField(allow_null=True)
    start_year = serializers.IntegerField(allow_null=True)
    age = serializers.IntegerField(allow_null=True)
    car_type_name = serializers.CharField(allow_null=True)
    car_dep_id = serializers.IntegerField(allow_null=True)
    car_dep_name = serializers.CharField(allow_null=True)
    unit_noun = serializers.CharField()
    branch_company_id = serializers.CharField()
    branch_company_name = serializers.CharField()


class CarHistoryTotalsSerializer(serializers.Serializer):
    repair_total = serializers.FloatField()
    work_total = serializers.FloatField()
    repair_cost_per_hr = serializers.FloatField(allow_null=True)
    ticket_count = serializers.IntegerField()
    breakdown_count = serializers.IntegerField()
    doc_breakdown_count = serializers.IntegerField(
        help_text="ส่วนของ breakdown_count ที่นับจากใบจ่ายอะไหล่ (รถไม่มีใบแจ้งซ่อม)"
    )
    doc_pm_count = serializers.IntegerField(
        help_text="ส่วนของ pm_count ที่นับจากใบจ่ายอะไหล่ประเภท PM (รถไม่มีใบแจ้งซ่อม)"
    )
    pm_count = serializers.IntegerField()
    open_count = serializers.IntegerField()
    downtime_hours = serializers.FloatField()
    parts_total = serializers.FloatField()
    data_from = serializers.CharField(allow_null=True, help_text="เดือนแรกที่มีข้อมูล")


class CarHistoryMonthlySerializer(serializers.Serializer):
    labels = _labels()
    repair = _floats()
    work = _floats()
    breakdowns = serializers.ListField(child=serializers.IntegerField())
    pm = serializers.ListField(child=serializers.IntegerField())


class CarHistoryTicketSerializer(serializers.Serializer):
    ext_id = serializers.IntegerField()
    ref_no = serializers.CharField()
    reported_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
    ma_type = serializers.CharField()
    ma_type_name = serializers.CharField()
    broke_reason = serializers.CharField()
    car_state = serializers.CharField()
    is_open = serializers.BooleanField()
    stage_label = serializers.CharField()
    repair_hours = serializers.FloatField(allow_null=True)
    parts = PartSerializer(many=True, help_text="อะไหล่จากใบจ่ายสินค้าภายในที่อ้างอิงใบนี้")
    parts_amount = serializers.FloatField()
    parts_count = serializers.IntegerField()


class CarHistoryRepairItemSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    label = serializers.CharField()
    repair_name = serializers.CharField()
    amount = serializers.FloatField()


class CarHistoryDocJobSerializer(serializers.Serializer):
    ref_no = serializers.CharField(help_text="เลขที่ใบจ่ายอะไหล่ (หลายใบคั่นด้วย , )")
    docdat = serializers.DateField()
    is_pm = serializers.BooleanField()
    amount = serializers.FloatField()
    parts = PartSerializer(many=True)


class CarHistorySerializer(serializers.Serializer):
    car = CarHistoryCarSerializer()
    totals = CarHistoryTotalsSerializer()
    monthly = CarHistoryMonthlySerializer()
    repair_items = CarHistoryRepairItemSerializer(
        many=True, help_text="ค่าซ่อมรายเดือนแยกตามระบบ ใหม่ -> เก่า"
    )
    tickets = CarHistoryTicketSerializer(many=True)
    doc_jobs = CarHistoryDocJobSerializer(
        many=True, help_text="การซ่อมจากใบจ่ายอะไหล่ของรถที่ไม่มีใบแจ้งซ่อม ใหม่ -> เก่า"
    )
    jobs = JobsSerializer(help_text="งานที่ทำจากบันทึกการใช้รถ แยกตามแผนกค่าใช้จ่าย")


# ------------------------------------------------------------------ sync


class SyncResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    result = serializers.DictField()
