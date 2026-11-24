"""คำนวณข้อมูลหน้า dashboard — ย้ายมาจาก views.home() เดิม

ต่างจากเดิม:
- รับตัวกรองเป็น argument (เดิมอ่านจาก session: company_code, car_dep_id)
- ตรวจว่า user มีสิทธิ์เห็นบริษัทที่ขอ (เดิมไม่ตรวจ)
- ปีเป็นพารามิเตอร์ (เดิม hard-code '2026')
- คืนค่าเป็น list/number ล้วน (เดิมบางค่าเป็น json.dumps สำหรับ template)
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from datetime import date, datetime
from functools import reduce

from django.db.models import Case, Count, F, FloatField, Max, Q, Sum, Value, When
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import Coalesce

from dbapp.models import (
    BaseBranchCompany,
    BaseCarDepartment,
    BaseCarType,
    SummaryCarJob,
    SummaryMaintenance,
    SummaryOil,
    SummaryRepair,
    SummaryRepairDoc,
    SummaryUnmatched,
    SummaryWork,
    UserProfile,
)
from dbapp.services.insights import FUEL_PER_HOUR, FUEL_PER_KM, build_insights

ALL_COMPANIES = "ALL"

MONTHS_TH = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]  # fmt: skip

# ประเภทใบแจ้งซ่อมที่นับเป็น "การเสีย" (02 = ซ่อม)
MA_TYPE_BREAKDOWN = "02"
MA_TYPE_PM = "04"  # บำรุงรักษาตามรอบ (PM)
MA_TYPE_NAMES = {"01": "สั่งทำ", "02": "ซ่อม", "03": "ติดตั้ง", "04": "PM"}

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
    # ไม่นับใบที่ยังไม่ปิด เวลาปิดก่อนแจ้ง ปิดงานในอนาคต หรือนานเกิน 1 ปี (กรอกวันที่ผิด)
    reported_at, finished_at = to_gregorian(reported_at), to_gregorian(finished_at)
    if not finished_at or finished_at <= reported_at or finished_at > datetime.now():
        return None
    hours = (finished_at - reported_at).total_seconds() / 3600
    return hours if hours <= MAX_REPAIR_HOURS else None


def repair_span(reported_at, finished_at):
    """(เริ่ม, จบ) ของใบซ่อมที่ใช้คำนวณได้ (เงื่อนไขเดียวกับ repair_hours) ไม่งั้น None"""
    if repair_hours(reported_at, finished_at) is None:
        return None
    return to_gregorian(reported_at), to_gregorian(finished_at)


def merge_spans(spans):
    """รวมช่วงที่ซ้อนกัน: รถคันเดียวมีหลายใบเปิดพร้อมกันก็หยุดอยู่ครั้งเดียว ไม่นับชั่วโมงซ้ำ"""
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, (end - start).total_seconds() / 3600) for start, end in merged]


def cal_mtbf(work_total, failure_count):
    # MTBF = ชั่วโมงทำงาน / จำนวนครั้งที่เสีย
    if failure_count > 0 and work_total > 0:
        return work_total / failure_count
    return None


def car_age(start_year, year):
    """อายุ (ปี) ณ ปีที่ดูข้อมูล ไม่รู้ปีที่เริ่มใช้งาน หรือเริ่มใช้หลังปีที่ดู = None"""
    if not start_year or start_year > year:
        return None
    return year - start_year


def cal_mean(values):
    return sum(values) / len(values) if values else None


# แผนกที่ชั่วโมงทำงานมาจากเวลางานในบันทึกการใช้รถ (SummaryCarJob) แทนหน้าปัดชั่วโมง
# เลขไมล์ของแผนกเหล่านี้เป็น กม. จึงเทียบน้ำมันเป็น ลิตร/กม. (id ตรงกับ webstock)
JOB_HOURS_CAR_DEPS = {1, 2}  # 1 = ยานพาหนะ, 2 = รถบรรทุก


def work_source(car_dep_id):
    """(model, field) ของชั่วโมงทำงาน: รถบรรทุก/ยานพาหนะ = เวลางาน, อื่นๆ = หน้าปัดชั่วโมง"""
    if car_dep_id in JOB_HOURS_CAR_DEPS:
        return SummaryCarJob, "hours"
    return SummaryWork, "sum_diff_mile"


def hours_per_day_by_car_dep(car_dep):
    # ชั่วโมงทำงานมาตรฐานต่อวันของแต่ละแผนก (🔧 ปรับตามจริง)
    if str(car_dep) == "3":  # เครื่องจักรกลหนัก
        return 10
    return 8


def _label(value):
    return value if value else UNKNOWN


def car_label(row):
    """ชื่อรถ:รหัส (ตัด ':' ท้ายกรณีไม่มีรหัส)"""
    return f"{row['car__name'] or UNKNOWN}:{row['car__code'] or ''}".rstrip(":")


def ticketless_docs(base_filter, fields=()):
    """ใบจ่ายอะไหล่ (Express) ของรถที่ไม่มีใบแจ้งซ่อมเลยในตัวกรองนี้ เรียงตามวันที่

    ใบแจ้งซ่อมเป็นข้อมูลหลัก: รถที่มีใบแจ้งซ่อมอย่างน้อย 1 ใบในช่วงนี้ไม่นับจากใบจ่ายซ้ำ
    ไม่นับใบจ่ายที่มีแต่น้ำมัน (ยอดไม่รวมน้ำมันเป็น 0)
    """
    base_filter = {**base_filter, "car_id__isnull": False}
    with_tickets = set(
        SummaryMaintenance.objects.filter(**base_filter)
        .values_list("car_id", "branch_company_id")
        .distinct()
    )
    docs = (
        SummaryRepairDoc.objects.filter(**base_filter, amount__gt=0)
        .values("car_id", "branch_company_id", "month", "docdat", "ma_ref", "repair_name", *fields)
        .order_by("docdat", "docnum")
    )
    for d in docs:
        if (d["car_id"], d["branch_company_id"]) not in with_tickets:
            d["is_pm"] = is_pm_repair(d.pop("repair_name"))
            yield d


def doc_event_key(doc):
    """การซ่อม 1 ครั้ง = ใบจ่ายที่อ้างใบแจ้งซ่อม (note3) เดียวกัน หรือเบิกวันเดียวกัน แยก PM/ซ่อม

    (วันเดียวกันมีทั้งใบ PM และใบซ่อม นับเป็น PM 1 ครั้ง + ซ่อม 1 ครั้ง)
    """
    return (doc["car_id"], doc["branch_company_id"], doc["ma_ref"] or doc["docdat"], doc["is_pm"])


def doc_repair_events(base_filter, fields=()):
    """การซ่อมจากใบจ่ายอะไหล่ของรถที่ไม่มีใบแจ้งซ่อม (ดู ticketless_docs, doc_event_key)

    แต่ละครั้งมี is_pm: ประเภทการซ่อม (note2) เป็น "PM" = งานบำรุงรักษาตามรอบ ไม่ใช่การเสีย
    ไม่มีเวลาปิดงาน จึงไม่มี MTTR/Downtime
    """
    events = {}
    for d in ticketless_docs(base_filter, fields):
        events.setdefault(doc_event_key(d), d)
    return list(events.values())


def is_pm_repair(repair_name):
    return (repair_name or "").strip().upper() == "PM"


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

    work_model, work_field = work_source(base_filter.get("car_dep_id"))
    work_total = float(
        work_model.objects.filter(**base_filter).aggregate(total=Sum(work_field))["total"] or 0
    )

    durations = []
    month_counts = {}
    month_durations = {}
    cars = {}

    # PM (ma_type 04) เทียบกับการซ่อมเมื่อเสีย: PM น้อยแต่เสียบ่อย = บำรุงรักษาเชิงรุกยังไม่พอ
    pm_months = {
        int(r["month"]): r["n"]
        for r in SummaryMaintenance.objects.filter(**base_filter, ma_type=MA_TYPE_PM)
        .values("month")
        .annotate(n=Count("id"))
    }
    pm_count = sum(pm_months.values())

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
                "spans": [],
            },
        )
        car["count"] += 1
        span = repair_span(f["reported_at"], f["finished_at"])
        if span:
            car["spans"].append(span)

        if hours is not None:
            durations.append(hours)
            month_durations.setdefault(month, []).append(hours)
            car["durations"].append(hours)

    # รถที่ไม่มีใบแจ้งซ่อม: นับการซ่อมจากใบจ่ายอะไหล่แทน (นับครั้งได้ แต่ไม่มีเวลาซ่อม)
    doc_events = doc_repair_events(base_filter, ("car__code", "car__name", "branch_company__name"))
    doc_pm = [d for d in doc_events if d["is_pm"]]
    for d in doc_pm:
        pm_months[int(d["month"])] = pm_months.get(int(d["month"]), 0) + 1
    pm_count += len(doc_pm)
    doc_events = [d for d in doc_events if not d["is_pm"]]
    for d in doc_events:
        month = int(d["month"])
        month_counts[month] = month_counts.get(month, 0) + 1
        car = cars.setdefault(
            (d["car_id"], d["branch_company_id"]),
            {
                "label": car_label(d),
                "company": d["branch_company__name"] or "",
                "count": 0,
                "durations": [],
                "spans": [],
            },
        )
        car["count"] += 1
    failure_count = len(failures) + len(doc_events)

    mtbf = cal_mtbf(work_total, failure_count)
    mttr = cal_mean(durations)
    availability = mtbf / (mtbf + mttr) * 100 if mtbf is not None and mttr is not None else None

    top_cars = sorted(
        cars.values(),
        key=lambda c: (c["count"], cal_mean(c["durations"]) or 0),
        reverse=True,
    )[:10]
    # Downtime = ชั่วโมงที่รถหยุดซ่อม (แจ้งซ่อม -> ปิดงาน) ของใบที่ปิดงานแล้ว
    # ใบที่เปิดซ้อนกันของคันเดียวกันนับเวลาครั้งเดียว · รายเดือนนับตามเดือนที่เริ่มหยุด
    month_downtime = {}
    for c in cars.values():
        c["downtime"] = 0.0
        for start, hours in merge_spans(c["spans"]):
            c["downtime"] += hours
            month_downtime[start.month] = month_downtime.get(start.month, 0) + hours
    top_downtime = sorted(
        (c for c in cars.values() if c["downtime"] > 0),
        key=lambda c: c["downtime"],
        reverse=True,
    )[:10]

    trend_mttr = [cal_mean(month_durations.get(m, [])) for m in months]
    planned = pm_count + failure_count

    return {
        "failure_count": failure_count,
        # ส่วนที่นับจากใบจ่ายอะไหล่ (รถที่ไม่มีใบแจ้งซ่อม)
        "doc_failure_count": len(doc_events),
        "doc_pm_count": len(doc_pm),
        "repair_closed": len(durations),
        "mtbf": mtbf,
        "mttr": mttr,
        "availability": availability,
        "downtime_hours": sum(c["downtime"] for c in cars.values()),
        "pm_count": pm_count,
        # สัดส่วน PM ในงาน PM + ซ่อม (None = ไม่มีทั้งสองอย่าง)
        "pm_ratio": pm_count / planned * 100 if planned else None,
        "trend": {
            "labels": [MONTHS_TH[m - 1] for m in months],
            "count": [month_counts.get(m, 0) for m in months],
            # None = ไม่มีข้อมูล (แสดงเป็นช่องว่างในกราฟ)
            "mttr": [round(v, 1) if v is not None else None for v in trend_mttr],
            "pm": [pm_months.get(m, 0) for m in months],
            "downtime": [round(month_downtime.get(m, 0), 1) for m in months],
        },
        "top_cars": {
            "labels": [c["label"] for c in top_cars],
            "companies": [c["company"] for c in top_cars],
            "count": [c["count"] for c in top_cars],
        },
        "top_downtime": {
            "labels": [c["label"] for c in top_downtime],
            "companies": [c["company"] for c in top_downtime],
            "hours": [round(c["downtime"], 1) for c in top_downtime],
        },
    }


def period_filter(year, months):
    """ตัวกรองช่วงเวลา: ปี + เดือนแรกถึงเดือนสุดท้ายของ months"""
    return {"year": year, "month__gte": months[0], "month__lte": months[-1]}


# หน้ารวมทุกบริษัท: รถคันเดียวกันที่ลงข้อมูลไว้หลายบริษัท รวมเป็นแถวเดียว
# (ยานพาหนะ, รถบรรทุก, เครื่องจักรกลหนัก, รถเจาะ)
MERGE_COMPANIES_CAR_DEPS = {1, 2, 3, 6}
BRANCH_ID_SEP = ","


def branch_ids(value):
    """branch_company_id ของแถวรถ -> list ของ id (แถวที่รวมหลายบริษัทเก็บเป็น "06,15")"""
    return [b for b in str(value or "").split(BRANCH_ID_SEP) if b]


def merges_companies(company_code, car_dep_id, company_ids):
    """ดูทุกบริษัท + แผนกที่รวมรถคันเดียวกันข้ามบริษัท"""
    return (
        company_code == ALL_COMPANIES
        and car_dep_id in MERGE_COMPANIES_CAR_DEPS
        and len(company_ids) > 1
    )


# ค่าดิบที่บวกกันได้ (ค่าอัตราส่วนคำนวณใหม่หลังรวม)
_RAW_SUMS = (
    "repair_total", "oil_total", "km_total", "km_liters",
    "work_total", "work_days", "failure_count",
)  # fmt: skip
_RAW_ONLY = ("work_days", "durations", "spans")


def car_table_raw(car_dep_id, year, company_ids, car_type_id, months=range(1, 13)):
    """ยอดดิบของตารางรถ แถวละ รถ + บริษัท (ทะเบียนเดียวกันอาจอยู่คนละบริษัท)

    คืน (rows, all_durations) ส่งต่อให้ finish_car_table
    """
    table_filter = {
        "car_dep_id": car_dep_id,
        **period_filter(year, months),
        "branch_company_id__in": company_ids,
        "car_id__isnull": False,
    }
    if car_type_id is not None:
        table_filter["car__car_type_id"] = car_type_id

    group_fields = (
        "car_id",
        "car__code",
        "car__name",
        "car__start_year",
        "car__brand",
        "car__car_model",
        "car__car_type_id",
        "car__car_type__name",
        "branch_company_id",
        "branch_company__name",
    )
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
                "start_year": item.get("car__start_year"),
                "brand": item.get("car__brand"),
                "car_model": item.get("car__car_model"),
                "age": car_age(item.get("car__start_year"), year),
                "car_type_id": item.get("car__car_type_id"),
                "car_type_name": item.get("car__car_type__name"),
                "repair_total": 0.0,
                "oil_total": 0.0,
                "km_total": 0.0,
                "km_liters": 0.0,
                "work_total": 0.0,
                "work_days": 0.0,
                "failure_count": 0,
                "durations": [],
                "spans": [],
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
        .annotate(
            oil_total=Sum("sum_liter"),
            km_total=Sum("sum_km"),
            # ลิตรเฉพาะเดือนที่มีเลขไมล์ เดือนที่เติมน้ำมันแต่ไม่ได้บันทึกไมล์จะไม่ทำให้ ลิตร/กม. สูงเกินจริง
            km_liters=Sum(
                Case(
                    When(sum_km__gt=0, then=F("sum_liter")),
                    default=Value(0),
                    output_field=FloatField(),
                ),
                output_field=FloatField(),
            ),
        )
    ):
        row = ensure_row(item)
        row["oil_total"] = float(item["oil_total"] or 0)
        row["km_total"] = float(item["km_total"] or 0)
        row["km_liters"] = float(item["km_liters"] or 0)

    # ชั่วโมงทำงาน: รถบรรทุก/ยานพาหนะใช้เวลางานในบันทึกการใช้รถ (SummaryCarJob)
    # วันที่ทำงาน (count_diff_time) มาจาก SummaryWork เสมอ
    work_items = {}
    for item in (
        SummaryWork.objects.filter(**table_filter)
        .values(*group_fields)
        .annotate(work_total=Sum("sum_diff_mile"), work_days=Sum("count_diff_time"))
    ):
        work_items[(item["car_id"], item["branch_company_id"])] = item
    work_model, _ = work_source(car_dep_id)
    if work_model is SummaryCarJob:
        for item in work_items.values():
            item["work_total"] = 0
        for item in (
            SummaryCarJob.objects.filter(**table_filter)
            .values(*group_fields)
            .annotate(work_total=Sum("hours"))
        ):
            key = (item["car_id"], item["branch_company_id"])
            work_items.setdefault(key, {**item, "work_days": 0})["work_total"] = item["work_total"]

    for item in work_items.values():
        row = ensure_row(item)
        row["work_total"] = float(item["work_total"] or 0)
        row["work_days"] = float(item["work_days"] or 0)

    # ใบแจ้งซ่อมประเภท "ซ่อม" ต่อคัน -> MTBF / MTTR
    all_durations = []
    for item in SummaryMaintenance.objects.filter(**table_filter, ma_type=MA_TYPE_BREAKDOWN).values(
        *group_fields, "reported_at", "finished_at"
    ):
        row = ensure_row(item)
        row["failure_count"] += 1
        hours = repair_hours(item["reported_at"], item["finished_at"])
        if hours is not None:
            all_durations.append(hours)
            row["durations"].append(hours)
            row["spans"].append(repair_span(item["reported_at"], item["finished_at"]))

    # รถที่ไม่มีใบแจ้งซ่อม: นับครั้งที่ซ่อมจากใบจ่ายอะไหล่ (ให้ตรงกับส่วนการเสียและเวลาซ่อม)
    doc_fields = [f for f in group_fields if f not in ("car_id", "branch_company_id")]
    for item in doc_repair_events(table_filter, doc_fields):
        if not item["is_pm"]:
            ensure_row(item)["failure_count"] += 1

    return list(rows.values()), all_durations


def merge_company_rows(raw_rows):
    """รวมแถวของรถคันเดียวกันที่อยู่หลายบริษัท (บวกค่าดิบ ชื่อบริษัทคั่นด้วย ", ")"""
    merged = {}
    for r in sorted(raw_rows, key=lambda r: str(r["branch_company_id"])):
        m = merged.get(r["car_id"])
        if m is None:
            merged[r["car_id"]] = {
                **r,
                "branch_company_id": str(r["branch_company_id"]),
                "durations": list(r["durations"]),
                "spans": list(r["spans"]),
            }
            continue
        m["branch_company_id"] += BRANCH_ID_SEP + str(r["branch_company_id"])
        m["branch_company_name"] = ", ".join(
            n for n in (m["branch_company_name"], r["branch_company_name"]) if n
        )
        for field in _RAW_SUMS:
            m[field] += r[field]
        m["durations"] += r["durations"]
        m["spans"] += r["spans"]
    return list(merged.values())


def finish_car_table(raw_rows, all_durations, car_dep_id, merge_companies=False):
    """ยอดดิบ -> แถวตารางรถ (ค่าอัตราส่วน MTBF/MTTR) + แถวรวม (ไม่แก้ raw_rows)"""
    if merge_companies:
        raw_rows = merge_company_rows(raw_rows)
    hours_per_day = hours_per_day_by_car_dep(car_dep_id)
    table_rows = []
    for raw in raw_rows:
        row = {k: v for k, v in raw.items() if k not in _RAW_ONLY}
        work_total = row["work_total"]
        work_days = raw["work_days"]
        row["percent_ma"] = (
            work_total / (work_days * hours_per_day) * 100
            if work_days > 0 and hours_per_day > 0
            else 0.0
        )
        row["avg_work_per_day"] = work_total / work_days if work_days > 0 else 0.0
        row["fuel_rate"] = row["oil_total"] / work_total if work_total > 0 else 0.0
        row["repair_cost_per_hr"] = row["repair_total"] / work_total if work_total > 0 else 0.0
        row["liter_per_km"] = row["km_liters"] / row["km_total"] if row["km_total"] > 0 else 0.0
        row["mtbf"] = cal_mtbf(work_total, row["failure_count"])
        row["mttr"] = cal_mean(raw["durations"])
        row["downtime_hours"] = sum(h for _, h in merge_spans(raw["spans"]))
        table_rows.append(row)

    table_rows.sort(key=lambda r: (r["code"], r["branch_company_name"]))
    work_sum = sum(r["work_total"] for r in table_rows)
    oil_sum = sum(r["oil_total"] for r in table_rows)
    km_sum = sum(r["km_total"] for r in table_rows)
    km_liters_sum = sum(r.pop("km_liters", 0.0) for r in table_rows)
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
        "km_total": km_sum,
        "liter_per_km": km_liters_sum / km_sum if km_sum > 0 else 0,
        "repair_total": repair_sum,
        "repair_cost_per_hr": repair_sum / work_sum if work_sum > 0 else 0,
        "failure_count": failure_sum,
        "mtbf": cal_mtbf(work_sum, failure_sum),
        "mttr": cal_mean(all_durations),
        "downtime_hours": sum(r["downtime_hours"] for r in table_rows),
    }
    return table_rows, totals


def build_car_table(
    car_dep_id, year, company_ids, car_type_id, months=range(1, 13), merge_companies=False
):
    raw_rows, all_durations = car_table_raw(car_dep_id, year, company_ids, car_type_id, months)
    return finish_car_table(raw_rows, all_durations, car_dep_id, merge_companies)


def build_branch_compare(car_rows):
    """เทียบสาขา/บริษัท (เมื่อดูหลายบริษัท) จากแถวในตารางรถ — ตัวเลขจึงตรงกับตาราง"""
    branches = {}
    for r in car_rows:
        b = branches.setdefault(
            r["branch_company_id"],
            {
                "branch_company_id": str(r["branch_company_id"]),
                "branch_company_name": r["branch_company_name"] or UNKNOWN,
                "car_count": 0,
                "repair_total": 0.0,
                "work_total": 0.0,
                "failure_count": 0,
                "downtime_hours": 0.0,
                "_ma": [],
            },
        )
        b["car_count"] += 1
        b["repair_total"] += r["repair_total"]
        b["work_total"] += r["work_total"]
        b["failure_count"] += r["failure_count"]
        b["downtime_hours"] += r["downtime_hours"]
        if r["percent_ma"] > 0:
            b["_ma"].append(r["percent_ma"])

    result = []
    for b in branches.values():
        ma = b.pop("_ma")
        work = b["work_total"]
        b["repair_cost_per_hr"] = b["repair_total"] / work if work > 0 else None
        b["percent_ma"] = cal_mean(ma)
        b["mtbf"] = cal_mtbf(work, b["failure_count"])
        result.append(b)
    return sorted(result, key=lambda b: b["repair_total"], reverse=True)


# -------------------------------------------------------------- dashboard


@dataclass
class DashboardFilters:
    company: str
    year: int
    car_dep: int = 1
    car_type: int | None = None  # None = ทุกชนิด
    car_id: int | None = None
    branch_company_id: str | None = None
    month_from: int | None = None  # None = เดือนแรกของปี
    month_to: int | None = None  # None = เดือนล่าสุดที่มีข้อมูล


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


def build_unmatched(year, company_ids, months=range(1, 13)):
    """ค่าใช้จ่ายที่ remark จับคู่กับรถใน webstock ไม่ได้ รวมทั้งปีต่อ remark + บริษัท

    ไม่มีแผนก จึงไม่กรองตามแท็บแผนก/ประเภทรถ/คันที่เลือก
    """
    rows = list(
        SummaryUnmatched.objects.filter(
            **period_filter(year, months), branch_company_id__in=company_ids
        )
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


def merge_unmatched_months(by_month, year, company_ids, car_type, months=range(1, 13)):
    """เพิ่มค่าซ่อมที่จับคู่กับรถไม่ได้เข้าไปในยอดรายเดือน (เมื่อกรองประเภทรถอยู่ ไม่รวม เพราะไม่รู้ประเภท)"""
    if car_type is not None:
        return by_month
    totals = {int(r["month"]): dict(r) for r in by_month}
    extra = (
        SummaryUnmatched.objects.filter(
            **period_filter(year, months), branch_company_id__in=company_ids
        )
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


PERIOD_KEYS = {"year", "month__gte", "month__lte"}


def available_years(company_ids, selected_year, today):
    """ปีที่มีข้อมูลค่าซ่อมหรือชั่วโมงทำงาน ใหม่ -> เก่า (มีปีปัจจุบันและปีที่เลือกเสมอ)"""
    years = set(
        SummaryRepair.objects.filter(branch_company_id__in=company_ids)
        .values_list("year", flat=True)
        .distinct()
    )
    years |= set(
        SummaryWork.objects.filter(branch_company_id__in=company_ids)
        .values_list("year", flat=True)
        .distinct()
    )
    years |= {today.year, selected_year}
    return sorted((y for y in years if y), reverse=True)


def build_compare(
    car_dep_id, filters, company_ids, car_type, months, include_unmatched, merge_companies=False
):
    """ตัวเลขช่วงเดียวกันของปีก่อน (เดือนเดียวกัน) ไว้เทียบกับแผงหัวและแถบตัวเลขสรุป

    เทียบระดับตัวกรอง (บริษัท/แผนก/ประเภทรถ) เหมือนแถบตัวเลขสรุปที่ไม่เปลี่ยนตามรถที่เลือก
    """
    year = filters.year - 1
    _, totals = build_car_table(car_dep_id, year, company_ids, car_type, months, merge_companies)
    has_data = bool(totals["repair_total"] or totals["work_total"] or totals["failure_count"])
    repair_total = totals["repair_total"]
    if include_unmatched:
        repair_total += build_unmatched(year, company_ids, months)["repair_total"]
    return {
        "year": year,
        "month_from": months[0],
        "month_to": months[-1],
        "has_data": has_data,
        "repair_total": repair_total,
        "totals": totals if has_data else None,
    }


def build_dashboard(user, filters: DashboardFilters, today=None, now=None):
    # import ที่นี่ เพราะ open_jobs ใช้ to_gregorian จากไฟล์นี้
    from dbapp.services.model_compare import build_model_benchmark, build_model_comparison
    from dbapp.services.open_jobs import build_open_jobs
    from dbapp.services.parts import build_parts
    from dbapp.services.watchlist import build_watchlist

    today = today or date.today()
    company_ids = resolve_company_ids(user, filters.company)
    is_other = filters.car_dep == OTHER_CAR_DEP
    # car_dep_id=None -> Django กรองเป็น IS NULL (รถที่ไม่มีแผนก)
    car_dep_id = None if is_other else filters.car_dep
    noun = unit_noun(car_dep_id, is_other)
    fuel = fuel_spec(car_dep_id)

    # เดือน 1 -> เดือนปัจจุบัน (ถ้าเป็นปีที่ผ่านมาแล้วแสดงครบ 12 เดือน)
    # เลือกช่วงเดือนได้ภายในนั้น (เกินเดือนล่าสุดจะตัดให้)
    last_month = today.month if filters.year >= today.year else 12
    month_to = min(filters.month_to or last_month, last_month)
    month_from = min(max(filters.month_from or 1, 1), month_to)
    months = range(month_from, month_to + 1)

    car_types = list(available_car_types(car_dep_id, filters.year, company_ids))
    car_type = filters.car_type
    if car_type is not None and car_type not in {ct.id for ct in car_types}:
        car_type = None

    raw_rows, all_durations = car_table_raw(car_dep_id, filters.year, company_ids, car_type, months)
    # แถวละรถ + บริษัท (ใช้เทียบสาขา)
    company_rows, company_totals = finish_car_table(raw_rows, all_durations, car_dep_id)
    # หน้ารวมทุกบริษัท: รถคันเดียวกันหลายบริษัทเป็นแถวเดียว (branch_company_id = "06,15")
    merge = merges_companies(filters.company, car_dep_id, company_ids)
    car_rows, car_totals = (
        finish_car_table(raw_rows, all_durations, car_dep_id, merge_companies=True)
        if merge
        else (company_rows, company_totals)
    )

    # เลือกรถด้วย car_id + branch_company_id (code ของรถอาจว่างหรือซ้ำกัน)
    # รับได้ทั้งบริษัทเดียว (กดจากกราฟ/ใบค้าง) และหลายบริษัท (แถวที่รวมไว้)
    selected_car = None
    if filters.car_id is not None and filters.branch_company_id:
        wanted = set(branch_ids(filters.branch_company_id))
        selected_car = next(
            (
                r
                for r in car_rows
                if r["car_id"] == filters.car_id
                and wanted & set(branch_ids(r["branch_company_id"]))
            ),
            None,
        )
        # รถที่ไม่ได้อยู่ในบริษัทที่ user มองเห็น จะไม่อยู่ในตาราง -> ไม่ให้กรองถึง
        if selected_car is None:
            filters.car_id = None
            filters.branch_company_id = None
        else:
            filters.branch_company_id = str(selected_car["branch_company_id"])

    base_filter = {"car_dep_id": car_dep_id, **period_filter(filters.year, months)}
    if car_type is not None:
        base_filter["car__car_type_id"] = car_type
    if selected_car:
        base_filter["car_id"] = filters.car_id
        base_filter["branch_company_id__in"] = branch_ids(filters.branch_company_id)
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
    if work_source(car_dep_id)[0] is SummaryCarJob:
        # รถบรรทุก/ยานพาหนะ: ชั่วโมงจากเวลางาน (ไม่ใช่ผลต่างเลขไมล์)
        job_hours = {
            int(i["month"]): float(i["hours"] or 0)
            for i in SummaryCarJob.objects.filter(**base_filter)
            .values("month")
            .annotate(hours=Sum("hours"))
        }
        for item in work_by_month:
            item["total_mile"] = job_hours.pop(int(item["month"]), 0.0)
        for month, hours in job_hours.items():
            work_by_month.append(
                {"month": month, "month_th": None, "car_dep": car_dep_id,
                 "total_mile": hours, "total_time": 0}
            )  # fmt: skip
        work_by_month.sort(key=lambda i: int(i["month"]))

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
        unmatched = build_unmatched(filters.year, company_ids, months)
        by_month = merge_unmatched_months(by_month, filters.year, company_ids, car_type, months)

    repair_by_month = {int(i["month"]): float(i["amount_sum"] or 0) for i in by_month}
    work_by_month_map = {int(i["month"]): float(i["total_mile"] or 0) for i in work_by_month}

    def amounts(rows):
        return [float(r["amount_sum"] or 0) for r in rows]

    result = {
        "filters": {
            "company": filters.company,
            "year": filters.year,
            "car_dep": filters.car_dep,
            "unit_noun": noun,
            "fuel_field": fuel["field"],
            "fuel_unit": fuel["unit"],
            "month_from": month_from,
            "month_to": month_to,
            "years": available_years(company_ids, filters.year, today),
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
                        "car_id": c["car_id"],
                        "branch_company_id": str(c["branch_company_id"]),
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
        "parts": build_parts(base_filter),
        "jobs": build_jobs(base_filter),
        # สถานะ ณ ตอนนี้ ไม่กรองปี
        "open_jobs": build_open_jobs(
            {k: v for k, v in base_filter.items() if k not in PERIOD_KEYS}, now=now
        ),
        "compare": build_compare(
            car_dep_id,
            filters,
            company_ids,
            car_type,
            months,
            include_unmatched=is_other and not selected_car,
            merge_companies=merge,
        ),
    }
    # รถทั้งตาราง (ไม่กรองคันเดียว) เพื่อเทียบค่ากลางเหมือนตารางรถ
    table_filter = {
        "car_dep_id": car_dep_id,
        **period_filter(filters.year, months),
        "branch_company_id__in": company_ids,
    }
    if car_type is not None:
        table_filter["car__car_type_id"] = car_type
    # เทียบสาขา: เฉพาะตอนดูหลายบริษัทและไม่ได้เลือกคันเดียว
    result["branch_compare"] = (
        build_branch_compare(company_rows) if len(company_ids) > 1 and not selected_car else []
    )
    result["model_comparison"] = build_model_comparison(car_rows, fuel)
    result["model_benchmark"] = build_model_benchmark(car_rows, selected_car, fuel)
    result["watchlist"] = build_watchlist(car_rows, table_filter, result["open_jobs"], noun, fuel)
    result["insights"] = build_insights(
        result,
        # เดือนปัจจุบันยังไม่จบ ไม่นำมาคิดแนวโน้ม
        partial_last_month=filters.year == today.year and month_to == today.month,
        **data_quality_counts(filters.year, company_ids, is_other, unmatched),
        noun=noun,
        fuel=fuel,
    )
    result["last_synced_at"] = last_synced_at()
    return result


# ตารางสรุปที่ sync ลบแล้วสร้างใหม่ทุกครั้ง: created_at ล่าสุด = เวลาที่ดึงข้อมูลจาก webstock ครั้งล่าสุด
SYNCED_MODELS = (
    SummaryRepair,
    SummaryOil,
    SummaryWork,
    SummaryMaintenance,
    SummaryUnmatched,
    SummaryCarJob,
)


NO_EXPENSE_DEPT = "ไม่ระบุแผนกค่าใช้จ่าย"
NO_JOB = "ไม่ระบุรายละเอียดงาน"


def build_jobs(base_filter):
    """งานที่ทำจากบันทึกการใช้รถ แยกตามแผนกค่าใช้จ่าย -> รายละเอียดงาน
    ชั่วโมง = ผลรวมเวลางาน, กม. = ผลรวมเลขไมล์ของงาน, ครั้ง = จำนวนงานที่บันทึก
    """
    rows = (
        SummaryCarJob.objects.filter(**base_filter)
        .values("expense_dept_name", "job")
        .annotate(
            hours=Coalesce(Sum("hours"), Value(0), output_field=FloatField()),
            km=Coalesce(Sum("km"), Value(0), output_field=FloatField()),
            trips=Coalesce(Sum("trips"), Value(0)),
        )
    )
    cars = {
        (i["expense_dept_name"], i["job"]): i["cars"]
        for i in SummaryCarJob.objects.filter(**base_filter)
        .values("expense_dept_name", "job")
        .annotate(cars=Count("car_id", distinct=True))
    }
    dept_cars = {
        i["expense_dept_name"]: i["cars"]
        for i in SummaryCarJob.objects.filter(**base_filter)
        .values("expense_dept_name")
        .annotate(cars=Count("car_id", distinct=True))
    }

    depts = {}
    for r in rows:
        name = r["expense_dept_name"] or ""
        dept = depts.setdefault(
            name,
            {
                "name": name or NO_EXPENSE_DEPT,
                "assigned": bool(name),
                "hours": 0.0,
                "km": 0.0,
                "trips": 0,
                "cars": dept_cars.get(r["expense_dept_name"], 0),
                "jobs": [],
            },
        )
        dept["hours"] += r["hours"]
        dept["km"] += r["km"]
        dept["trips"] += r["trips"]
        dept["jobs"].append(
            {
                "job": r["job"] or NO_JOB,
                "hours": r["hours"],
                "km": r["km"],
                "trips": r["trips"],
                "cars": cars.get((r["expense_dept_name"], r["job"]), 0),
            }
        )

    departments = sorted(depts.values(), key=lambda d: (not d["assigned"], -d["hours"]))
    for d in departments:
        d["jobs"].sort(key=lambda j: (-j["hours"], -j["trips"]))
    return {
        "hours": sum(d["hours"] for d in departments),
        "km": sum(d["km"] for d in departments),
        "trips": sum(d["trips"] for d in departments),
        "departments": departments,
    }


def last_synced_at():
    """เวลาที่อัปเดตข้อมูลจาก webstock ครั้งล่าสุด (ทั้งปุ่มอัปเดตและงานอัปเดตอัตโนมัติ)"""
    stamps = [m.objects.aggregate(at=Max("created_at"))["at"] for m in SYNCED_MODELS]
    return max((s for s in stamps if s), default=None)


# แผนกที่เทียบน้ำมันเป็น ลิตร/กม. = แผนกที่ชั่วโมงมาจากเวลางาน (เลขไมล์เป็น กม.)
FUEL_PER_KM_CAR_DEPS = JOB_HOURS_CAR_DEPS


def fuel_spec(car_dep_id):
    return FUEL_PER_KM if car_dep_id in FUEL_PER_KM_CAR_DEPS else FUEL_PER_HOUR


OTHER_NOUN = "รถ/เครื่องจักร"  # แท็บอื่นๆ มีทั้งรถและเครื่องจักร


def unit_noun(car_dep_id, is_other):
    """คำที่ใช้เรียกรถในข้อความ = ชื่อแผนกที่เลือก (ยานพาหนะ, เครื่องจักรกลหนัก, ...)"""
    if is_other:
        return OTHER_NOUN
    name = BaseCarDepartment.objects.filter(id=car_dep_id).values_list("name", flat=True).first()
    return (name or "").strip() or OTHER_NOUN


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
