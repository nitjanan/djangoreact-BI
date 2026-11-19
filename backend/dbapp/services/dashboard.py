"""คำนวณข้อมูลหน้า dashboard — ย้ายมาจาก views.home() เดิม

ต่างจากเดิม:
- รับตัวกรองเป็น argument (เดิมอ่านจาก session: company_code, car_dep_id)
- ตรวจว่า user มีสิทธิ์เห็นบริษัทที่ขอ (เดิมไม่ตรวจ)
- ปีเป็นพารามิเตอร์ (เดิม hard-code '2026')
- คืนค่าเป็น list/number ล้วน (เดิมบางค่าเป็น json.dumps สำหรับ template)
"""

import operator
from dataclasses import dataclass
from datetime import date
from functools import reduce

from django.db.models import Case, F, FloatField, Q, Sum, Value, When
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import Coalesce

from dbapp.models import (
    BaseBranchCompany,
    BaseCarType,
    SummaryMaintenance,
    SummaryOil,
    SummaryRepair,
    SummaryUnmatched,
    SummaryWork,
    UserProfile,
)
from dbapp.services.insights import build_insights

ALL_COMPANIES = "ALL"

MONTHS_TH = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]  # fmt: skip

# ประเภทใบแจ้งซ่อมที่นับเป็น "การเสีย" (02 = ซ่อม)
MA_TYPE_BREAKDOWN = "02"

UNKNOWN = "ไม่ระบุ"


class CompanyAccessDenied(Exception):
    pass


# ------------------------------------------------------------------ access


HEATMAP_CARS = 15


def user_companies(user):
    """บริษัทที่ user มองเห็น เรียงตามรหัส (00 ทั้งหมด, 01, 02, ...)"""
    return BaseBranchCompany.objects.filter(userprofile__user=user).order_by("id")


def user_visible_tabs(user):
    profile = UserProfile.objects.filter(user=user).first()
    return list(profile.visible.values_list("name", flat=True)) if profile else []


def resolve_company_ids(user, company_code):
    """แปลงรหัสบริษัทที่เลือกเป็น list ของ branch_company id (เดิม: findCompanyIn)"""
    allowed = user_companies(user)
    if not allowed.filter(code=company_code).exists():
        raise CompanyAccessDenied(company_code)

    if company_code == ALL_COMPANIES:
        return list(allowed.values_list("id", flat=True))
    return list(allowed.filter(code=company_code).values_list("id", flat=True))


# ------------------------------------------------------------- calculations


BUDDHIST_ERA_OFFSET = 543
MAX_REPAIR_HOURS = 365 * 24


def to_gregorian(dt):
    """วันที่ที่กรอกเป็น พ.ศ. (เช่น 2569) -> ค.ศ. (2026)"""
    if dt and dt.year >= 2400:
        try:
            return dt.replace(year=dt.year - BUDDHIST_ERA_OFFSET)
        except ValueError:  # 29 ก.พ. ในปีที่ไม่ใช่ปีอธิกสุรทิน
            return dt.replace(year=dt.year - BUDDHIST_ERA_OFFSET, day=28)
    return dt


def repair_hours(reported_at, finished_at):
    # เวลาซ่อม (ชม.) = ปิดงาน - แจ้งซ่อม
    # ไม่นับใบที่ยังไม่ปิด เวลาปิดก่อนแจ้ง หรือนานเกิน 1 ปี (กรอกวันที่ผิด)
    reported_at, finished_at = to_gregorian(reported_at), to_gregorian(finished_at)
    if not finished_at or finished_at <= reported_at:
        return None
    hours = (finished_at - reported_at).total_seconds() / 3600
    return hours if hours <= MAX_REPAIR_HOURS else None


def cal_mtbf(work_total, failure_count):
    # MTBF = ชั่วโมงทำงาน / จำนวนครั้งที่เสีย
    if failure_count > 0 and work_total > 0:
        return work_total / failure_count
    return None


def cal_mean(values):
    return sum(values) / len(values) if values else None


def hours_per_day_by_car_dep(car_dep):
    # ชั่วโมงทำงานมาตรฐานต่อวันของแต่ละแผนก (🔧 ปรับตามจริง)
    if str(car_dep) == "2":  # รถบรรทุก/ยานพาหนะ
        return 35
    if str(car_dep) == "3":  # เครื่องจักรกลหนัก
        return 10
    return 8


def _label(value):
    return value if value else UNKNOWN


def car_label(row):
    """ชื่อรถ:รหัส (ตัด ':' ท้ายกรณีไม่มีรหัส)"""
    return f"{row['car__name'] or UNKNOWN}:{row['car__code'] or ''}".rstrip(":")


def build_reliability(base_filter, months):
    failures = list(
        SummaryMaintenance.objects.filter(**base_filter, ma_type=MA_TYPE_BREAKDOWN).values(
            "car_id",
            "car__code",
            "car__name",
            "branch_company_id",
            "branch_company__name",
            "month",
            "reported_at",
            "finished_at",
        )
    )

    work_total = float(
        SummaryWork.objects.filter(**base_filter).aggregate(total=Sum("sum_diff_mile"))["total"]
        or 0
    )

    durations = []
    month_counts = {}
    month_durations = {}
    cars = {}

    for f in failures:
        hours = repair_hours(f["reported_at"], f["finished_at"])
        month = int(f["month"])
        month_counts[month] = month_counts.get(month, 0) + 1

        car = cars.setdefault(
            (f["car_id"], f["branch_company_id"]),
            {
                "label": car_label(f),
                "company": f["branch_company__name"] or "",
                "count": 0,
                "durations": [],
            },
        )
        car["count"] += 1

        if hours is not None:
            durations.append(hours)
            month_durations.setdefault(month, []).append(hours)
            car["durations"].append(hours)

    mtbf = cal_mtbf(work_total, len(failures))
    mttr = cal_mean(durations)
    availability = mtbf / (mtbf + mttr) * 100 if mtbf is not None and mttr is not None else None

    top_cars = sorted(
        cars.values(),
        key=lambda c: (c["count"], cal_mean(c["durations"]) or 0),
        reverse=True,
    )[:10]

    trend_mttr = [cal_mean(month_durations.get(m, [])) for m in months]

    return {
        "failure_count": len(failures),
        "repair_closed": len(durations),
        "mtbf": mtbf,
        "mttr": mttr,
        "availability": availability,
        "trend": {
            "labels": [MONTHS_TH[m - 1] for m in months],
            "count": [month_counts.get(m, 0) for m in months],
            # None = ไม่มีข้อมูล (แสดงเป็นช่องว่างในกราฟ)
            "mttr": [round(v, 1) if v is not None else None for v in trend_mttr],
        },
        "top_cars": {
            "labels": [c["label"] for c in top_cars],
            "companies": [c["company"] for c in top_cars],
            "count": [c["count"] for c in top_cars],
        },
    }


def build_car_table(car_dep_id, year, company_ids, car_type_id):
    table_filter = {
        "car_dep_id": car_dep_id,
        "year": year,
        "branch_company_id__in": company_ids,
        "car_id__isnull": False,
    }
    if car_type_id is not None:
        table_filter["car__car_type_id"] = car_type_id

    group_fields = ("car_id", "car__code", "car__name", "branch_company_id", "branch_company__name")
    rows = {}

    def ensure_row(item):
        key = (item["car_id"], item["branch_company_id"])
        if key not in rows:
            rows[key] = {
                "car_id": item["car_id"],
                "branch_company_id": item["branch_company_id"],
                "branch_company_name": item.get("branch_company__name") or "",
                "code": item.get("car__code") or "",
                "name": item.get("car__name"),
                "percent_ma": 0.0,
                "avg_work_per_day": 0.0,
                "work_total": 0.0,
                "oil_total": 0.0,
                "fuel_rate": 0.0,
                "repair_total": 0.0,
                "repair_cost_per_hr": 0.0,
                "failure_count": 0,
                "mtbf": None,
                "mttr": None,
            }
        return rows[key]

    for item in (
        SummaryRepair.objects.filter(**table_filter)
        .values(*group_fields)
        .annotate(repair_total=Sum("amount"))
    ):
        ensure_row(item)["repair_total"] = float(item["repair_total"] or 0)

    for item in (
        SummaryOil.objects.filter(**table_filter)
        .values(*group_fields)
        .annotate(oil_total=Sum("sum_liter"))
    ):
        ensure_row(item)["oil_total"] = float(item["oil_total"] or 0)

    for item in (
        SummaryWork.objects.filter(**table_filter)
        .values(*group_fields, "car_dep")
        .annotate(work_total=Sum("sum_diff_mile"), work_days=Sum("count_diff_time"))
    ):
        row = ensure_row(item)
        work_total = float(item["work_total"] or 0)
        work_days = float(item["work_days"] or 0)
        hours_per_day = hours_per_day_by_car_dep(item.get("car_dep"))

        if work_days > 0:
            row["avg_work_per_day"] = work_total / work_days
        if work_total > 0:
            row["fuel_rate"] = row["oil_total"] / work_total
            row["repair_cost_per_hr"] = row["repair_total"] / work_total
        if work_days > 0 and hours_per_day > 0:
            row["percent_ma"] = work_total / (work_days * hours_per_day) * 100
        row["work_total"] = work_total

    # ใบแจ้งซ่อมประเภท "ซ่อม" ต่อคัน -> MTBF / MTTR
    all_durations = []
    car_durations = {}
    for item in SummaryMaintenance.objects.filter(**table_filter, ma_type=MA_TYPE_BREAKDOWN).values(
        *group_fields, "reported_at", "finished_at"
    ):
        row = ensure_row(item)
        row["failure_count"] += 1
        hours = repair_hours(item["reported_at"], item["finished_at"])
        if hours is not None:
            all_durations.append(hours)
            car_durations.setdefault((item["car_id"], item["branch_company_id"]), []).append(hours)

    for key, row in rows.items():
        row["mtbf"] = cal_mtbf(row["work_total"], row["failure_count"])
        row["mttr"] = cal_mean(car_durations.get(key, []))

    table_rows = sorted(rows.values(), key=lambda r: (r["code"], r["branch_company_name"]))
    work_sum = sum(r["work_total"] for r in table_rows)
    oil_sum = sum(r["oil_total"] for r in table_rows)
    repair_sum = sum(r["repair_total"] for r in table_rows)
    failure_sum = sum(r["failure_count"] for r in table_rows)

    totals = {
        "percent_ma": cal_mean([r["percent_ma"] for r in table_rows if r["percent_ma"] > 0]) or 0,
        "avg_work_per_day": cal_mean(
            [r["avg_work_per_day"] for r in table_rows if r["avg_work_per_day"] > 0]
        )
        or 0,
        "work_total": work_sum,
        "oil_total": oil_sum,
        "fuel_rate": oil_sum / work_sum if work_sum > 0 else 0,
        "repair_total": repair_sum,
        "repair_cost_per_hr": repair_sum / work_sum if work_sum > 0 else 0,
        "failure_count": failure_sum,
        "mtbf": cal_mtbf(work_sum, failure_sum),
        "mttr": cal_mean(all_durations),
    }
    return table_rows, totals


# -------------------------------------------------------------- dashboard


@dataclass
class DashboardFilters:
    company: str
    year: int
    car_dep: int = 1
    car_type: int | None = None  # None = ทุกชนิด
    car_id: int | None = None
    branch_company_id: str | None = None


def available_car_types(car_dep_id, year, company_ids):
    """ชนิดรถที่มีข้อมูลจริงในแผนก/ปี/บริษัทที่เลือก (ใช้ทำ dropdown)"""
    car_type_filter = {
        "car_dep_id": car_dep_id,
        "year": year,
        "branch_company_id__in": company_ids,
        "car__car_type_id__isnull": False,
    }
    ids = set()
    for model in (SummaryRepair, SummaryOil, SummaryWork):
        ids.update(
            model.objects.filter(**car_type_filter)
            .values_list("car__car_type_id", flat=True)
            .distinct()
        )
    return BaseCarType.objects.filter(id__in=ids)


# แท็บ "อื่นๆ": ข้อมูลที่ไม่มีแผนก = รถที่ยังไม่ได้ตั้งแผนกใน webstock + remark ที่จับคู่กับรถไม่ได้
OTHER_CAR_DEP = 0


def build_unmatched(year, company_ids):
    """ค่าใช้จ่ายที่ remark จับคู่กับรถใน webstock ไม่ได้ รวมทั้งปีต่อ remark + บริษัท

    ไม่มีแผนก จึงไม่กรองตามแท็บแผนก/ประเภทรถ/คันที่เลือก
    """
    rows = list(
        SummaryUnmatched.objects.filter(year=year, branch_company_id__in=company_ids)
        .values("remark", "branch_company_id", "branch_company__name")
        .annotate(repair_amount=Sum("repair_amount"), oil_qty=Sum("oil_qty"))
        .order_by("-repair_amount", "-oil_qty", "remark")
    )
    items = [
        {
            "remark": r["remark"],
            "branch_company_name": r["branch_company__name"] or "",
            "repair_amount": float(r["repair_amount"] or 0),
            "oil_qty": float(r["oil_qty"] or 0),
        }
        for r in rows
    ]
    return {
        "rows": items,
        "repair_total": sum(i["repair_amount"] for i in items),
        "oil_total": sum(i["oil_qty"] for i in items),
    }


def merge_unmatched_months(by_month, year, company_ids, car_type):
    """เพิ่มค่าซ่อมที่จับคู่กับรถไม่ได้เข้าไปในยอดรายเดือน (เมื่อกรองประเภทรถอยู่ ไม่รวม เพราะไม่รู้ประเภท)"""
    if car_type is not None:
        return by_month
    totals = {int(r["month"]): dict(r) for r in by_month}
    extra = (
        SummaryUnmatched.objects.filter(year=year, branch_company_id__in=company_ids)
        .values("month")
        .annotate(amount_sum=Sum("repair_amount"))
    )
    for r in extra:
        month = int(r["month"])
        row = totals.setdefault(
            month, {"month": month, "month_th": MONTHS_TH[month - 1], "amount_sum": 0}
        )
        row["amount_sum"] = float(row["amount_sum"] or 0) + float(r["amount_sum"] or 0)
    return [totals[m] for m in sorted(totals)]


def build_dashboard(user, filters: DashboardFilters, today=None):
    today = today or date.today()
    company_ids = resolve_company_ids(user, filters.company)
    is_other = filters.car_dep == OTHER_CAR_DEP
    # car_dep_id=None -> Django กรองเป็น IS NULL (รถที่ไม่มีแผนก)
    car_dep_id = None if is_other else filters.car_dep

    # เดือน 1 -> เดือนปัจจุบัน (ถ้าเป็นปีที่ผ่านมาแล้วแสดงครบ 12 เดือน)
    last_month = today.month if filters.year >= today.year else 12
    months = range(1, last_month + 1)

    car_types = list(available_car_types(car_dep_id, filters.year, company_ids))
    car_type = filters.car_type
    if car_type is not None and car_type not in {ct.id for ct in car_types}:
        car_type = None

    car_rows, car_totals = build_car_table(car_dep_id, filters.year, company_ids, car_type)

    # เลือกรถด้วย car_id + branch_company_id (code ของรถอาจว่างหรือซ้ำกัน)
    selected_car = None
    if filters.car_id is not None and filters.branch_company_id:
        selected_car = next(
            (
                r
                for r in car_rows
                if r["car_id"] == filters.car_id
                and str(r["branch_company_id"]) == str(filters.branch_company_id)
            ),
            None,
        )
        # รถที่ไม่ได้อยู่ในบริษัทที่ user มองเห็น จะไม่อยู่ในตาราง -> ไม่ให้กรองถึง
        if selected_car is None:
            filters.car_id = None
            filters.branch_company_id = None

    base_filter = {"car_dep_id": car_dep_id, "year": filters.year}
    if car_type is not None:
        base_filter["car__car_type_id"] = car_type
    if selected_car:
        base_filter["car_id"] = filters.car_id
        base_filter["branch_company_id"] = filters.branch_company_id
    else:
        base_filter["branch_company_id__in"] = company_ids

    repairs = SummaryRepair.objects.filter(**base_filter)

    by_repair_type = list(
        repairs.values("repair_name").annotate(amount_sum=Sum("amount")).order_by("-amount_sum")
    )
    by_month = list(
        repairs.values("month", "month_th").annotate(amount_sum=Sum("amount")).order_by("month")
    )
    by_car_type = list(
        repairs.values("car__car_type__name")
        .annotate(amount_sum=Sum("amount"))
        .order_by("-amount_sum")
    )
    # แยกตามรถ + บริษัท (ทะเบียนเดียวกันอาจอยู่คนละบริษัท)
    by_car = list(
        repairs.values(
            "car_id", "branch_company_id", "car__name", "car__code", "branch_company__name"
        )
        .annotate(amount_sum=Sum("amount"))
        .order_by("-amount_sum")
    )

    # ตารางสี รถ x เดือน: เฉพาะรถที่ค่าซ่อมสูงสุด HEATMAP_CARS คัน
    heat_cars = by_car[:HEATMAP_CARS]
    heat_cells = (
        repairs.filter(
            reduce(
                operator.or_,
                (
                    Q(car_id=c["car_id"], branch_company_id=c["branch_company_id"])
                    for c in heat_cars
                ),
                Q(pk__in=[]),
            )
        )
        .values("car_id", "branch_company_id", "month")
        .annotate(amount_sum=Sum("amount"))
    )
    heat_map = {
        (c["car_id"], c["branch_company_id"], int(c["month"])): float(c["amount_sum"] or 0)
        for c in heat_cells
    }

    oil_by_month = list(
        SummaryOil.objects.filter(**base_filter)
        .values("month", "month_th")
        .annotate(
            sum_liter_sum=Coalesce(Sum("sum_liter"), Value(0), output_field=FloatField()),
            sum_km_sum=Coalesce(Sum("sum_km"), Value(0), output_field=FloatField()),
        )
        .annotate(
            real_liter_per_km=Case(
                When(sum_km_sum=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    F("sum_liter_sum") / F("sum_km_sum"), output_field=FloatField()
                ),
                output_field=FloatField(),
            )
        )
        .order_by("month")
    )

    work_by_month = list(
        SummaryWork.objects.filter(**base_filter)
        .values("month", "month_th", "car_dep")
        .annotate(
            total_mile=Coalesce(Sum("sum_diff_mile"), Value(0), output_field=FloatField()),
            total_time=Coalesce(Sum("count_diff_time"), Value(0), output_field=FloatField()),
        )
        .order_by("month")
    )

    work_hours, work_percent = [], []
    for item in work_by_month:
        total_mile = float(item["total_mile"] or 0)
        total_time = float(item["total_time"] or 0)
        hours_per_day = hours_per_day_by_car_dep(item["car_dep"])
        percent = (
            total_mile / (total_time * hours_per_day) * 100
            if total_time > 0 and hours_per_day > 0
            else 0
        )
        work_hours.append(round(total_mile, 2))
        work_percent.append(round(percent, 2))

    # แท็บอื่นๆ (ไม่ได้เลือกคันเดียว): รวมค่าซ่อมที่จับคู่กับรถไม่ได้ในยอดรายเดือนด้วย
    # (ยอดในตารางรถยังเป็นของรถจริงเท่านั้น หน้าเว็บบวกยอดรวมเองที่แผงหัว)
    unmatched = {"rows": [], "repair_total": 0.0, "oil_total": 0.0}
    if is_other and not selected_car:
        unmatched = build_unmatched(filters.year, company_ids)
        by_month = merge_unmatched_months(by_month, filters.year, company_ids, car_type)

    repair_by_month = {int(i["month"]): float(i["amount_sum"] or 0) for i in by_month}
    work_by_month_map = {int(i["month"]): float(i["total_mile"] or 0) for i in work_by_month}

    def amounts(rows):
        return [float(r["amount_sum"] or 0) for r in rows]

    result = {
        "filters": {
            "company": filters.company,
            "year": filters.year,
            "car_dep": filters.car_dep,
            "car_type": car_type,
            "car_id": filters.car_id,
            "branch_company_id": filters.branch_company_id,
        },
        "car_types": [{"id": ct.id, "name": ct.name} for ct in car_types],
        "selected_car": selected_car,
        "car_table": {"rows": car_rows, "totals": car_totals},
        "charts": {
            "repair_by_type": {
                "labels": [_label(r["repair_name"]) for r in by_repair_type],
                "series": amounts(by_repair_type),
                "total": sum(amounts(by_repair_type)),
            },
            "repair_by_car_type": {
                "labels": [_label(r["car__car_type__name"]) for r in by_car_type],
                "series": amounts(by_car_type),
                "total": sum(amounts(by_car_type)),
            },
            "repair_by_month": {
                "labels": [_label(r["month_th"]) for r in by_month],
                "series": amounts(by_month),
            },
            "repair_by_car": {
                # ตัด ':' ท้ายชื่อ กรณีรถไม่มี code
                "labels": [car_label(r) for r in by_car],
                "companies": [r["branch_company__name"] or "" for r in by_car],
                "series": amounts(by_car),
                "total": sum(amounts(by_car)),
            },
            "repair_heatmap": {
                "labels": [MONTHS_TH[m - 1] for m in months],
                "rows": [
                    {
                        "name": car_label(c),
                        "company": c["branch_company__name"] or "",
                        "data": [
                            heat_map.get((c["car_id"], c["branch_company_id"], m), 0)
                            for m in months
                        ],
                    }
                    for c in heat_cars
                ],
            },
            "oil_by_month": {
                "labels": [_label(r["month_th"]) for r in oil_by_month],
                "liters": [float(r["sum_liter_sum"]) for r in oil_by_month],
                "liter_per_km": [float(r["real_liter_per_km"] or 0) for r in oil_by_month],
            },
            "work_by_month": {
                "labels": [_label(r["month_th"]) for r in work_by_month],
                "hours": work_hours,
                "percent": work_percent,
            },
            "repair_vs_work": {
                "labels": [MONTHS_TH[m - 1] for m in months],
                "repair": [repair_by_month.get(m, 0) for m in months],
                "work": [work_by_month_map.get(m, 0) for m in months],
            },
        },
        "reliability": build_reliability(base_filter, months),
        "unmatched": unmatched,
    }
    result["insights"] = build_insights(
        result,
        # เดือนปัจจุบันยังไม่จบ ไม่นำมาคิดแนวโน้ม
        partial_last_month=filters.year == today.year,
        **data_quality_counts(filters.year, company_ids, is_other, unmatched),
    )
    return result


def data_quality_counts(year, company_ids, is_other, unmatched):
    """ตัวเลขคุณภาพข้อมูลระดับบริษัท สำหรับข้อสังเกต (ไม่ขึ้นกับแท็บแผนก)"""
    if is_other:
        # แท็บอื่นๆ แสดงรายการที่จับคู่ไม่ได้และรถไม่มีแผนกอยู่แล้ว
        return {"unmatched_total": unmatched["repair_total"], "no_dep_cars": 0}
    unmatched_total = (
        SummaryUnmatched.objects.filter(year=year, branch_company_id__in=company_ids).aggregate(
            total=Sum("repair_amount")
        )["total"]
        or 0
    )
    no_dep = set()
    for model in (SummaryRepair, SummaryOil, SummaryWork):
        no_dep.update(
            model.objects.filter(
                year=year,
                branch_company_id__in=company_ids,
                car_dep_id__isnull=True,
                car_id__isnull=False,
            )
            .values_list("car_id", "branch_company_id")
            .distinct()
        )
    return {"unmatched_total": float(unmatched_total), "no_dep_cars": len(no_dep)}
