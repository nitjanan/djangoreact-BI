from datetime import date, datetime

import pytest

from dbapp.models import BaseBranchCompany, BaseCar, BaseCarDepartment, SummaryMaintenance
from dbapp.services.open_jobs import IMMOBILE_STATE, build_open_jobs

NOW = datetime(2026, 11, 19, 12)
MOVABLE = "สามารถทำการเคลื่อนย้ายได้"


@pytest.fixture
def setup(db):
    co = BaseBranchCompany.objects.create(id="01", code="C01", name="สาขา 1")
    dep = BaseCarDepartment.objects.create(id=1, name="แผนกรถ")
    car1 = BaseCar.objects.create(id=1, code="CAR1", name="รถ 1", car_dep=dep)
    car2 = BaseCar.objects.create(id=2, code="CAR2", name="รถ 2", car_dep=dep)
    seq = iter(range(1, 100))

    def job(car, reported_at, finished_at=None, is_complete=None, state=MOVABLE, **extra):
        SummaryMaintenance.objects.create(
            ext_id=next(seq),
            branch_company=co,
            car=car,
            car_dep=dep,
            year=reported_at.year,
            month=reported_at.month,
            reported_at=reported_at,
            finished_at=finished_at,
            is_complete=is_complete,
            car_state=state,
            **extra,
        )

    return {"car1": car1, "car2": car2, "job": job}


def run():
    return build_open_jobs({"car_dep_id": 1, "branch_company_id__in": ["01"]}, now=NOW)


def test_counts_only_unclosed_jobs(setup):
    job = setup["job"]
    job(setup["car1"], datetime(2026, 11, 18, 8))  # เปิด
    job(setup["car1"], datetime(2026, 11, 1), finished_at=datetime(2026, 11, 2))  # ปิดแล้ว
    job(setup["car1"], datetime(2026, 11, 1), is_complete=True)  # เสร็จแต่ไม่มีเวลาปิด

    result = run()
    assert result["total"] == 1
    assert result["car_count"] == 1


def test_age_buckets_stale_and_oldest_first(setup):
    job = setup["job"]
    job(setup["car1"], datetime(2026, 11, 19, 8))  # 0 วัน
    job(setup["car1"], datetime(2026, 11, 17))  # 2 วัน
    job(setup["car1"], datetime(2026, 11, 13))  # 6 วัน
    job(setup["car1"], datetime(2026, 9, 1))  # 79 วัน
    job(setup["car1"], datetime(2569, 8, 1))  # ปี พ.ศ. -> 2026-08-01

    result = run()
    assert [b["count"] for b in result["buckets"]] == [1, 1, 1, 2]
    assert result["stale_count"] == 2
    days = [j["days"] for j in result["jobs"]]
    assert days[0] == (NOW - datetime(2026, 8, 1)).days
    assert days == sorted(days, reverse=True)


def test_immobile_cars_counted_once(setup):
    job = setup["job"]
    job(setup["car1"], datetime(2026, 11, 1), state=IMMOBILE_STATE)
    job(setup["car1"], datetime(2026, 11, 2), state=IMMOBILE_STATE)
    job(setup["car2"], datetime(2026, 11, 18))

    result = run()
    assert result["immobile_car_count"] == 1
    assert result["car_count"] == 2


def test_stage_counts_and_overdue_po(setup):
    job = setup["job"]
    job(
        setup["car1"],
        datetime(2026, 11, 1),
        stage="waiting_parts",
        stage_since=datetime(2026, 11, 10),
        po_due=date(2026, 11, 15),
        broke_reason="ล้อระเบิด",
        documents=[{"type": "PO", "ref_no": "PO-1"}],
    )
    job(setup["car2"], datetime(2026, 11, 18))  # ยังไม่มีข้อมูลเอกสาร

    result = run()
    assert result["has_process"] is True
    assert {s["code"]: s["count"] for s in result["stages"]} == {"waiting_parts": 1, "unknown": 1}
    waiting = result["jobs"][0]
    assert waiting["stage_label"] == "รอของ"
    assert waiting["stage_days"] == 9
    assert waiting["po_overdue"] is True
    assert waiting["broke_reason"] == "ล้อระเบิด"
    assert waiting["documents"] == [{"type": "PO", "ref_no": "PO-1"}]


def test_without_process_data(setup):
    setup["job"](setup["car1"], datetime(2026, 11, 18))
    assert run()["has_process"] is False
