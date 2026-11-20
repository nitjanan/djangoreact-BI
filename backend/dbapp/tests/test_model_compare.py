from dbapp.services.dashboard import car_age
from dbapp.services.insights import FUEL_PER_HOUR, FUEL_PER_KM
from dbapp.services.model_compare import build_model_benchmark, build_model_comparison


def row(car_id, brand, model, *, car_type=1, work=100.0, repair=1000.0, age=None, **extra):
    return {
        "car_id": car_id,
        "branch_company_id": "01",
        "car_type_id": car_type,
        "car_type_name": {1: "รถขุด", 2: "รถตัก", None: None}[car_type],
        "brand": brand,
        "car_model": model,
        "age": age,
        "work_total": work,
        "repair_total": repair,
        "oil_total": extra.get("oil", 0.0),
        "km_total": extra.get("km", 0.0),
        "liter_per_km": extra.get("liter_per_km", 0.0),
        "failure_count": extra.get("failures", 0),
        "percent_ma": extra.get("percent_ma", 0.0),
    }


def test_car_age():
    assert car_age(2019, 2026) == 7
    assert car_age(2026, 2026) == 0
    assert car_age(None, 2026) is None
    assert car_age(2027, 2026) is None  # เริ่มใช้หลังปีที่ดู


def test_groups_by_type_brand_model_using_sums_not_mean_of_cars():
    result = build_model_comparison(
        [
            # SANY SY215C 2 คัน: 3000 บาท / 200 ชม. = 15 (ไม่ใช่เฉลี่ย 10 กับ 20)
            row(1, "SANY", "SY215C", work=100, repair=1000, age=4),
            row(2, " sany ", "sy215c", work=100, repair=2000, age=6),
            row(3, "KOMATSU", "PC200", work=100, repair=500),
            row(4, None, None, work=100, repair=4500),  # ไม่ได้กรอกยี่ห้อ
        ],
        FUEL_PER_HOUR,
    )
    assert result["total_cars"] == 4
    assert result["missing_cars"] == 1
    sany, komatsu = result["rows"][1], result["rows"][0]  # ต้นทุนต่ำขึ้นก่อน
    assert (komatsu["brand"], sany["brand"]) == ("KOMATSU", "SANY")
    assert sany["cars"] == 2
    assert sany["repair_cost_per_hr"] == 15
    assert sany["avg_age"] == 5
    # ทั้งชนิดรถ (รวมคันไม่มียี่ห้อ) = 8000 / 400 = 20
    assert sany["type_repair_cost_per_hr"] == 20
    assert sany["vs_type"] == 0.75


def test_compares_only_within_car_type():
    result = build_model_comparison(
        [
            row(1, "CAT", "320", car_type=1, repair=1000),
            row(2, "CAT", "950", car_type=2, repair=3000),
            row(3, "CAT", "320", car_type=None, repair=100),
        ],
        FUEL_PER_HOUR,
    )
    assert [(r["car_type_name"], r["car_model"]) for r in result["rows"]] == [
        ("รถขุด", "320"),
        ("รถตัก", "950"),
        ("ไม่ระบุชนิด", "320"),
    ]
    assert all(r["vs_type"] == 1 for r in result["rows"])


def test_fuel_and_reliability_per_model():
    result = build_model_comparison(
        [
            row(1, "HINO", "500", work=0, repair=0, km=1000, liter_per_km=0.3, failures=1),
            row(2, "HINO", "500", work=0, repair=0, km=3000, liter_per_km=0.2),
        ],
        FUEL_PER_KM,
    )
    [hino] = result["rows"]
    assert hino["fuel"] == (300 + 600) / 4000
    assert hino["repair_cost_per_hr"] is None
    assert hino["mtbf"] is None  # ไม่มีชั่วโมงทำงาน
    assert hino["failure_count"] == 1


def test_merges_spelling_variants_of_same_model():
    result = build_model_comparison(
        [
            row(1, "LGMG", "MS25"),
            row(2, "LGMG", "MS 25"),
            row(3, "(JUNJIN)", "JD800"),
            row(4, "JUN JIN", "JD 800"),
            row(5, "ISUZU", "D - Max"),
            row(6, "isuzu", "D-MAX"),
        ],
        FUEL_PER_HOUR,
    )
    assert [r["cars"] for r in result["rows"]] == [2, 2, 2]


def test_per_hour_values_skip_cars_with_negative_or_zero_hours():
    # C8: เลขมิเตอร์ถูกรีเซ็ต ชั่วโมงติดลบ ถ้านับรวม ทั้งชนิดจะได้ชั่วโมงติดลบ
    result = build_model_comparison(
        [
            row(1, "CAT", "320", work=100, repair=1000, oil=500),
            row(2, "CAT", "320", work=-400000, repair=9000, oil=100),
            row(3, "CAT", "320", work=0, repair=200),
        ],
        FUEL_PER_HOUR,
    )
    [cat] = result["rows"]
    assert cat["cars"] == 3
    assert cat["repair_total"] == 10200  # ยอดรวมยังนับทุกคัน
    assert cat["work_total"] == 100
    assert cat["repair_cost_per_hr"] == 10
    assert cat["fuel"] == 5
    assert cat["type_repair_cost_per_hr"] == 10


def test_benchmark_compares_selected_car_with_other_cars_of_same_model_and_type():
    rows = [
        row(1, "SANY", "SY215C", work=100, repair=3000, age=12),
        row(2, "sany", "SY 215C", work=100, repair=1000, age=4),
        row(3, "SANY", "SY215C", work=100, repair=2000, age=6),
        row(4, "CAT", "320", work=100, repair=500),
        row(5, "CAT", "950", car_type=2, work=100, repair=9000),
    ]
    b = build_model_benchmark(rows, rows[0], FUEL_PER_HOUR)
    assert (b["brand"], b["car_model"], b["car_type_name"]) == ("SANY", "SY215C", "รถขุด")
    assert b["car"]["repair_cost_per_hr"] == 30
    assert b["model"]["cars"] == 2  # ไม่รวมคันนี้
    assert b["model"]["repair_cost_per_hr"] == 15
    assert b["model"]["avg_age"] == 5
    assert b["type"]["cars"] == 3  # รถขุดคันอื่น ไม่รวมรถตัก
    assert b["type"]["repair_cost_per_hr"] == 3500 / 300


def test_benchmark_without_brand_or_peers():
    rows = [row(1, None, None), row(2, "CAT", "320"), row(3, "VOLVO", "EC210")]
    assert build_model_benchmark(rows, rows[0], FUEL_PER_HOUR) is None
    assert build_model_benchmark(rows, None, FUEL_PER_HOUR) is None
    b = build_model_benchmark(rows, rows[1], FUEL_PER_HOUR)
    assert b["model"] is None
    assert b["type"]["cars"] == 2
