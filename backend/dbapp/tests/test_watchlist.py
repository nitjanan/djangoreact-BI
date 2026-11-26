from datetime import datetime

import pytest

from dbapp.models import BaseBranchCompany, BaseCar, BaseCarDepartment, SummaryMaintenance
from dbapp.services.watchlist import REPEAT_DAYS, REPLACE_AGE, build_watchlist

NO_OPEN_JOBS = {"jobs": []}


def car(car_id, **values):
    """แถวตารางรถแบบปกติ: ต้นทุน 100 บาท/ชม. น้ำมัน 10 ลิตร/ชม. MTBF 500 ชม."""
    row = {
        "car_id": car_id,
        "branch_company_id": "01",
        "branch_company_name": "สาขา 1",
        "code": f"CAR{car_id}",
        "name": f"รถ {car_id}",
        "work_total": 1000.0,
        "repair_total": 100_000.0,
        "repair_cost_per_hr": 100.0,
        "oil_total": 10_000.0,
        "fuel_rate": 10.0,
        "failure_count": 2,
        "mtbf": 500.0,
        "car_type_id": 1,
        "car_type_name": "รถขุด",
        "age": None,
        "downtime_hours": 50.0,
        "brand": "",
        "car_model": "",
    }
    row.update(values)
    return row


def fleet(*special):
    """รถปกติ 5 คัน + คันที่กำหนดเอง (รถน้อยกว่า 5 คันจะไม่เทียบค่ากลาง)"""
    ids = {r["car_id"] for r in special}
    return [car(i) for i in range(1, 6) if i not in ids] + list(special)


def run(rows, open_jobs=NO_OPEN_JOBS):
    return build_watchlist(rows, {"car_dep_id": 1, "year": 2026}, open_jobs)


def codes(result):
    return {c["car_id"]: [r["code"] for r in c["reasons"]] for c in result["cars"]}


@pytest.mark.django_db
def test_normal_fleet_has_no_cars_to_watch():
    result = run(fleet())
    assert result["cars"] == []
    assert result["compared"] is True


@pytest.mark.django_db
def test_flags_costly_frequent_and_fuel_hungry_cars():
    result = run(
        fleet(
            car(6, repair_cost_per_hr=400.0, repair_total=400_000.0),
            car(7, failure_count=5, mtbf=200.0),
            car(8, fuel_rate=20.0),
            car(9, repair_cost_per_hr=400.0, repair_total=1_000.0),  # แพงต่อชม. แต่ยอดน้อย
            car(10, failure_count=1, mtbf=100.0),  # เสียครั้งเดียว ยังไม่นับ
        )
    )
    assert codes(result) == {6: ["cost"], 7: ["failure"], 8: ["fuel"]}
    counts = {r["code"]: r["count"] for r in result["reasons"]}
    assert counts == {
        "stale": 0,
        "cost": 1,
        "replace": 0,
        "repeat": 0,
        "failure": 1,
        "fuel": 1,
        "fuel_spike": 0,
        "low_use": 0,
    }


@pytest.mark.django_db
def test_fuel_spike_and_low_use_become_watch_reasons():
    spike = {"car_id": 2, "branch_company_id": "01", "extra_liters": 1_234.0}
    spike["spikes"] = [{"label": "มีนาคม", "ratio": 1.8}, {"label": "เมษายน", "ratio": 1.4}]
    parked = {"car_id": 3, "branch_company_id": "01", "idle": True, "idle_streak": 3}
    parked |= {"low_hours": False, "avg_hours": 0.0, "ratio": None}
    slow = {"car_id": 4, "branch_company_id": "01", "idle": False, "idle_streak": 0}
    slow |= {"low_hours": True, "avg_hours": 20.0, "ratio": 0.2}
    result = build_watchlist(
        fleet(),
        {"car_dep_id": 1, "year": 2026},
        NO_OPEN_JOBS,
        fuel_anomalies={"cars": [spike]},
        low_use={"cars": [parked, slow], "median_hours": 100.0},
    )
    assert codes(result) == {2: ["fuel_spike"], 3: ["low_use"], 4: ["low_use"]}
    reasons = {c["car_id"]: c["reasons"][0] for c in result["cars"]}
    assert (reasons[2]["value"], reasons[2]["note"]) == (
        "เกิน 1,234 ลิตร",
        "2 เดือน · สูงสุด มีนาคม 1.8 เท่าของปกติ",
    )
    assert reasons[3]["value"] == "จอด 3 เดือน"
    assert (reasons[4]["value"], reasons[4]["note"]) == ("20 ชม./เดือน", "20% ของรถส่วนใหญ่ (100 ชม.)")
    # จอดนิ่งเรียงก่อนชั่วโมงต่ำในตัวกรองใช้งานน้อย
    assert reasons[3]["sort"] > reasons[4]["sort"]


@pytest.mark.django_db
def test_too_few_cars_skips_median_rules():
    result = run([car(1, repair_cost_per_hr=10_000.0), car(2)])
    assert result["cars"] == []
    assert result["compared"] is False


@pytest.mark.django_db
def test_stale_open_job_and_sorting_by_reason_count():
    open_jobs = {
        "jobs": [
            {"car_id": 6, "branch_company_id": "01", "ref_no": "MR1", "days": 12, "immobile": True},
            {"car_id": 6, "branch_company_id": "01", "ref_no": "MR2", "days": 3, "immobile": False},
            {"car_id": 1, "branch_company_id": "01", "ref_no": "MR3", "days": 5, "immobile": False},
        ]
    }
    result = run(
        fleet(car(6, repair_cost_per_hr=400.0, repair_total=400_000.0), car(7, fuel_rate=20.0)),
        open_jobs,
    )
    assert [c["car_id"] for c in result["cars"]] == [6, 7]
    stale = result["cars"][0]["reasons"][-1]
    assert stale["code"] == "stale"
    assert stale["detail"] == "MR1 ค้าง 12 วัน · เคลื่อนย้ายไม่ได้"


def test_repeat_repairs_within_days(db):
    co = BaseBranchCompany.objects.create(id="01", code="C01", name="สาขา 1")
    dep = BaseCarDepartment.objects.create(id=1, name="แผนกรถ")
    seq = iter(range(1, 100))

    def job(car_id, reported_at, ma_type="02"):
        SummaryMaintenance.objects.create(
            ext_id=next(seq),
            branch_company=co,
            car=BaseCar.objects.get_or_create(id=car_id, defaults={"car_dep": dep})[0],
            car_dep=dep,
            year=2026,
            month=reported_at.month,
            reported_at=reported_at,
            ma_type=ma_type,
        )

    job(1, datetime(2026, 3, 1))
    job(1, datetime(2569, 3, 20))  # ปี พ.ศ. = 2026-03-20 ห่าง 19 วัน -> ซ้ำ
    job(2, datetime(2026, 3, 1))
    job(2, datetime(2026, 3, 1).replace(month=5))  # ห่างเกิน 30 วัน
    job(3, datetime(2026, 3, 1))
    job(3, datetime(2026, 3, 5), ma_type="01")  # ไม่ใช่ใบซ่อม

    result = run([car(1), car(2), car(3)])
    assert codes(result) == {1: ["repeat"]}
    detail = result["cars"][0]["reasons"][0]["detail"]
    assert detail == f"แจ้งซ่อมซ้ำภายใน {REPEAT_DAYS} วัน 1 ครั้ง (ห่างกันน้อยสุด 19 วัน)"
    reason = result["cars"][0]["reasons"][0]
    assert (reason["value"], reason["note"]) == ("1 ครั้ง", "ห่างกันน้อยสุด 19 วัน")


@pytest.mark.django_db
def test_old_car_costlier_than_its_car_type_is_replacement_candidate():
    result = run(
        fleet(
            car(6, age=REPLACE_AGE + 4, repair_cost_per_hr=200.0),
            car(7, age=REPLACE_AGE - 1, repair_cost_per_hr=200.0),  # ยังไม่เก่า
            car(8, age=REPLACE_AGE + 4, repair_cost_per_hr=120.0),  # เก่าแต่ซ่อมไม่แพง
            car(9, age=None, repair_cost_per_hr=200.0),  # ไม่รู้อายุ
        )
    )
    assert codes(result) == {6: ["replace"]}
    detail = result["cars"][0]["reasons"][0]["detail"]
    assert f"อายุ {REPLACE_AGE + 4} ปี" in detail
    assert "2.0 เท่าของรถขุดส่วนใหญ่" in detail
    assert result["cars"][0]["monthly"] == [0.0] * 12
    assert result["cars"][0]["age"] == REPLACE_AGE + 4
    replace = result["cars"][0]["replace"]
    assert [(s["code"], s["value"]) for s in replace["signals"]] == [
        ("old", f"{REPLACE_AGE + 4} ปี"),
        ("costly", "2.0 เท่าของรถขุด"),
    ]


@pytest.mark.django_db
def test_replacement_detail_skips_signals_that_have_their_own_badge():
    # เก่า + ซ่อมแพงมาก (ติดป้ายซ่อมแพงเทียบกับงานด้วย) -> ไม่เขียนต้นทุน/ชม. ซ้ำใน ควรพิจารณาเปลี่ยน
    result = run(
        fleet(car(6, age=REPLACE_AGE + 2, repair_cost_per_hr=400.0, repair_total=400_000.0))
    )

    reasons = {r["code"]: r["detail"] for r in result["cars"][0]["reasons"]}
    assert set(reasons) == {"cost", "replace"}
    assert "บาท/ชม." not in reasons["replace"]
    assert f"อายุ {REPLACE_AGE + 2} ปี" in reasons["replace"]
    assert "ร่วมกับซ่อมแพงเทียบกับงาน" in reasons["replace"]
    replace = result["cars"][0]["replace"]
    assert [s["code"] for s in replace["signals"]] == ["old"]
    assert replace["covered"] == ["ซ่อมแพงเทียบกับงาน"]


@pytest.mark.django_db
def test_replacement_compares_within_car_type_only():
    # รถตัก 5 คันต้นทุน 300 บาท/ชม. ทั้งหมด คันเก่าต้นทุน 400 ไม่ถึง 1.5 เท่าของรถตัก
    loaders = [car(20 + i, car_type_id=2, repair_cost_per_hr=300.0) for i in range(5)]
    result = run(fleet(*loaders, car(30, car_type_id=2, age=20, repair_cost_per_hr=400.0)))
    assert "replace" not in [r["code"] for c in result["cars"] for r in c["reasons"]]
