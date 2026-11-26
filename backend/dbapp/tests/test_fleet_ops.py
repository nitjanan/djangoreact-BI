from datetime import date, datetime

import pytest

from dbapp.models import (
    BaseBranchCompany,
    BaseCar,
    BaseCarDepartment,
    SummaryMaintenance,
    SummaryOil,
    SummaryRepair,
    SummaryRepairDoc,
    SummaryWork,
)
from dbapp.services.downtime import build_downtime
from dbapp.services.fleet_usage import build_fuel_anomalies, build_low_use, car_months
from dbapp.services.part_prices import build_part_prices

NOW = datetime(2026, 11, 19, 12)
DEP = 3  # เครื่องจักร: ชั่วโมงจากหน้าปัด (SummaryWork)


@pytest.fixture
def co(db):
    BaseCarDepartment.objects.create(id=DEP, name="เครื่องจักร")
    return BaseBranchCompany.objects.create(id="01", code="C01", name="สาขา 1")


def make_car(i):
    return BaseCar.objects.create(id=i, code=f"CAR{i}", name=f"รถ {i}", car_dep_id=DEP)


def scope(months=range(1, 13)):
    return {
        "car_dep_id": DEP,
        "branch_company_id__in": ["01"],
        "year": 2026,
        "month__gte": months[0],
        "month__lte": months[-1],
    }


def usage(co, car, month, hours=0, liters=0):
    if hours:
        SummaryWork.objects.create(
            year=2026, month=month, count_diff_time=20, meter_hours=hours,
            branch_company=co, car_dep_id=DEP, car=car,
        )  # fmt: skip
    if liters:
        SummaryOil.objects.create(
            year=2026, month=month, sum_liter=liters, branch_company=co, car_dep_id=DEP, car=car
        )


# ------------------------------------------------------------ fuel anomalies


def test_fuel_spike_compares_car_with_its_own_months(co):
    thirsty = make_car(1)  # ใช้น้ำมันมากตลอด (ปกติของคันนี้) ไม่ถือว่าผิดปกติ
    spiky = make_car(2)
    for m in range(1, 6):
        usage(co, thirsty, m, hours=100, liters=3000)
        usage(co, spiky, m, hours=100, liters=1000 if m != 4 else 2000)

    months = range(1, 6)
    result = build_fuel_anomalies(car_months(scope(months)), months)

    assert [c["car_id"] for c in result["cars"]] == [2]
    car = result["cars"][0]
    assert car["baseline"] == 10
    assert [s["month"] for s in car["spikes"]] == [4]
    assert car["spikes"][0]["extra_liters"] == pytest.approx(1000)
    assert car["rates"][3] == 20


def test_fuel_spike_needs_enough_months_and_ignores_tiny_months(co):
    few = make_car(1)
    usage(co, few, 1, hours=100, liters=1000)
    usage(co, few, 2, hours=100, liters=3000)
    tiny = make_car(2)
    for m in range(1, 5):
        usage(co, tiny, m, hours=100, liters=1000)
    usage(co, tiny, 5, hours=2, liters=200)  # ชั่วโมงน้อยมาก อัตราแกว่ง ไม่นับ

    months = range(1, 6)
    assert build_fuel_anomalies(car_months(scope(months)), months)["cars"] == []


# ------------------------------------------------------------ low use


def test_low_use_flags_parked_and_low_hour_cars(co):
    for i in range(1, 6):
        car = make_car(i)
        for m in range(1, 5):
            usage(co, car, m, hours=200, liters=500)
    parked = make_car(6)
    usage(co, parked, 1, hours=200, liters=500)
    usage(co, parked, 2, liters=100)  # เติมน้ำมันแต่ไม่มีชั่วโมง = ยังใช้อยู่
    low = make_car(7)
    for m in range(1, 5):
        usage(co, low, m, hours=20, liters=50)
    fuel_only = make_car(8)  # ไม่บันทึกชั่วโมง ไม่เทียบชั่วโมง
    for m in range(1, 5):
        usage(co, fuel_only, m, liters=300)

    months = range(1, 5)
    result = build_low_use(car_months(scope(months)), months)

    by_id = {c["car_id"]: c for c in result["cars"]}
    assert set(by_id) == {6, 7}
    assert by_id[6]["idle"] and by_id[6]["idle_streak"] == 2
    assert by_id[7]["low_hours"] and not by_id[7]["idle"]
    assert result["median_hours"] == 200
    assert result["hours_car_count"] == 7
    assert result["cars"][0]["car_id"] == 6  # จอดนิ่งนานสุดก่อน


# ------------------------------------------------------------ downtime


def job(co, car, ext_id, reported_at, finished_at=None, ma_type="02"):
    SummaryMaintenance.objects.create(
        ext_id=ext_id, branch_company=co, car=car, car_dep_id=DEP,
        year=reported_at.year, month=reported_at.month,
        reported_at=reported_at, finished_at=finished_at, ma_type=ma_type,
    )  # fmt: skip


def test_downtime_clips_to_period_and_counts_cars_down_per_day(co):
    car1, car2 = make_car(1), make_car(2)
    # แจ้งก่อนช่วง ปิดในช่วง -> นับเฉพาะส่วนที่อยู่ในช่วง (1 มี.ค. 00:00 - 2 มี.ค. 00:00 = 24 ชม.)
    job(co, car1, 1, datetime(2026, 2, 27), datetime(2026, 3, 2))
    # ใบซ้อนกันของคันเดียวกันนับเวลาครั้งเดียว
    job(co, car2, 2, datetime(2026, 3, 1, 8), datetime(2026, 3, 1, 20))
    job(co, car2, 3, datetime(2026, 3, 1, 10), datetime(2026, 3, 1, 12))
    job(co, car2, 4, datetime(2026, 3, 5), ma_type="04")  # PM ไม่นับ

    result = build_downtime(scope(range(3, 4)), 2026, range(3, 4), now=NOW)

    hours = {c["car_id"]: c["hours"] for c in result["cars"]}
    assert hours == {1: pytest.approx(24), 2: pytest.approx(12)}
    assert result["daily"][:3] == [2, 0, 0]
    assert len(result["daily"]) == 31
    assert result["peak"] == 2
    assert result["peak_date"] == date(2026, 3, 1)


def test_downtime_open_ticket_runs_until_now(co):
    car = make_car(1)
    # ใบเปิดยังไม่มีประเภท (webstock ใส่ตอนปิดงาน) นับเป็นการเสีย · ใบ PM ที่เปิดอยู่ไม่นับ
    job(co, car, 1, datetime(2026, 11, 18, 12), ma_type=None)
    job(co, make_car(2), 2, datetime(2026, 11, 18, 12), ma_type="04")

    result = build_downtime(scope(range(11, 12)), 2026, range(11, 12), now=NOW)

    assert result["open_car_count"] == 1
    assert result["cars"][0]["hours"] == pytest.approx(24)
    assert result["cars"][0]["spans"][0]["open"] is True
    assert len(result["daily"]) == 19  # 1-19 พ.ย. (วันนี้ยังไม่จบ)


# ------------------------------------------------------------ part prices


def doc(co, docdat, *parts):
    SummaryRepairDoc.objects.create(
        docnum=f"D{docdat:%m%d}", docdat=docdat, summary_date=docdat.replace(day=1),
        year=docdat.year, month=docdat.month, amount=1, car_dep_id=DEP, branch_company=co,
        parts=[
            {"stkcod": code, "name": code, "qty": qty, "unit": "ชิ้น", "amount": amount,
             "stktyp": typ}
            for code, qty, amount, typ in parts
        ],
    )  # fmt: skip


def test_part_price_change_uses_edge_medians_and_skips_job_priced_items(co):
    for i, price in enumerate([100, 100, 100, 120, 120, 120]):
        doc(
            co,
            date(2026, i + 1, 10),
            ("FILTER", 2, price * 2, "อะไหล่"),
            ("LABOR", 1, [500, 5000, 800, 300, 9000, 1200][i], "อะไหล่"),  # ราคาตามงาน
            ("OIL", 1, 50, "น้ำมัน"),  # ไม่ใช่อะไหล่
        )

    months = range(4, 7)
    result = build_part_prices(scope(months), 2026, months)

    assert [r["stkcod"] for r in result["up"]] == ["FILTER"]
    row = result["up"][0]
    assert row["first_price"] == 100 and row["last_price"] == 120
    assert row["change"] == pytest.approx(20)
    assert row["period_qty"] == 6
    assert row["impact"] == pytest.approx(120)
    assert result["compared"] == 1


# ------------------------------------------------------------ replacement


def table_row(car_id, **values):
    """แถวตารางรถแบบปกติ: ต้นทุน 100 บาท/ชม. MTBF 500 ชม. หยุด 50 ชม."""
    row = {
        "car_id": car_id, "branch_company_id": "01", "branch_company_name": "สาขา 1",
        "code": f"CAR{car_id}", "name": f"รถ {car_id}", "brand": "", "car_model": "",
        "car_type_id": 1, "car_type_name": "รถขุด", "age": 3,
        "work_total": 1000.0, "repair_total": 100_000.0, "repair_cost_per_hr": 100.0,
        "failure_count": 2, "mtbf": 500.0, "downtime_hours": 50.0,
    }  # fmt: skip
    row.update(values)
    return row


def run_replacement(rows, months=range(1, 5)):
    from dbapp.services.replacement import build_replacement

    return build_replacement(rows, scope(months), months)


def test_replacement_needs_two_signals_including_old_or_costly(co):
    rows = [table_row(i) for i in range(1, 6)] + [
        table_row(6, age=12, repair_cost_per_hr=300.0, repair_total=300_000.0),  # เก่า + แพง
        table_row(7, age=15),  # เก่าอย่างเดียว
        table_row(
            8, failure_count=6, mtbf=100.0, downtime_hours=400.0
        ),  # เสียบ่อย+หยุดนาน แต่ใหม่และไม่แพง
        table_row(
            9, age=None, repair_cost_per_hr=200.0, failure_count=5, mtbf=150.0
        ),  # แพง + เสียบ่อย
    ]

    result = run_replacement(rows)

    by_id = {c["car_id"]: [s["code"] for s in c["signals"]] for c in result["cars"]}
    assert by_id == {6: ["old", "costly"], 9: ["costly", "failure"]}
    assert result["unknown_age_count"] == 1


def test_replacement_rising_cost_uses_monthly_repairs(co):
    car = make_car(6)
    for m, amount in [(1, 10_000), (2, 10_000), (3, 40_000), (4, 40_000)]:
        SummaryRepair.objects.create(
            year=2026, month=m, amount=amount, branch_company=co, car_dep_id=DEP, car=car
        )
    rows = [table_row(i) for i in range(1, 6)] + [table_row(6, age=11)]

    result = run_replacement(rows)

    car = result["cars"][0]
    assert [s["code"] for s in car["signals"]] == ["old", "rising"]
    assert car["trend"] == 4
    assert car["annual_repair"] == pytest.approx(300_000)  # 100,000 ใน 4 เดือน x 12 / 4
    assert car["monthly"] == [10_000, 10_000, 40_000, 40_000]


# ------------------------------------------------------------ forecast


def test_forecast_uses_recent_full_months():
    from dbapp.services.forecast import build_forecast

    repair = {1: 100.0, 2: 500.0, 3: 200.0, 4: 300.0, 5: 400.0, 6: 50.0}
    today = date(2026, 6, 20)

    result = build_forecast(repair, {}, 2026, range(1, 7), today)

    assert result["repair"]["expected"] == 300  # เม.ย.-มิ.ย.ไม่นับ: (200+300+400)/3
    assert (result["repair"]["low"], result["repair"]["high"]) == (100, 500)
    assert result["repair"]["month_to_date"] == 50
    assert result["current_label"] == "มิถุนายน" and result["next_label"] == "กรกฎาคม"
    # ดูปีก่อน หรือไม่ได้ดูถึงเดือนปัจจุบัน -> ไม่คาดการณ์
    assert build_forecast(repair, {}, 2025, range(1, 13), today) is None
    assert build_forecast(repair, {}, 2026, range(1, 5), today) is None
    assert build_forecast(repair, {}, 2026, range(1, 3), date(2026, 2, 10)) is None
