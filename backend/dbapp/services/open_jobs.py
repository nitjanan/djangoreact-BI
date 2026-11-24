"""ใบแจ้งซ่อมที่ยังเปิดอยู่ (หัวหน้าช่างยังไม่ปิดงาน) ณ ตอนนี้

ไม่ขึ้นกับปีที่เลือก เพราะเป็นสถานะปัจจุบัน — ใบที่แจ้งปีก่อนแต่ยังไม่ปิดก็ยังนับ
ใบที่ is_complete = True แต่ไม่มีเวลาปิดงาน ไม่นับ (ถือว่างานจบแล้ว แค่ไม่ได้บันทึกเวลา)
"""

from datetime import datetime

from dbapp.models import SummaryMaintenance
from dbapp.services.dashboard import to_gregorian
from dbapp.services.maintenance_stage import STAGE_LABELS, STAGES
from dbapp.services.parts import part_rows

# car_state จาก webstock
IMMOBILE_STATE = "ไม่สามารถทำการเคลื่อนย้ายได้"

# (ชื่อช่วง, อายุสูงสุดเป็นวัน) — ช่วงสุดท้ายไม่มีเพดาน
AGE_BUCKETS = [("0–1 วัน", 1), ("1–3 วัน", 3), ("3–7 วัน", 7), ("มากกว่า 7 วัน", None)]
STALE_DAYS = 7

NO_STAGE = "unknown"
NO_STAGE_LABEL = "ยังไม่มีข้อมูลเอกสาร"


def open_jobs_queryset(base_filter):
    return SummaryMaintenance.objects.filter(**base_filter, finished_at__isnull=True).exclude(
        is_complete=True
    )


def _bucket_index(days):
    for i, (_, limit) in enumerate(AGE_BUCKETS):
        if limit is None or days <= limit:
            return i
    return len(AGE_BUCKETS) - 1


def _days(now, since):
    since = to_gregorian(since)
    return max((now - since).days, 0) if since else None


def build_open_jobs(base_filter, now=None):
    """base_filter: ตัวกรองแบบเดียวกับ dashboard แต่ไม่มี year"""
    now = now or datetime.now()
    today = now.date()
    rows = open_jobs_queryset(base_filter).values(
        "ext_id",
        "ref_no",
        "car_id",
        "car__code",
        "car__name",
        "branch_company_id",
        "branch_company__name",
        "reported_at",
        "car_state",
        "broke_reason",
        "stage",
        "stage_since",
        "po_due",
        "documents",
    )

    buckets = [0] * len(AGE_BUCKETS)
    stage_counts = dict.fromkeys([code for code, _ in STAGES] + [NO_STAGE], 0)
    cars = set()
    immobile_cars = set()
    jobs = []

    for row in rows:
        days = _days(now, row["reported_at"])
        buckets[_bucket_index(days)] += 1
        immobile = row["car_state"] == IMMOBILE_STATE
        car_key = (row["car_id"], row["branch_company_id"])
        cars.add(car_key)
        if immobile:
            immobile_cars.add(car_key)

        stage = row["stage"] if row["stage"] in STAGE_LABELS else NO_STAGE
        stage_counts[stage] += 1
        po_due = row["po_due"]

        jobs.append(
            {
                "ext_id": row["ext_id"],
                "ref_no": row["ref_no"] or "",
                "car_id": row["car_id"],
                "branch_company_id": row["branch_company_id"] or "",
                "branch_company_name": row["branch_company__name"] or "",
                "code": row["car__code"] or "",
                "name": row["car__name"],
                "reported_at": to_gregorian(row["reported_at"]),
                "days": days,
                "immobile": immobile,
                "broke_reason": row["broke_reason"] or "",
                "stage": stage,
                "stage_label": STAGE_LABELS.get(stage, NO_STAGE_LABEL),
                "stage_days": _days(now, row["stage_since"]),
                "po_due": po_due,
                "po_overdue": bool(po_due and po_due < today),
                "documents": row["documents"] or [],
            }
        )

    jobs.sort(key=lambda j: j["days"], reverse=True)

    # อะไหล่ที่จ่ายไปแล้วระหว่างซ่อม (เฉพาะใบที่คลังกรอกเลขที่ใบแจ้งซ่อม)
    parts = part_rows(j["ext_id"] for j in jobs)
    for j in jobs:
        j["parts"] = parts.get(j["ext_id"], [])
        j["parts_amount"] = sum(p["amount"] for p in j["parts"])

    return {
        "total": len(jobs),
        "car_count": len(cars),
        "immobile_car_count": len(immobile_cars),
        "stale_count": sum(1 for j in jobs if j["days"] > STALE_DAYS),
        "stale_days": STALE_DAYS,
        "has_process": stage_counts[NO_STAGE] < len(jobs),
        "buckets": [
            {"label": label, "count": count}
            for (label, _), count in zip(AGE_BUCKETS, buckets)  # noqa: B905 (strict= ต้อง Python 3.10)
        ],
        "stages": [
            {"code": code, "label": label, "count": stage_counts[code]}
            for code, label in [*STAGES, (NO_STAGE, NO_STAGE_LABEL)]
            if stage_counts[code]
        ],
        "jobs": jobs,
    }
