"""กฎสรุปและข้อสังเกตอัตโนมัติ (dbapp/services/insights.py) — ไม่ใช้ฐานข้อมูล"""

from dbapp.services.insights import FUEL_PER_KM, build_insights

MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน"]


def car(i, repair=10_000.0, work=100.0, oil=500.0, failures=0, mttr=None, company="01", km=0.0):
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
        "km_total": km,
        "liter_per_km": oil / km if km > 0 else 0.0,
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
    facts = {f["label"]: f for f in result["overview"]}
    assert (facts["ค่าซ่อมรวม"]["value"], facts["ค่าซ่อมรวม"]["note"]) == (
        "1.00 ล้านบาท",
        "จากรถ 11 คัน",
    )
    pareto = facts["ค่าซ่อมส่วนใหญ่มาจาก"]
    assert pareto["value"].endswith("จาก 11 คัน")
    assert pareto["note"] == "รถกลุ่มนี้ใช้ค่าซ่อมรวมกัน 80%"
    assert 0 < pareto["share"] < 100
    top_type = facts["ซ่อมอะไรมากที่สุด"]
    assert (top_type["value"], top_type["note"]) == ("ซ่อมเครื่องยนต์", "100% ของค่าซ่อมทั้งหมด")
    assert facts["เดือนที่จ่ายมากที่สุด"]["value"] == "มกราคม"


def test_car_in_top_repair_and_top_failures_is_urgent():
    rows = [car(1, repair=500_000, failures=9, mttr=40.0)] + [
        car(i, repair=10_000 * i, failures=1) for i in range(2, 8)
    ]
    result = build_insights(dashboard(rows))
    urgent = [i for i in result["items"] if i["title"].endswith("เสียบ่อยและซ่อมแพง")]
    assert len(urgent) == 1
    assert urgent[0]["severity"] == "high"
    assert urgent[0]["target"] == {"car_id": 1, "branch_company_id": "01"}
    assert urgent[0]["points"][0] == "เสีย 9 ครั้ง"
    assert "ซ่อมนานเฉลี่ย 40 ชม./ครั้ง" in urgent[0]["points"]
    assert urgent[0]["hint"]


def test_texts_use_selected_department_name():
    # คำว่า "รถ" ในข้อความแทนด้วยชื่อแผนกที่เลือก
    rows = [car(1, repair=200_000, work=100)] + [car(i, repair=10_000) for i in range(2, 8)]
    result = build_insights(dashboard(rows), noun="เครื่องจักรกลหนัก")
    item = next(i for i in result["items"] if "ค่าซ่อมแพงเกินงานที่ทำ" in i["title"])
    assert item["title"] == "เครื่องจักรกลหนัก 1 คันค่าซ่อมแพงเกินงานที่ทำ"
    assert item["compare"]["baseline_label"] == "เครื่องจักรกลหนักส่วนใหญ่"
    assert result["overview"][0]["note"] == "จากเครื่องจักรกลหนัก 7 คัน"


def test_cost_per_hour_outlier_uses_median_of_same_filter():
    # ค่ากลาง 100 บาท/ชม. คันที่ 1 = 2,000 บาท/ชม. (20 เท่า)
    rows = [car(1, repair=200_000, work=100)] + [car(i, repair=10_000) for i in range(2, 8)]
    result = build_insights(dashboard(rows))
    item = next(i for i in result["items"] if "ค่าซ่อมแพงเกินงานที่ทำ" in i["title"])
    assert item["title"] == "รถ 1 คันค่าซ่อมแพงเกินงานที่ทำ"
    assert item["target"]["car_id"] == 1
    assert "20.0 เท่า" in item["detail"]
    assert (item["compare"]["value"], item["compare"]["baseline"]) == (2000, 100)
    assert item["compare"]["baseline_label"] == "รถส่วนใหญ่"
    [entry] = item["cars"]
    assert entry["target"] == {"car_id": 1, "branch_company_id": "01"}
    assert entry["value"] == "2,000 บาท/ชม. · 20.0 เท่า"
    assert "ค่ากลาง" not in item["detail"]


def test_no_comparison_with_too_few_cars():
    rows = [car(1, repair=200_000), car(2), car(3)]
    result = build_insights(dashboard(rows))
    assert not any(i["kind"] in ("urgent", "efficiency") for i in result["items"])


def test_month_spike_names_the_causing_cars():
    data = dashboard([car(i) for i in range(1, 7)], monthly=(100, 100, 100, 100, 100, 1_000))
    data["charts"]["repair_heatmap"]["rows"] = [
        {
            "name": "รถ1:C1",
            "company": "",
            "car_id": 1,
            "branch_company_id": "01",
            "data": [0, 0, 0, 0, 0, 900],
        },
    ]
    result = build_insights(data)
    spike = next(i for i in result["items"] if i["kind"] == "anomaly")
    assert spike["title"] == "เดือนมิถุนายนจ่ายค่าซ่อมมากกว่าปกติ"
    assert "รถ1 (C1) 900 บาท" in spike["detail"]
    assert spike["cars"][0]["target"] == {"car_id": 1, "branch_company_id": "01"}
    assert spike["compare"]["value_label"] == "เดือนมิถุนายน"


def test_fuel_hungry_cars():
    rows = [car(1, oil=2_000)] + [car(i) for i in range(2, 8)]
    result = build_insights(dashboard(rows))
    item = next(i for i in result["items"] if i["kind"] == "efficiency")
    assert item["title"] == "รถ 1 คันใช้น้ำมันมากกว่าคันอื่น"
    assert [c["target"]["car_id"] for c in item["cars"]] == [1]


def test_trend_excludes_partial_month_and_flags_improvement():
    data = dashboard(
        [car(i) for i in range(1, 7)],
        failures=(10, 10, 10, 5, 5, 5),
        mttr=(100.0, 100.0, 100.0, 50.0, 50.0, 0.0),
    )
    result = build_insights(data, partial_last_month=False)
    assert ("trend", "good") in kinds(result)
    trend = next(i for i in result["items"] if i["title"] == "จำนวนครั้งที่เสียลดลง 50% ช่วงหลัง")
    assert trend["compare"]["value_label"] == "3 เดือนล่าสุด (เมษายน–มิถุนายน)"
    assert trend["compare"]["baseline_label"] == "ก่อนหน้านั้น (มกราคม–มีนาคม)"

    # เดือนสุดท้ายยังไม่จบ -> ตัดออก เหลือ 5 เดือน: ก่อนหน้า 2 เดือน ล่าสุด 3 เดือน
    result = build_insights(data, partial_last_month=True)
    assert "จำนวนครั้งที่เสียลดลง 33% ช่วงหลัง" in [i["title"] for i in result["items"]]


def test_data_quality_lists_problems():
    rows = [car(1, work=-500), car(2, work=0, oil=300)]
    result = build_insights(dashboard(rows), unmatched_total=1_500_000, no_dep_cars=4)
    item = next(i for i in result["items"] if i["kind"] == "data")
    assert item["severity"] == "info"
    assert item["points"] == [
        "ค่าซ่อม 1.50 ล้านบาท ยังไม่รู้ว่าเป็นของรถ/เครื่องจักรคันไหน (ดูรายการในแท็บอื่นๆ)",
        "1 คันชั่วโมงทำงานติดลบ (เลขไมล์ในบันทึกการใช้รถคีย์ผิด)",
        "1 คันเติมน้ำมันแต่ไม่มีบันทึกชั่วโมงทำงาน",
        "4 คันยังไม่ได้กำหนดแผนกใน webstock",
    ]
    assert item["target"]["car_id"] == 1
    assert item["action"] == "ดูคันที่ชั่วโมงติดลบ"
    # ข้อมูลเตือนอยู่ท้ายสุด
    assert result["items"][-1] is item


def test_selected_car_is_compared_with_fleet():
    rows = [car(1, repair=50_000, failures=3, mttr=12.0)] + [car(i) for i in range(2, 8)]
    data = dashboard(rows)
    data["selected_car"] = rows[0]
    result = build_insights(data)
    facts = {f["label"]: f for f in result["overview"]}
    assert (facts["ค่าซ่อมรวม"]["value"], facts["ค่าซ่อมรวม"]["note"]) == (
        "50,000 บาท",
        "มากเป็นอันดับ 1 จาก 7 คัน",
    )
    cost = facts["ค่าซ่อมต่อชั่วโมงทำงาน"]
    assert cost["value"] == "500 บาท"
    assert cost["note"] == "สูงกว่ารถส่วนใหญ่ 5.0 เท่า (100 บาท)"
    assert cost["tone"] == "bad"
    assert (facts["เสีย"]["value"], facts["เสีย"]["note"]) == ("3 ครั้ง", "ซ่อมนานเฉลี่ย 12 ชม./ครั้ง")


def test_empty_filter():
    result = build_insights(dashboard([], monthly=(0,) * 6))
    assert result["items"] == []
    [only] = result["overview"]
    assert only["note"] == "ยังไม่มีค่าซ่อมในตัวกรองนี้"


def test_fuel_per_km_for_trucks():
    # รถบรรทุก: ค่ากลาง 0.5 ลิตร/กม. คันที่ 1 = 2 ลิตร/กม.
    rows = [car(1, oil=2_000, km=1_000)] + [car(i, oil=500, km=1_000) for i in range(2, 8)]
    result = build_insights(dashboard(rows), noun="รถบรรทุก", fuel=FUEL_PER_KM)
    item = next(i for i in result["items"] if "ใช้น้ำมันมากกว่า" in i["title"])
    assert item["title"] == "รถบรรทุก 1 คันใช้น้ำมันมากกว่าคันอื่น"
    assert item["detail"].startswith("วิ่ง 1 กม.ใช้น้ำมัน 2.00 ลิตร")
    assert item["compare"]["value_text"] == "2.00 ลิตร/กม."
    assert item["compare"]["baseline_text"] == "0.50 ลิตร/กม."
