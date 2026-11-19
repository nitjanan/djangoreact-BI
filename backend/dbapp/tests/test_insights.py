"""กฎสรุปและข้อสังเกตอัตโนมัติ (dbapp/services/insights.py) — ไม่ใช้ฐานข้อมูล"""

from dbapp.services.insights import build_insights

MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน"]


def car(i, repair=10_000.0, work=100.0, oil=500.0, failures=0, mttr=None, company="01"):
    return {
        "car_id": i,
        "branch_company_id": company,
        "branch_company_name": f"บริษัท{company}",
        "code": f"C{i}",
        "name": f"รถ{i}",
        "percent_ma": 0.0,
        "avg_work_per_day": 0.0,
        "work_total": work,
        "oil_total": oil,
        "fuel_rate": oil / work if work > 0 else 0.0,
        "repair_total": repair,
        "repair_cost_per_hr": repair / work if work > 0 else 0.0,
        "failure_count": failures,
        "mtbf": None,
        "mttr": mttr,
    }


def dashboard(
    rows,
    monthly=(100.0, 100.0, 100.0, 100.0, 100.0, 100.0),
    failures=(0,) * 6,
    mttr=(None,) * 6,
):
    ranked = sorted(rows, key=lambda r: -r["repair_total"])
    total = sum(r["repair_total"] for r in rows)
    return {
        "selected_car": None,
        "car_table": {"rows": rows, "totals": {}},
        "charts": {
            "repair_by_month": {"labels": MONTHS, "series": list(monthly)},
            "repair_by_type": {"labels": ["ซ่อมเครื่องยนต์"], "series": [total], "total": total},
            "repair_by_car": {
                "labels": [r["name"] for r in ranked],
                "companies": [r["branch_company_name"] for r in ranked],
                "series": [r["repair_total"] for r in ranked],
                "total": total,
            },
            "repair_heatmap": {"labels": MONTHS, "rows": []},
            "repair_vs_work": {"labels": MONTHS, "repair": list(monthly), "work": [0] * 6},
        },
        "reliability": {"trend": {"labels": MONTHS, "count": list(failures), "mttr": list(mttr)}},
    }


def kinds(result):
    return [(i["kind"], i["severity"]) for i in result["items"]]


def test_overview_reports_total_pareto_and_top_type():
    rows = [car(1, repair=800_000)] + [car(i, repair=20_000) for i in range(2, 12)]
    monthly = (200_000, 200_000, 200_000, 100_000, 100_000, 200_000)
    result = build_insights(dashboard(rows, monthly=monthly))
    text = " ".join(result["overview"])
    assert "ค่าซ่อมรวม 1.00 ล้านบาท จากรถ 11 คัน" in text
    assert "ใช้ค่าซ่อมรวมกัน 80%" in text
    assert "ประเภทซ่อมเครื่องยนต์เป็นสัดส่วนสูงสุด (100%)" in text


def test_car_in_top_repair_and_top_failures_is_urgent():
    rows = [car(1, repair=500_000, failures=9, mttr=40.0)] + [
        car(i, repair=10_000 * i, failures=1) for i in range(2, 8)
    ]
    result = build_insights(dashboard(rows))
    urgent = [i for i in result["items"] if i["title"].endswith("เสียบ่อยและซ่อมแพง")]
    assert len(urgent) == 1
    assert urgent[0]["severity"] == "high"
    assert urgent[0]["target"] == {"car_id": 1, "branch_company_id": "01"}
    assert "เสีย 9 ครั้ง" in urgent[0]["detail"]


def test_cost_per_hour_outlier_uses_median_of_same_filter():
    # ค่ากลาง 100 บาท/ชม. คันที่ 1 = 2,000 บาท/ชม. (20 เท่า)
    rows = [car(1, repair=200_000, work=100)] + [car(i, repair=10_000) for i in range(2, 8)]
    result = build_insights(dashboard(rows))
    item = next(i for i in result["items"] if "ซ่อมแพงเมื่อเทียบกับงานที่ทำ" in i["title"])
    assert item["target"]["car_id"] == 1
    assert "20.0 เท่า" in item["detail"]


def test_no_comparison_with_too_few_cars():
    rows = [car(1, repair=200_000), car(2), car(3)]
    result = build_insights(dashboard(rows))
    assert not any(i["kind"] in ("urgent", "efficiency") for i in result["items"])


def test_month_spike_names_the_causing_cars():
    data = dashboard([car(i) for i in range(1, 7)], monthly=(100, 100, 100, 100, 100, 1_000))
    data["charts"]["repair_heatmap"]["rows"] = [
        {"name": "รถ1:C1", "company": "", "data": [0, 0, 0, 0, 0, 900]},
    ]
    result = build_insights(data)
    spike = next(i for i in result["items"] if i["kind"] == "anomaly")
    assert spike["title"] == "ค่าซ่อมเดือนมิถุนายนสูงผิดปกติ"
    assert "รถ1 (C1) 900 บาท" in spike["detail"]


def test_fuel_hungry_cars():
    rows = [car(1, oil=2_000)] + [car(i) for i in range(2, 8)]
    result = build_insights(dashboard(rows))
    item = next(i for i in result["items"] if i["kind"] == "efficiency")
    assert item["title"] == "รถ 1 คันใช้น้ำมันสูงผิดปกติ"


def test_trend_excludes_partial_month_and_flags_improvement():
    data = dashboard(
        [car(i) for i in range(1, 7)],
        failures=(10, 10, 10, 5, 5, 5),
        mttr=(100.0, 100.0, 100.0, 50.0, 50.0, 0.0),
    )
    result = build_insights(data, partial_last_month=False)
    assert ("trend", "good") in kinds(result)
    titles = [i["title"] for i in result["items"]]
    assert "จำนวนครั้งที่เสียลดลง 50%" in titles

    # เดือนสุดท้ายยังไม่จบ -> ตัดออก เหลือ 5 เดือน: ก่อนหน้า 2 เดือน ล่าสุด 3 เดือน
    result = build_insights(data, partial_last_month=True)
    assert "จำนวนครั้งที่เสียลดลง 33%" in [i["title"] for i in result["items"]]


def test_data_quality_lists_problems():
    rows = [car(1, work=-500), car(2, work=0, oil=300)]
    result = build_insights(dashboard(rows), unmatched_total=1_500_000, no_dep_cars=4)
    item = next(i for i in result["items"] if i["kind"] == "data")
    assert item["severity"] == "info"
    assert "ค่าซ่อม 1.50 ล้านบาท ยังจับคู่กับรถไม่ได้" in item["detail"]
    assert "ชั่วโมงทำงานติดลบ 1 คัน" in item["detail"]
    assert "เติมน้ำมันแต่ไม่มีชั่วโมงทำงาน 1 คัน" in item["detail"]
    assert "รถยังไม่ได้ตั้งแผนก 4 คัน" in item["detail"]
    assert item["target"]["car_id"] == 1
    assert item["action"] == "ดูคันที่ชั่วโมงติดลบ"
    # ข้อมูลเตือนอยู่ท้ายสุด
    assert result["items"][-1] is item


def test_selected_car_is_compared_with_fleet():
    rows = [car(1, repair=50_000, failures=3, mttr=12.0)] + [car(i) for i in range(2, 8)]
    data = dashboard(rows)
    data["selected_car"] = rows[0]
    result = build_insights(data)
    text = " ".join(result["overview"])
    assert "รถ1 (C1) ค่าซ่อม 50,000 บาท อันดับ 1 จาก 7 คัน" in text
    assert "ต้นทุนซ่อม 500.00 บาท/ชม. สูงกว่าค่ากลาง (100.00) 5.0 เท่า" in text
    assert "เสีย 3 ครั้ง เวลาซ่อมเฉลี่ย 12 ชม./ครั้ง" in text


def test_empty_filter():
    result = build_insights(dashboard([], monthly=(0,) * 6))
    assert result == {"overview": ["ยังไม่มีค่าซ่อมในตัวกรองนี้"], "items": []}
