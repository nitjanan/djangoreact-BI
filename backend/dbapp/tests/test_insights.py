"""กฎสรุปและข้อสังเกตอัตโนมัติ (dbapp/services/insights.py) — ไม่ใช้ฐานข้อมูล"""

from dbapp.services.insights import build_insights

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


def test_fleet_insights_leave_car_lists_to_watchlist():
    # ซ่อมแพงต่อชม./เสียบ่อย/กินน้ำมัน แสดงใน "รถที่ต้องจับตา" แล้ว ไม่ซ้ำในข้อสังเกต
    rows = [car(1, repair=500_000, work=100, oil=5_000, failures=9)] + [
        car(i, failures=1) for i in range(2, 8)
    ]
    result = build_insights(dashboard(rows), noun="เครื่องจักรกลหนัก")
    assert not any(i["kind"] in ("urgent", "efficiency") for i in result["items"])
    assert result["overview"][0]["note"] == "จากเครื่องจักรกลหนัก 7 คัน"


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
    assert spike["chart"] == "repair_by_month"


def test_worsening_trend_links_to_its_chart():
    data = dashboard(
        [car(i) for i in range(1, 7)],
        monthly=(100, 100, 100, 300, 300, 300),
        failures=(5, 5, 5, 10, 10, 10),
        mttr=(50.0, 50.0, 50.0, 100.0, 100.0, 100.0),
    )
    result = build_insights(data, partial_last_month=False)
    charts = {i["title"].split(" ")[0]: i["chart"] for i in result["items"] if i["kind"] == "trend"}
    assert charts == {
        "จำนวนครั้งที่เสียเพิ่มขึ้น": "reliability",
        "เวลาซ่อมเฉลี่ยเพิ่มขึ้น": "reliability",
        "ค่าซ่อมเพิ่มขึ้น": "repair_by_month",
    }


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
    # ดีขึ้น: ไม่มีสิ่งที่ต้องทำ จึงไม่มีลิงก์ไปกราฟ
    assert trend["chart"] is None

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
