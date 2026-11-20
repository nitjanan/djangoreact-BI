from datetime import date, datetime

import pytest

from dbapp.models import (
    BaseBranchCompany,
    BaseCar,
    BaseCarDepartment,
    SummaryMaintenance,
    SummaryMaintenancePart,
    SummaryRepairDoc,
)
from dbapp.services import sync
from dbapp.services.open_jobs import build_open_jobs
from dbapp.services.parts import build_parts, doc_job_list

FILTER = {"car_dep_id": 1, "branch_company_id__in": ["01"]}


@pytest.fixture
def setup(db):
    co = BaseBranchCompany.objects.create(id="01", code="C01", name="สาขา 1")
    dep = BaseCarDepartment.objects.create(id=1, name="แผนกรถ")
    car = BaseCar.objects.create(id=1, code="CAR1", name="รถ 1", car_dep=dep)

    def job(ext_id, finished_at=None, ref_no="MR1"):
        return SummaryMaintenance.objects.create(
            ext_id=ext_id,
            ref_no=ref_no,
            branch_company=co,
            car=car,
            car_dep=dep,
            year=2026,
            month=10,
            reported_at=datetime(2026, 10, 1),
            finished_at=finished_at,
            broke_reason="ล้อระเบิด",
        )

    def part(ext_id, stkcod, amount, qty=1, name="", stktyp="อะไหล่"):
        SummaryMaintenancePart.objects.create(
            stktyp=stktyp,
            ext_id=ext_id,
            docnum="OU1",
            docdat=date(2026, 10, 3),
            stkcod=stkcod,
            name=name,
            qty=qty,
            unit="ตัว",
            amount=amount,
        )

    return {"job": job, "part": part}


def test_summary_counts_coverage_and_top_parts(setup):
    job, part = setup["job"], setup["part"]
    job(1, finished_at=datetime(2026, 10, 5))
    job(2, finished_at=datetime(2026, 10, 6))
    job(3)
    part(1, "TIRE", 4000, qty=2, name="ยาง")
    part(2, "TIRE", 2000, qty=1)
    part(2, "BOLT", 100, qty=8, name="น็อต", stktyp="พัสดุ")
    part(2, "LABOR", 900, stktyp="งานบริการ")  # ไม่ใช่อะไหล่/พัสดุ
    part(3, "ENGINE", 90000, name="เครื่องยนต์")  # แพงกว่าแต่ใช้ครั้งเดียว

    result = build_parts({**FILTER, "year": 2026})
    assert result["job_count"] == 3
    assert result["jobs_with_parts"] == 3
    assert result["amount"] == 96100
    # เรียงตามจำนวนครั้งที่ใช้ก่อน แล้วค่อยมูลค่า
    assert [t["stkcod"] for t in result["top"]] == ["TIRE", "ENGINE", "BOLT"]
    tire = result["top"][0]
    assert (tire["stkcod"], tire["name"], tire["qty"], tire["jobs"]) == ("TIRE", "ยาง", 3, 2)


def test_open_job_shows_parts_issued_so_far(setup):
    setup["job"](1)
    setup["part"](1, "TIRE", 4000)
    setup["part"](1, "BOLT", 100)

    [row] = build_open_jobs(FILTER, now=datetime(2026, 11, 19))["jobs"]
    assert row["parts_amount"] == 4100
    assert len(row["parts"]) == 2


MA = {
    "id": 7,
    "created": "2026-11-03T08:00:00",
    "chief_update": None,
    "mile": None,
    "ma_type": None,
    "car_state": None,
    "is_complete": None,
    "car_id": None,
    "car_dep": None,
    "branch_company": None,
}
PROCESS = {
    "id": 7,
    "ref_no": "MR1",
    "broke_reason": "",
    "approve_status": None,
    "approve_update": None,
    "requisitions": [],
}
PART = {
    "source": "IV",
    "docnum": "OU1",
    "docdat": "2026-11-04",
    "stkcod": "TIRE",
    "name": "ยาง",
    "stktyp": "อะไหล่",
    "qty": 2.0,
    "unit": "เส้น",
    "amount": 4000.0,
}


PO_PART = {**PART, "source": "PO", "received": False, "docnum": "S1", "stkcod": "BOLT"}


def run_sync(monkeypatch, settings, issued, purchased=()):
    settings.MAINTENANCE_API_BASE = "http://webstock"
    process = [{**PROCESS, "parts": {"issued": issued, "purchased": list(purchased)}}]
    monkeypatch.setattr(
        sync, "get_api_data", lambda url, base_url=None: process if "/process/" in url else [MA]
    )
    sync.sync_maintenance(today=date(2026, 11, 19))


def stored():
    return sorted(SummaryMaintenancePart.objects.values_list("stkcod", flat=True))


def test_sync_stores_only_issued_parts(db, monkeypatch, settings):
    # ของที่ซื้อตาม PO จะรับเข้าคลังแล้วออกใบจ่ายสินค้าภายในอีกครั้ง เก็บ PO ด้วยจะนับซ้ำ
    SummaryMaintenancePart.objects.create(ext_id=7, docnum="OLD", stkcod="OLD", amount=1)
    run_sync(monkeypatch, settings, [PART], [PO_PART])
    assert stored() == ["TIRE"]


def test_sync_keeps_issued_parts_when_express_unreachable(db, monkeypatch, settings):
    SummaryMaintenancePart.objects.create(ext_id=7, docnum="OLD", stkcod="OLD", amount=1)
    run_sync(monkeypatch, settings, None, [PO_PART])
    assert stored() == ["OLD"]


def add_doc(docnum, day, car, parts, ma_ref=None, name=""):
    SummaryRepairDoc.objects.create(
        docnum=docnum, docdat=date(2026, 10, day), summary_date=date(2026, 10, 1), year=2026,
        month=10, ma_ref=ma_ref, repair_name=name, amount=sum(p["amount"] for p in parts),
        parts=parts, branch_company_id="01", car=car, car_dep_id=1,
    )  # fmt: skip


def line(stkcod, amount, name="", qty=1, stktyp="อะไหล่"):
    return {"stkcod": stkcod, "name": name, "stktyp": stktyp, "qty": qty, "unit": "ตัว",
            "amount": amount}  # fmt: skip


def test_cars_without_tickets_use_issue_doc_parts(setup):
    job, part = setup["job"], setup["part"]
    job(1, finished_at=datetime(2026, 10, 5))
    part(1, "TIRE", 4000, qty=2, name="ยาง")
    car1 = BaseCar.objects.get(id=1)
    add_doc("OU9", 4, car1, [line("TIRE", 999)])  # รถ 1 มีใบแจ้งซ่อม: ไม่นับซ้ำ
    car2 = BaseCar.objects.create(id=2, code="CAR2", name="รถ 2", car_dep_id=1)
    # รถ 2 ไม่มีใบแจ้งซ่อม: ใบจ่ายวันเดียวกัน = ซ่อม 1 ครั้ง
    add_doc("OU1", 3, car2, [
        line("TIRE", 1500, qty=1),
        line("BOLT", 50, "น็อต", qty=4, stktyp="พัสดุ"),
        line("LABOR", 800, "ค่าแรง", stktyp="งานบริการ"),  # ไม่ใช่อะไหล่/พัสดุ
    ])  # fmt: skip
    add_doc("OU2", 3, car2, [line("TIRE", 1500)])
    add_doc("OU3", 9, car2, [line("FILTER", 300, "ไส้กรอง")], name="PM")
    add_doc("OU4", 12, car2, [])  # ไม่มีรายการอะไหล่
    add_doc("OU5", 15, car2, [line("SV", 2000, stktyp="งานบริการ")])  # มีแต่ค่าบริการ ไม่นับ

    result = build_parts({**FILTER, "year": 2026})
    assert (result["job_count"], result["jobs_with_parts"]) == (1, 1)
    assert (result["doc_count"], result["doc_amount"]) == (2, 3350)
    assert result["amount"] == 7350
    assert result["amount_per_job"] == 7350 / 3
    tire = result["top"][0]
    assert (tire["stkcod"], tire["name"], tire["qty"], tire["amount"], tire["jobs"]) == (
        "TIRE", "ยาง", 4, 7000, 2,
    )  # fmt: skip

    jobs = doc_job_list({**FILTER, "car_id": 2})
    assert [(j["ref_no"], j["is_pm"], j["amount"], len(j["parts"])) for j in jobs] == [
        ("OU3", True, 300, 1),
        ("OU1, OU2", False, 3050, 3),  # ค่าแรง (งานบริการ) ไม่นับเป็นอะไหล่
    ]
