"""ขั้นที่ใบแจ้งซ่อมค้างอยู่ คำนวณจากเส้นทางเอกสารใน webstock (API maintenance/api/process)

ใบแจ้งซ่อม -> อนุมัติซ่อม -> ใบขอเบิก -> (จ่ายจากสต็อก | ใบขอซื้อ -> เปรียบเทียบราคา -> ใบสั่งซื้อ -> รับของ)

ใบแจ้งซ่อมหนึ่งใบมีได้หลายใบขอเบิก/หลาย PO งานจะเดินต่อได้เมื่อของมาครบ
จึงใช้ขั้นที่ช้าที่สุดของใบขอเบิกที่ยังไม่ได้ของ
"""

from datetime import date, datetime

from django.utils.dateparse import parse_date, parse_datetime

# เรียงตามลำดับงาน (ช้าสุด -> เร็วสุด)
STAGES = [
    ("approval", "รออนุมัติซ่อม"),
    ("approved", "อนุมัติแล้ว · ยังไม่ขอเบิก"),
    ("requisition", "ขอเบิกแล้ว · รอจ่ายของ/ขอซื้อ"),
    ("pr_approval", "รออนุมัติขอซื้อ"),
    ("purchasing", "กำลังจัดซื้อ"),
    ("waiting_parts", "รอของ"),
    ("parts_ready", "ได้ของแล้ว · รอปิดงาน"),
]
STAGE_LABELS = dict(STAGES)
STAGE_ORDER = {code: i for i, (code, _) in enumerate(STAGES)}

MA_WAITING_APPROVAL = "ขออนุมัติซ่อมบำรุง"
MA_APPROVED = "อนุมัติซ่อมบำรุง"

APPROVED = "approved"
DEAD = {"rejected", "not_proceed"}


def _dt(value):
    """'2026-11-12' หรือ '2026-11-12T10:48:11' -> datetime"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    parsed = parse_datetime(value)
    if parsed:
        return parsed.replace(tzinfo=None)
    d = parse_date(value)
    return datetime(d.year, d.month, d.day) if d else None


def _latest(*values):
    found = [v for v in (_dt(x) for x in values) if v]
    return max(found) if found else None


def requisition_stage(rq):
    """(stage, since, po_due, waiting_pos) ของใบขอเบิกหนึ่งใบ"""
    prs = [p for p in rq["purchase_requisitions"] if p["status"] not in DEAD]
    cps = [c for c in rq["comparisons"] if c["status"] not in DEAD]
    pos = [p for p in rq["purchase_orders"] if p["status"] not in DEAD]
    approved_pos = [p for p in pos if p["status"] == APPROVED]

    if approved_pos:
        waiting = [p for p in approved_pos if not p["is_receive"]]
        if waiting:
            dues = [d for d in (_dt(p["due_receive_update"]) for p in waiting) if d]
            since = _latest(*(p["approver_update"] or p["created"] for p in waiting))
            return "waiting_parts", since, min(dues) if dues else None, waiting
        since = _latest(*(p["receive_update"] for p in approved_pos))
        return "parts_ready", since, None, []

    if pos or cps or any(p["status"] == APPROVED for p in prs):
        since = _latest(
            *(p["created"] for p in pos),
            *(c["created"] for c in cps),
            *(p["approver_update"] for p in prs if p["status"] == APPROVED),
        )
        return "purchasing", since, None, []

    if prs:
        return "pr_approval", _latest(*(p["created"] for p in prs)), None, []

    if rq["invoices"]:
        # จ่ายจากสต็อกแล้ว ไม่ต้องซื้อ
        return "parts_ready", _latest(*(i["created"] for i in rq["invoices"])), None, []

    return "requisition", _dt(rq["created"]), None, []


def job_stage(process, reported_at):
    """ขั้นของใบแจ้งซ่อมที่ยังไม่ปิด

    คืน dict: stage, stage_since, po_due (วันกำหนดรับของที่เร็วที่สุด), documents (เลขที่เอกสารไว้แสดง)
    """
    documents = [{"type": "RQ", "ref_no": rq["ref_no"]} for rq in process["requisitions"]]

    if not process["requisitions"]:
        if process["approve_status"] == MA_APPROVED:
            stage, since = "approved", _dt(process["approve_update"]) or reported_at
        else:
            stage, since = "approval", reported_at
        return {"stage": stage, "stage_since": since, "po_due": None, "documents": documents}

    per_rq = [requisition_stage(rq) for rq in process["requisitions"]]
    stage = min((s for s, *_ in per_rq), key=STAGE_ORDER.__getitem__)
    since = _latest(*(s_since for s, s_since, *_ in per_rq if s == stage)) or reported_at
    dues = [due for s, _, due, _ in per_rq if s == stage and due]
    for _, _, _, waiting in per_rq:
        documents += [{"type": "PO", "ref_no": p["ref_no"]} for p in waiting]

    return {
        "stage": stage,
        "stage_since": since,
        "po_due": min(dues).date() if dues else None,
        "documents": documents,
    }
