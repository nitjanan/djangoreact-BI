from datetime import date, datetime

import pytest

from dbapp.models import (
    BaseBranchCompany,
    BaseCar,
    BaseCarDepartment,
    SummaryMaintenance,
    SummaryMaintenancePart,
)
from dbapp.services import sync
from dbapp.services.open_jobs import build_open_jobs
from dbapp.services.parts import build_parts

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

    def part(ext_id, stkcod, amount, qty=1, name=""):
        SummaryMaintenancePart.objects.create(
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
    job(3)  # ไม่มีข้อมูลอะไหล่
    part(1, "TIRE", 4000, qty=2, name="ยาง")
    part(2, "TIRE", 2000, qty=1)
    part(2, "BOLT", 100, qty=8, name="น็อต")

    result = build_parts({**FILTER, "year": 2026})
    assert result["job_count"] == 3
    assert result["jobs_with_parts"] == 2
    assert result["amount"] == 6100
    assert result["amount_per_job"] == 3050
    tire = result["top"][0]
    assert (tire["stkcod"], tire["name"], tire["qty"], tire["jobs"]) == ("TIRE", "ยาง", 3, 2)


def test_job_list_when_car_selected(setup):
    setup["job"](1, finished_at=datetime(2026, 10, 5))
    setup["part"](1, "TIRE", 4000)

    [row] = build_parts({**FILTER, "year": 2026}, with_jobs=True)["jobs"]
    assert row["ref_no"] == "MR1"
    assert row["closed"] is True
    assert row["amount"] == 4000
    assert [p["stkcod"] for p in row["parts"]] == ["TIRE"]


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
