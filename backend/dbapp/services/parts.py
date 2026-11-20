"""อะไหล่ที่ใช้ในการซ่อม = ใบจ่ายสินค้าภายใน-อะไหล่ ใน Express ที่อ้างอิงเลขที่ใบแจ้งซ่อม

ของที่ซื้อตามใบสั่งซื้อจะรับเข้าคลังแล้วออกใบจ่ายสินค้าภายในทุกครั้ง จึงไม่นับใบสั่งซื้อ (นับซ้ำ)
คลังเพิ่งเริ่มกรอกเลขที่ใบแจ้งซ่อม (ปี 2569) และบางบริษัทยังไม่กรอก
ข้อมูลยังไม่ครบ จึงแสดงสัดส่วนใบแจ้งซ่อมที่มีข้อมูลอะไหล่คู่กันเสมอ

รถที่ไม่มีใบแจ้งซ่อมเลยในตัวกรองนี้ ใช้รายการอะไหล่ในใบจ่าย (SummaryRepairDoc) แทน
(ดู dashboard.ticketless_docs) การซ่อม 1 ครั้งนับแบบเดียวกับกราฟความน่าเชื่อถือ
"""

from collections import defaultdict

from dbapp.models import SummaryMaintenance, SummaryMaintenancePart
from dbapp.services.dashboard import doc_event_key, ticketless_docs

TOP_PARTS = 15

# นับเฉพาะประเภทสินค้าที่เป็นอะไหล่/พัสดุ (ไม่รวมค่าแรง งานบริการ น้ำมัน วัตถุระเบิด ฯลฯ)
PART_TYPES = ("อะไหล่", "พัสดุ")


def is_part(stktyp):
    return (stktyp or "").strip() in PART_TYPES


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

    # ใช้บ่อยที่สุดก่อน (จำนวนครั้งที่ซ่อม) เท่ากันเรียงตามมูลค่า
    top = sorted(groups.values(), key=lambda g: (len(g["jobs"]), g["amount"]), reverse=True)[
        :TOP_PARTS
    ]
    return [{**g, "jobs": len(g["jobs"])} for g in top]


def doc_jobs(base_filter):
    """การซ่อมจากใบจ่ายอะไหล่ของรถที่ไม่มีใบแจ้งซ่อม -> [{key, docnums, docdat, repair_name, parts}]

    parts มีรูปแบบเดียวกับ _row (ใส่ ext_id = key ให้ _top_parts นับจำนวนครั้ง)
    """
    events = {}
    fields = ("id", "docnum", "parts")
    docs = ticketless_docs(base_filter, fields)
    for d in docs:
        if not any(is_part(p.get("stktyp")) for p in d["parts"]):
            continue
        key = doc_event_key(d)
        event = events.setdefault(
            key,
            {"id": d["id"], "docnums": [], "docdat": d["docdat"], "is_pm": d["is_pm"], "parts": []},
        )
        event["docnums"].append(d["docnum"])
        for p in d["parts"]:
            if not is_part(p.get("stktyp")):
                continue
            event["parts"].append(
                {
                    "ext_id": key,
                    "docnum": d["docnum"],
                    "docdat": d["docdat"],
                    "stkcod": p.get("stkcod") or "",
                    "name": p.get("name") or "",
                    "qty": float(p.get("qty") or 0),
                    "unit": p.get("unit") or "",
                    "amount": float(p.get("amount") or 0),
                }
            )
    return list(events.values())


def build_parts(base_filter):
    """base_filter: ตัวกรองแบบเดียวกับ dashboard (มีปี) ใช้กับ SummaryMaintenance

    job_count/jobs_with_parts นับเฉพาะใบแจ้งซ่อม (ความครบของข้อมูล)
    นับเฉพาะรายการที่ stktyp เป็นอะไหล่/พัสดุ (PART_TYPES)
    doc_count/doc_amount = ส่วนที่มาจากใบจ่ายอะไหล่ของรถที่ไม่มีใบแจ้งซ่อม
    """
    jobs = SummaryMaintenance.objects.filter(**base_filter)
    rows = list(
        SummaryMaintenancePart.objects.filter(
            ext_id__in=jobs.values("ext_id"), stktyp__in=PART_TYPES
        ).values(*FIELDS)
    )
    docs = doc_jobs(base_filter)
    doc_rows = [p for d in docs for p in d["parts"]]

    ticket_amount = sum(float(r["amount"]) for r in rows)
    doc_amount = sum(p["amount"] for p in doc_rows)
    amount = ticket_amount + doc_amount
    jobs_with_parts = len({r["ext_id"] for r in rows})
    repairs = jobs_with_parts + len(docs)

    return {
        "job_count": jobs.count(),
        "jobs_with_parts": jobs_with_parts,
        "doc_count": len(docs),
        "doc_amount": doc_amount,
        "amount": amount,
        "amount_per_job": amount / repairs if repairs else None,
        "top": _top_parts(rows + doc_rows),
    }


def doc_job_list(base_filter):
    """การซ่อมจากใบจ่ายอะไหล่ (รถที่ไม่มีใบแจ้งซ่อม) พร้อมอะไหล่ ใหม่ -> เก่า สำหรับหน้าประวัติรถ"""
    return [
        {
            "ref_no": ", ".join(d["docnums"]),
            "docdat": d["docdat"],
            "is_pm": d["is_pm"],
            "amount": sum(p["amount"] for p in d["parts"]),
            "parts": [{k: v for k, v in p.items() if k != "ext_id"} for p in d["parts"]],
        }
        for d in reversed(doc_jobs(base_filter))
    ]
