from datetime import date

import pytest

from dbapp.models import BaseBranchCompany, BaseCar, BaseCarDepartment, SummaryMaintenance
from dbapp.services import sync

TODAY = date(2026, 11, 19)

MA = {
    "id": 7,
    "created": "2026-11-03T08:00:00",
    "chief_update": None,
    "mile": 100,
    "ma_type": None,
    "car_state": "ไม่สามารถทำการเคลื่อนย้ายได้",
    "is_complete": None,
    "car_id": 1,
    "car_dep": 1,
    "branch_company": "01",
}

PROCESS = {
    "id": 7,
    "ref_no": "MS1",
    "broke_reason": "ล้อระเบิด",
    "approve_status": "ขออนุมัติซ่อมบำรุง",
    "approve_update": None,
    "requisitions": [],
}


@pytest.fixture
def base(db, settings):
    BaseBranchCompany.objects.create(id="01", code="C01", name="สาขา 1")
    dep = BaseCarDepartment.objects.create(id=1, name="แผนกรถ")
    BaseCar.objects.create(id=1, code="CAR1", name="รถ 1", car_dep=dep)
    settings.MAINTENANCE_API_BASE = "http://webstock"


def fake_api(monkeypatch, maintenance, process):
    def get(url, base_url=None):
        return process if "/process/" in url else maintenance

    monkeypatch.setattr(sync, "get_api_data", get)


def test_merges_process_into_open_job(base, monkeypatch):
    fake_api(monkeypatch, [MA], [PROCESS])
    assert sync.sync_maintenance(today=TODAY) is True

    row = SummaryMaintenance.objects.get(ext_id=7)
    assert row.ref_no == "MS1"
    assert row.broke_reason == "ล้อระเบิด"
    assert row.stage == "approval"


def test_closed_job_gets_no_stage(base, monkeypatch):
    fake_api(monkeypatch, [{**MA, "chief_update": "2026-11-04T08:00:00"}], [PROCESS])
    sync.sync_maintenance(today=TODAY)

    row = SummaryMaintenance.objects.get(ext_id=7)
    assert row.ref_no == "MS1"
    assert row.stage is None


def test_works_when_webstock_has_no_process_api(base, monkeypatch):
    fake_api(monkeypatch, [MA], [])
    assert sync.sync_maintenance(today=TODAY) is True
    assert SummaryMaintenance.objects.get(ext_id=7).stage is None
