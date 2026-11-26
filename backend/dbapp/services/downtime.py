"""ไทม์ไลน์รถหยุดซ่อม: แต่ละคันหยุดช่วงไหน และมีรถหยุดพร้อมกันกี่คันในแต่ละวัน

ใช้ใบแจ้งซ่อมประเภทซ่อม (เสีย) เหมือน Downtime ในส่วนการเสียและเวลาซ่อม ต่างกันที่
- ใบที่ยังไม่ปิดงานนับถึงตอนนี้ (Downtime เดิมนับเฉพาะใบที่ปิดแล้ว)
  ใบที่ยังไม่ปิดส่วนใหญ่ยังไม่ได้ระบุประเภท (webstock ใส่ประเภทตอนปิดงาน) จึงนับใบเปิดที่ไม่มีประเภทด้วย
  ใบเปิดที่ระบุประเภทอื่นแล้ว (เช่น PM) ไม่นับ
- ใบที่แจ้งก่อนช่วงที่เลือกแต่ยังหยุดอยู่ในช่วงนี้ก็นับ (ตัดเฉพาะส่วนที่อยู่ในช่วง)
"""

from calendar import monthrange
from datetime import date, datetime, time, timedelta

from django.db.models import Q

from dbapp.models import SummaryMaintenance
from dbapp.services.dashboard import (
    MA_TYPE_BREAKDOWN,
    MAX_REPAIR_HOURS,
    PERIOD_KEYS,
    car_label,
    repair_span,
    to_gregorian,
)

TOP_CARS = 20

FIELDS = (
    "ext_id",
    "ref_no",
    "broke_reason",
    "car_id",
    "car__code",
    "car__name",
    "branch_company_id",
    "branch_company__name",
    "reported_at",
    "finished_at",
    "is_complete",
)


def period_bounds(year, months, now):
    start = datetime(year, months[0], 1)
    end = datetime.combine(
        date(year, months[-1], monthrange(year, months[-1])[1]) + timedelta(days=1), time()
    )
    return start, min(end, now)


def _span(row, now):
    """(เริ่ม, จบ, ยังไม่ปิด) หรือ None ถ้าใช้ไม่ได้"""
    if row["finished_at"] is None:
        if row["is_complete"]:  # ปิดงานแล้วแต่ไม่ได้บันทึกเวลา
            return None
        start = to_gregorian(row["reported_at"])
        # แจ้งในอนาคต หรือเปิดค้างนานเกิน 1 ปี (น่าจะลืมปิด) ไม่แสดง
        if start is None or start > now or (now - start).total_seconds() / 3600 > MAX_REPAIR_HOURS:
            return None
        return start, now, True
    span = repair_span(row["reported_at"], row["finished_at"])
    return (*span, False) if span else None


def build_downtime(base_filter, year, months, now=None):
    """base_filter: ตัวกรองแบบเดียวกับ dashboard (มีปี/เดือน)"""
    now = now or datetime.now()
    start, end = period_bounds(year, months, now)
    scope = {k: v for k, v in base_filter.items() if k not in PERIOD_KEYS}
    # ใบที่แจ้งตั้งแต่ปีก่อนถึงเดือนสุดท้ายที่เลือก หรือยังไม่ปิด (ตัดตามช่วงอีกทีด้านล่าง)
    rows = SummaryMaintenance.objects.filter(
        Q(year=year - 1) | Q(year=year, month__lte=months[-1]) | Q(finished_at__isnull=True),
        Q(ma_type=MA_TYPE_BREAKDOWN) | Q(ma_type__isnull=True, finished_at__isnull=True),
        **scope,
        car_id__isnull=False,
    ).values(*FIELDS)

    cars = {}
    for row in rows:
        span = _span(row, now)
        if span is None:
            continue
        s, e, is_open = span
        s, e = max(s, start), min(e, end)
        if e <= s:
            continue
        car = cars.setdefault(
            (row["car_id"], row["branch_company_id"]),
            {
                "car_id": row["car_id"],
                "branch_company_id": str(row["branch_company_id"]),
                "label": car_label(row),
                "company": row["branch_company__name"] or "",
                "spans": [],
            },
        )
        car["spans"].append(
            {
                "start": s,
                "end": e,
                "open": is_open,
                "ref_no": row["ref_no"] or "",
                "broke_reason": row["broke_reason"] or "",
            }
        )

    # ชั่วโมงหยุด: ใบที่ซ้อนกันของคันเดียวกันนับเวลาครั้งเดียว
    days = (end.date() - start.date()).days + (1 if end.time() != time() else 0)
    daily = [0] * max(days, 0)
    for car in cars.values():
        car["spans"].sort(key=lambda sp: sp["start"])
        merged = []
        for sp in car["spans"]:
            if merged and sp["start"] <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], sp["end"])
            else:
                merged.append([sp["start"], sp["end"]])
        car["hours"] = sum((e - s).total_seconds() / 3600 for s, e in merged)
        car["open"] = any(sp["open"] for sp in car["spans"])
        down_days = set()
        for s, e in merged:
            d = s.date()
            last = (e - timedelta(microseconds=1)).date()
            while d <= last:
                down_days.add(d)
                d += timedelta(days=1)
        for d in down_days:
            i = (d - start.date()).days
            if 0 <= i < len(daily):
                daily[i] += 1

    ranked = sorted(cars.values(), key=lambda c: c["hours"], reverse=True)
    peak = max(daily, default=0)
    return {
        "start": start,
        "end": end,
        "car_count": len(cars),
        "open_car_count": sum(1 for c in cars.values() if c["open"]),
        "hours": sum(c["hours"] for c in cars.values()),
        "daily": daily,
        "peak": peak,
        "peak_date": start.date() + timedelta(days=daily.index(peak)) if peak else None,
        "cars": ranked[:TOP_CARS],
    }
