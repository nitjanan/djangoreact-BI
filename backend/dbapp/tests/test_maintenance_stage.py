from datetime import date, datetime

from dbapp.services.maintenance_stage import job_stage

REPORTED = datetime(2026, 11, 1, 8)


def process(requisitions=(), approve_status="อนุมัติซ่อมบำรุง", approve_update=None):
    return {
        "approve_status": approve_status,
        "approve_update": approve_update,
        "requisitions": list(requisitions),
    }


def rq(ref="RQ-1", created="2026-11-02", invoices=(), prs=(), cps=(), pos=()):
    return {
        "ref_no": ref,
        "created": created,
        "invoices": list(invoices),
        "purchase_requisitions": list(prs),
        "comparisons": list(cps),
        "purchase_orders": list(pos),
    }


def pr(status="pending", created="2026-11-03", approver_update=None):
    return {"status": status, "created": created, "approver_update": approver_update}


def po(
    ref="PO-1",
    status="approved",
    is_receive=False,
    due=None,
    created="2026-11-05",
    approver_update="2026-11-06T09:00:00",
    receive_update=None,
):
    return {
        "ref_no": ref,
        "status": status,
        "is_receive": is_receive,
        "due_receive_update": due,
        "created": created,
        "approver_update": approver_update,
        "receive_update": receive_update,
    }


def test_waiting_for_repair_approval():
    result = job_stage(process(approve_status="ขออนุมัติซ่อมบำรุง"), REPORTED)
    assert result["stage"] == "approval"
    assert result["stage_since"] == REPORTED


def test_approved_without_requisition_counts_from_approval_time():
    result = job_stage(process(approve_update="2026-11-01T15:00:00"), REPORTED)
    assert result["stage"] == "approved"
    assert result["stage_since"] == datetime(2026, 11, 1, 15)


def test_requisition_waiting():
    result = job_stage(process([rq()]), REPORTED)
    assert result["stage"] == "requisition"
    assert result["documents"] == [{"type": "RQ", "ref_no": "RQ-1"}]


def test_issued_from_stock_is_parts_ready():
    invoice = {"ref_no": "IV-1", "created": "2026-11-04"}
    assert job_stage(process([rq(invoices=[invoice])]), REPORTED)["stage"] == "parts_ready"


def test_pr_pending_then_approved_moves_to_purchasing():
    assert job_stage(process([rq(prs=[pr()])]), REPORTED)["stage"] == "pr_approval"
    approved = pr(status="approved", approver_update="2026-11-04T10:00:00")
    assert job_stage(process([rq(prs=[approved])]), REPORTED)["stage"] == "purchasing"


def test_rejected_pr_is_ignored():
    result = job_stage(process([rq(prs=[pr(status="rejected")])]), REPORTED)
    assert result["stage"] == "requisition"


def test_po_waiting_for_parts_has_due_date_and_po_ref():
    result = job_stage(process([rq(pos=[po(due="2026-11-21")])]), REPORTED)
    assert result["stage"] == "waiting_parts"
    assert result["po_due"] == date(2026, 11, 21)
    assert result["stage_since"] == datetime(2026, 11, 6, 9)
    assert {"type": "PO", "ref_no": "PO-1"} in result["documents"]


def test_pending_po_is_still_purchasing():
    result = job_stage(process([rq(pos=[po(status="pending")])]), REPORTED)
    assert result["stage"] == "purchasing"


def test_received_is_parts_ready():
    received = po(is_receive=True, receive_update="2026-11-10")
    assert job_stage(process([rq(pos=[received])]), REPORTED)["stage"] == "parts_ready"


def test_slowest_requisition_wins():
    done = rq("RQ-1", pos=[po("PO-1", is_receive=True, receive_update="2026-11-10")])
    waiting = rq("RQ-2", prs=[pr()])
    assert job_stage(process([done, waiting]), REPORTED)["stage"] == "pr_approval"
