"""ประวัติรถรายคัน: ใบแจ้งซ่อมทุกใบ ค่าซ่อม/ชั่วโมงทำงานรายเดือน และยอดสะสม

ไม่กรองปี: ดูทุกช่วงที่ sync มา (ค่าซ่อม/ชั่วโมงทำงานมีตั้งแต่ต้นปีก่อนหน้า)
รถหนึ่งคันแยกตามบริษัท (ทะเบียนเดียวกันอาจอยู่คนละบริษัท) เหมือนตารางรถใน dashboard
หน้ารวมทุกบริษัทรวมรถคันเดียวกันหลายบริษัทเป็นแถวเดียว: branch_company_id = "06,15"
"""

from datetime import datetime

from django.db.models import Count, Sum

from dbapp.models import (
    BaseBranchCompany,
    BaseCar,
    SummaryMaintenance,
    SummaryRepair,
)
from dbapp.services.dashboard import (
    BUDDHIST_ERA_OFFSET,
    MA_TYPE_BREAKDOWN,
    MA_TYPE_NAMES,
    MA_TYPE_PM,
    CompanyAccessDenied,
    branch_ids,
    car_age,
    doc_repair_events,
    merge_spans,
    repair_hours,
    repair_span,
    to_gregorian,
    unit_noun,
    user_companies,
    work_source,
)
from dbapp.services.maintenance_stage import STAGE_LABELS
from dbapp.services.parts import doc_job_list, part_rows

MONTHS_SHORT_TH = [
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]  # fmt: skip
MAX_MONTHS = 24  # กราฟรายเดือนแสดงย้อนหลังไม่เกิน 24 เดือน


class CarNotFound(Exception):
    pass


def month_label(year, month):
    return f"{MONTHS_SHORT_TH[month - 1]} {(year + BUDDHIST_ERA_OFFSET) % 100:02d}"


def _month_range(first, last):
    """(ปี, เดือน) ต่อเนื่องตั้งแต่ first ถึง last (เดือนที่ไม่มีข้อมูลก็แสดงเป็น 0)"""
    y, m = first
    out = []
    while (y, m) <= last:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _by_month(queryset, field, func=Sum):
    return {
        (int(r["year"]), int(r["month"])): float(r["v"] or 0)
        for r in queryset.values("year", "month").annotate(v=func(field))
    }


def build_car_history(user, car_id, branch_company_id, now=None):
    now = now or datetime.now()
    allowed = {str(i) for i in user_companies(user).values_list("id", flat=True)}
    company_ids = branch_ids(branch_company_id)
    if not company_ids or not set(company_ids) <= allowed:
        raise CompanyAccessDenied(branch_company_id)
    car = BaseCar.objects.select_related("car_type", "car_dep").filter(id=car_id).first()
    companies = {str(c.id): c for c in BaseBranchCompany.objects.filter(id__in=company_ids)}
    if car is None or len(companies) != len(set(company_ids)):
        raise CarNotFound(car_id)

    car_filter = {"car_id": car_id, "branch_company_id__in": company_ids}
    work_model, work_field = work_source(car.car_dep_id)

    repair = _by_month(SummaryRepair.objects.filter(**car_filter), "amount")
    work = _by_month(work_model.objects.filter(**car_filter), work_field)
    tickets_qs = SummaryMaintenance.objects.filter(**car_filter)
    breakdowns = _by_month(tickets_qs.filter(ma_type=MA_TYPE_BREAKDOWN), "id", Count)
    pms = _by_month(tickets_qs.filter(ma_type=MA_TYPE_PM), "id", Count)
    # ไม่มีใบแจ้งซ่อมเลย: นับครั้งที่ซ่อมจากใบจ่ายอะไหล่ (Express) แทน
    doc_events = doc_repair_events(car_filter, ("year",))
    for d in doc_events:
        key = (int(d["year"]), int(d["month"]))
        target = pms if d["is_pm"] else breakdowns
        target[key] = target.get(key, 0) + 1
    doc_pm_count = sum(1 for d in doc_events if d["is_pm"])
    doc_breakdown_count = len(doc_events) - doc_pm_count

    keys = set(repair) | set(work) | set(breakdowns) | set(pms)
    months = _month_range(min(keys), max(keys))[-MAX_MONTHS:] if keys else []

    rows = list(
        tickets_qs.order_by("-reported_at").values(
            "ext_id",
            "ref_no",
            "reported_at",
            "finished_at",
            "ma_type",
            "broke_reason",
            "car_state",
            "is_complete",
            "stage",
        )
    )
    # อะไหล่ = ใบจ่ายสินค้าภายใน (Express) ที่อ้างอิงเลขที่ใบแจ้งซ่อม
    parts = part_rows(r["ext_id"] for r in rows)

    tickets = []
    spans = []
    for r in rows:
        hours = repair_hours(r["reported_at"], r["finished_at"])
        is_open = r["finished_at"] is None and r["is_complete"] is not True
        if hours is not None and r["ma_type"] == MA_TYPE_BREAKDOWN:
            spans.append(repair_span(r["reported_at"], r["finished_at"]))
        items = parts.get(r["ext_id"], [])
        tickets.append(
            {
                "ext_id": r["ext_id"],
                "ref_no": r["ref_no"] or "",
                "reported_at": to_gregorian(r["reported_at"]),
                "finished_at": to_gregorian(r["finished_at"]),
                "ma_type": r["ma_type"] or "",
                "ma_type_name": MA_TYPE_NAMES.get(r["ma_type"], "ไม่ระบุ"),
                "broke_reason": r["broke_reason"] or "",
                "car_state": r["car_state"] or "",
                "is_open": is_open,
                "stage_label": STAGE_LABELS.get(r["stage"], "") if is_open else "",
                "repair_hours": hours,
                "parts": items,
                "parts_amount": sum(p["amount"] for p in items),
                "parts_count": len(items),
            }
        )

    # ค่าซ่อมแยกตามระบบ (ใบเบิกค่าซ่อมใน webstock เก็บเป็นยอดรายเดือน ไม่ผูกกับใบแจ้งซ่อม)
    repair_items = [
        {
            "year": int(r["year"]),
            "month": int(r["month"]),
            "label": month_label(int(r["year"]), int(r["month"])),
            "repair_name": r["repair_name"] or "ไม่ระบุ",
            "amount": float(r["amount"] or 0),
        }
        for r in SummaryRepair.objects.filter(**car_filter)
        .values("year", "month", "repair_name")
        .annotate(amount=Sum("amount"))
        .order_by("-year", "-month", "-amount")
    ]

    # รถที่ไม่มีใบแจ้งซ่อม: การซ่อมและอะไหล่จากใบจ่ายอะไหล่ (Express)
    doc_jobs = doc_job_list(car_filter)

    repair_total = sum(repair.values())
    work_total = sum(work.values())
    return {
        "car": {
            "car_id": car.id,
            "code": car.code or "",
            "name": car.name,
            "brand": car.brand,
            "car_model": car.car_model,
            "start_year": car.start_year,
            "age": car_age(car.start_year, now.year),
            "car_type_name": car.car_type.name if car.car_type else None,
            "car_dep_id": car.car_dep_id,
            "car_dep_name": car.car_dep.name if car.car_dep else None,
            "unit_noun": unit_noun(car.car_dep_id, car.car_dep_id is None),
            "branch_company_id": ",".join(company_ids),
            "branch_company_name": ", ".join(
                companies[i].name or "" for i in dict.fromkeys(company_ids)
            ),
        },
        "totals": {
            "repair_total": repair_total,
            "work_total": work_total,
            "repair_cost_per_hr": repair_total / work_total if work_total > 0 else None,
            "ticket_count": len(tickets),
            "breakdown_count": sum(1 for t in tickets if t["ma_type"] == MA_TYPE_BREAKDOWN)
            + doc_breakdown_count,
            "doc_breakdown_count": doc_breakdown_count,
            "pm_count": sum(1 for t in tickets if t["ma_type"] == MA_TYPE_PM) + doc_pm_count,
            "doc_pm_count": doc_pm_count,
            "open_count": sum(1 for t in tickets if t["is_open"]),
            # ใบที่เปิดซ้อนกันนับเวลาครั้งเดียว
            "downtime_hours": sum(h for _, h in merge_spans(spans)),
            # อะไหล่ในใบแจ้งซ่อม + อะไหล่จากใบจ่ายของรถที่ไม่มีใบแจ้งซ่อม
            "parts_total": sum(t["parts_amount"] for t in tickets)
            + sum(j["amount"] for j in doc_jobs),
            "data_from": month_label(*months[0]) if months else None,
        },
        "monthly": {
            "labels": [month_label(y, m) for y, m in months],
            "repair": [repair.get(k, 0.0) for k in months],
            "work": [round(work.get(k, 0.0), 1) for k in months],
            "breakdowns": [int(breakdowns.get(k, 0)) for k in months],
            "pm": [int(pms.get(k, 0)) for k in months],
        },
        "repair_items": repair_items,
        "tickets": tickets,
        "doc_jobs": doc_jobs,
    }
