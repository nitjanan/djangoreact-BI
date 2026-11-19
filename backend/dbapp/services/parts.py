"""อะไหล่ที่ใช้ในการซ่อม = ใบจ่ายสินค้าภายใน-อะไหล่ ใน Express ที่อ้างอิงเลขที่ใบแจ้งซ่อม

ของที่ซื้อตามใบสั่งซื้อจะรับเข้าคลังแล้วออกใบจ่ายสินค้าภายในทุกครั้ง จึงไม่นับใบสั่งซื้อ (นับซ้ำ)
คลังเพิ่งเริ่มกรอกเลขที่ใบแจ้งซ่อม (ปี 2569) และบางบริษัทยังไม่กรอก
ข้อมูลยังไม่ครบ จึงแสดงสัดส่วนใบแจ้งซ่อมที่มีข้อมูลอะไหล่คู่กันเสมอ
"""

from collections import defaultdict
from datetime import date

from dbapp.models import SummaryMaintenance, SummaryMaintenancePart
from dbapp.services.dashboard import to_gregorian

TOP_PARTS = 15

FIELDS = ("ext_id", "docnum", "docdat", "stkcod", "name", "qty", "unit", "amount")


def _row(r):
    return {
        "docnum": r["docnum"],
        "docdat": r["docdat"],
        "stkcod": r["stkcod"],
        "name": r["name"],
        "qty": float(r["qty"]),
        "unit": r["unit"],
        "amount": float(r["amount"]),
    }


def part_rows(ext_ids):
    """{ext_id: [อะไหล่]} เรียงตามวันที่เอกสาร"""
    result = defaultdict(list)
    rows = (
        SummaryMaintenancePart.objects.filter(ext_id__in=list(ext_ids))
        .order_by("docdat", "docnum", "id")
        .values(*FIELDS)
    )
    for r in rows:
        result[r["ext_id"]].append(_row(r))
    return result


def _top_parts(rows):
    groups = {}
    for r in rows:
        g = groups.setdefault(
            r["stkcod"].upper(),
            {"stkcod": r["stkcod"], "name": "", "unit": "", "qty": 0.0, "amount": 0.0,
             "jobs": set()},
        )  # fmt: skip
        g["name"] = g["name"] or r["name"]
        g["unit"] = g["unit"] or r["unit"]
        g["qty"] += float(r["qty"])
        g["amount"] += float(r["amount"])
        g["jobs"].add(r["ext_id"])

    top = sorted(groups.values(), key=lambda g: g["amount"], reverse=True)[:TOP_PARTS]
    return [{**g, "jobs": len(g["jobs"])} for g in top]


def build_parts(base_filter, with_jobs=False):
    """base_filter: ตัวกรองแบบเดียวกับ dashboard (มีปี) ใช้กับ SummaryMaintenance

    with_jobs: ส่งรายการใบแจ้งซ่อมพร้อมอะไหล่ด้วย (ตอนเลือกรถคันเดียว)
    """
    jobs = SummaryMaintenance.objects.filter(**base_filter)
    rows = list(
        SummaryMaintenancePart.objects.filter(ext_id__in=jobs.values("ext_id")).values(*FIELDS)
    )

    amount = sum(float(r["amount"]) for r in rows)
    jobs_with_parts = len({r["ext_id"] for r in rows})

    result = {
        "job_count": jobs.count(),
        "jobs_with_parts": jobs_with_parts,
        "amount": amount,
        "amount_per_job": amount / jobs_with_parts if jobs_with_parts else None,
        "top": _top_parts(rows),
        "jobs": [],
    }

    if with_jobs and rows:
        items = defaultdict(list)
        for r in sorted(rows, key=lambda r: (r["docdat"] or date.min, r["docnum"])):
            items[r["ext_id"]].append(_row(r))
        job_rows = jobs.filter(ext_id__in=list(items)).order_by("-reported_at")
        for job in job_rows.values(
            "ext_id", "ref_no", "reported_at", "broke_reason", "finished_at"
        ):
            job_parts = items[job["ext_id"]]
            result["jobs"].append(
                {
                    "ext_id": job["ext_id"],
                    "ref_no": job["ref_no"] or "",
                    "reported_at": to_gregorian(job["reported_at"]),
                    "broke_reason": job["broke_reason"] or "",
                    "closed": job["finished_at"] is not None,
                    "amount": sum(p["amount"] for p in job_parts),
                    "parts": job_parts,
                }
            )
    return result
