"""สรุปและข้อสังเกตอัตโนมัติของหน้า dashboard (คำนวณตามกฎ ไม่ใช้ AI)

ทำงานกับผลลัพธ์ของ build_dashboard() ที่คำนวณเสร็จแล้ว ไม่ query เพิ่ม
(ยกเว้นตัวเลขคุณภาพข้อมูลที่ส่งมาเป็น argument) จึงทดสอบได้โดยไม่ต้องมีฐานข้อมูล

เกณฑ์ทุกข้อเทียบกับรถในตัวกรองเดียวกัน (บริษัท/แผนก/ประเภทรถ) ใช้ "ค่ากลาง" (median)
แทนค่าเฉลี่ย เพื่อไม่ให้รถคันที่ค่าสูงผิดปกติดึงเกณฑ์ขึ้นไปเอง
"""

from statistics import mean, median, pstdev

# ระดับความสำคัญ เรียงจากสำคัญมากไปน้อย
HIGH = "high"
MEDIUM = "medium"
GOOD = "good"
INFO = "info"
SEVERITY_ORDER = {HIGH: 0, MEDIUM: 1, GOOD: 2, INFO: 3}

TOP_N = 10  # อันดับที่ถือว่า "สูง"
MAX_LISTED = 5  # จำนวนรถสูงสุดที่ระบุชื่อในข้อสังเกตเดียว
COST_PER_HR_FACTOR = 3  # ต้นทุนซ่อม/ชม. สูงกว่าค่ากลางกี่เท่าจึงผิดปกติ
FUEL_RATE_FACTOR = 1.5  # น้ำมัน/ชม. สูงกว่าค่ากลางกี่เท่าจึงผิดปกติ
MIN_CARS_TO_COMPARE = 5  # รถน้อยกว่านี้ ค่ากลางไม่น่าเชื่อถือ ไม่เทียบ
TREND_MONTHS = 3  # ช่วงล่าสุดที่ใช้ดูแนวโน้ม
TREND_CHANGE = 0.2  # เปลี่ยนเกิน 20% จึงรายงาน


# ---------------------------------------------------------------- format


def baht(value):
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.2f} ล้านบาท"
    return f"{value:,.0f} บาท"


def times(ratio):
    return f"{ratio:,.1f} เท่า"


def car_name(row, with_company=False):
    name = row.get("name") or ""
    code = row.get("code") or ""
    label = f"{name} ({code})" if name and code and name != code else (name or code or "ไม่ระบุ")
    if with_company and row.get("branch_company_name"):
        label += f" · {row['branch_company_name']}"
    return label


def car_target(row):
    return {"car_id": row["car_id"], "branch_company_id": str(row["branch_company_id"])}


def item(severity, kind, title, detail, target=None, action="ดูรถคันนี้"):
    return {
        "severity": severity,
        "kind": kind,
        "title": title,
        "detail": detail,
        "target": target,
        # ข้อความปุ่มไปดูรถ (ไม่มี target = ไม่มีปุ่ม)
        "action": action if target else None,
    }


def heat_name(label):
    """ชื่อจาก car_label() แบบ "ชื่อ:รหัส" -> "ชื่อ (รหัส)" """
    name, _, code = label.partition(":")
    return f"{name} ({code})" if code else name


def names(rows, with_company):
    listed = ", ".join(car_name(r, with_company) for r in rows[:MAX_LISTED])
    more = len(rows) - MAX_LISTED
    return listed + (f" และอีก {more} คัน" if more > 0 else "")


# ---------------------------------------------------------------- rules


def overview(data, with_company):
    """ย่อหน้าสรุปภาพรวม: ยอดรวม, Pareto 80%, ประเภทการซ่อมหลัก, เดือนสูงสุด"""
    charts = data["charts"]
    rows = data["car_table"]["rows"]
    lines = []

    months = charts["repair_by_month"]
    total = sum(months["series"])
    if total <= 0:
        return ["ยังไม่มีค่าซ่อมในตัวกรองนี้"]
    lines.append(f"ค่าซ่อมรวม {baht(total)} จากรถ {len(rows):,} คัน")

    by_car = charts["repair_by_car"]
    if by_car["total"] > 0 and len(by_car["series"]) >= MIN_CARS_TO_COMPARE:
        running, count = 0.0, 0
        for v in by_car["series"]:
            running += v
            count += 1
            if running >= by_car["total"] * 0.8:
                break
        share = count / len(by_car["series"]) * 100
        lines.append(
            f"รถ {count} จาก {len(by_car['series'])} คันที่มีค่าซ่อม ({share:.0f}%) ใช้ค่าซ่อมรวมกัน 80%"
        )

    by_type = charts["repair_by_type"]
    if by_type["total"] > 0 and by_type["series"]:
        share = by_type["series"][0] / by_type["total"] * 100
        lines.append(f"ประเภท{by_type['labels'][0]}เป็นสัดส่วนสูงสุด ({share:.0f}%)")

    values = [v for v in months["series"] if v > 0]
    if len(values) >= 2:
        top = max(range(len(months["series"])), key=lambda i: months["series"][i])
        avg = mean(values)
        diff = (months["series"][top] - avg) / avg * 100 if avg else 0
        lines.append(
            f"เดือน{months['labels'][top]}สูงสุด {baht(months['series'][top])}"
            + (f" สูงกว่าค่าเฉลี่ย {diff:.0f}%" if diff >= 10 else "")
        )
    return lines


def urgent_cars(rows, with_company):
    """รถที่ติดทั้ง 10 อันดับค่าซ่อมสูงสุด และ 10 อันดับเสียบ่อยที่สุด"""
    by_repair = sorted((r for r in rows if r["repair_total"] > 0), key=lambda r: -r["repair_total"])
    by_failure = sorted(
        (r for r in rows if r["failure_count"] >= 2), key=lambda r: -r["failure_count"]
    )
    top_failure = {(r["car_id"], r["branch_company_id"]) for r in by_failure[:TOP_N]}
    hits = [r for r in by_repair[:TOP_N] if (r["car_id"], r["branch_company_id"]) in top_failure]
    return [
        item(
            HIGH,
            "urgent",
            f"{car_name(r, with_company)} เสียบ่อยและซ่อมแพง",
            f"เสีย {r['failure_count']} ครั้ง ค่าซ่อม {baht(r['repair_total'])}"
            + (f" เวลาซ่อมเฉลี่ย {r['mttr']:,.0f} ชม./ครั้ง" if r.get("mttr") else ""),
            car_target(r),
        )
        for r in hits[:3]
    ]


def costly_per_hour(rows, with_company):
    """ทำงานแล้วแต่ต้นทุนซ่อมต่อชั่วโมงสูงกว่าค่ากลางหลายเท่า"""
    valid = [r for r in rows if r["work_total"] > 0 and r["repair_total"] > 0]
    if len(valid) < MIN_CARS_TO_COMPARE:
        return []
    mid = median(r["repair_cost_per_hr"] for r in valid)
    min_repair = median(r["repair_total"] for r in valid)
    hits = sorted(
        (
            r
            for r in valid
            if mid > 0
            and r["repair_cost_per_hr"] > mid * COST_PER_HR_FACTOR
            and r["repair_total"] >= min_repair
        ),
        key=lambda r: -r["repair_cost_per_hr"],
    )
    if not hits:
        return []
    worst = hits[0]
    return [
        item(
            HIGH,
            "urgent",
            f"รถ {len(hits)} คันซ่อมแพงเมื่อเทียบกับงานที่ทำ",
            f"ต้นทุนซ่อมต่อชั่วโมงเกิน {COST_PER_HR_FACTOR} เท่าของค่ากลาง ({mid:,.0f} บาท/ชม.): "
            f"{names(hits, with_company)} — สูงสุด {car_name(worst, with_company)} "
            f"{worst['repair_cost_per_hr']:,.0f} บาท/ชม. "
            f"({times(worst['repair_cost_per_hr'] / mid)})",
            car_target(worst),
            "ดูคันที่สูงที่สุด",
        )
    ]


def month_spikes(data, show_causes=True):
    """เดือนที่ค่าซ่อมสูงเกินช่วงปกติ (ค่าเฉลี่ย + 2 SD) พร้อมรถที่เป็นต้นเหตุ"""
    chart = data["charts"]["repair_vs_work"]
    values = chart["repair"]
    active = [v for v in values if v > 0]
    if len(active) < 4:
        return []
    avg, sd = mean(active), pstdev(active)
    limit = avg + 2 * sd
    heat = data["charts"]["repair_heatmap"]
    out = []
    for i, v in enumerate(values):
        if sd <= 0 or v <= limit:
            continue
        causes = sorted(
            (r for r in heat["rows"] if i < len(r["data"]) and r["data"][i] > 0),
            key=lambda r: -r["data"][i],
        )[:3]
        cause_text = (
            " ส่วนใหญ่มาจาก "
            + ", ".join(f"{heat_name(r['name'])} {baht(r['data'][i])}" for r in causes)
            if causes and show_causes
            else ""
        )
        out.append(
            item(
                MEDIUM,
                "anomaly",
                f"ค่าซ่อมเดือน{chart['labels'][i]}สูงผิดปกติ",
                f"{baht(v)} สูงกว่าค่าเฉลี่ย {(v - avg) / avg * 100:.0f}% (เฉลี่ย {baht(avg)}/เดือน)"
                + cause_text,
            )
        )
    return out[:2]


def fuel_hungry(rows, with_company):
    """น้ำมันต่อชั่วโมงสูงกว่าค่ากลางของรถในตัวกรองเดียวกัน"""
    valid = [r for r in rows if r["work_total"] > 0 and r["oil_total"] > 0]
    if len(valid) < MIN_CARS_TO_COMPARE:
        return []
    mid = median(r["fuel_rate"] for r in valid)
    hits = sorted(
        (r for r in valid if mid > 0 and r["fuel_rate"] > mid * FUEL_RATE_FACTOR),
        key=lambda r: -r["fuel_rate"],
    )
    if not hits:
        return []
    return [
        item(
            MEDIUM,
            "efficiency",
            f"รถ {len(hits)} คันใช้น้ำมันสูงผิดปกติ",
            f"ลิตร/ชม. เกิน {FUEL_RATE_FACTOR:g} เท่าของค่ากลาง ({mid:,.2f} ลิตร/ชม.): "
            f"{names(hits, with_company)} อาจมาจากเครื่องยนต์มีปัญหา หรือบันทึกน้ำมัน/ชั่วโมงไม่ครบ",
            car_target(hits[0]),
            "ดูคันที่สูงที่สุด",
        )
    ]


def _change(values):
    """เทียบค่าเฉลี่ย TREND_MONTHS เดือนล่าสุด กับช่วงก่อนหน้า (ข้ามค่า None)"""
    recent = [v for v in values[-TREND_MONTHS:] if v is not None]
    before = [v for v in values[:-TREND_MONTHS] if v is not None]
    if len(recent) < 2 or len(before) < 2:
        return None
    a, b = mean(before), mean(recent)
    return (a, b, (b - a) / a) if a > 0 else None


def trends(data, partial_last_month):
    """แนวโน้ม 3 เดือนล่าสุดเทียบช่วงก่อนหน้า: จำนวนครั้งที่เสีย, เวลาซ่อมเฉลี่ย, ค่าซ่อม"""
    trim = slice(None, -1) if partial_last_month else slice(None)
    rel = data["reliability"]["trend"]
    checks = [
        ("จำนวนครั้งที่เสีย", rel["count"][trim], "{:,.0f} ครั้ง/เดือน"),
        ("เวลาซ่อมเฉลี่ย", rel["mttr"][trim], "{:,.0f} ชม."),
        ("ค่าซ่อม", data["charts"]["repair_vs_work"]["repair"][trim], None),
    ]
    out = []
    for label, values, fmt in checks:
        result = _change(values)
        if not result:
            continue
        before, recent, change = result
        if abs(change) < TREND_CHANGE:
            continue
        show = (lambda v: baht(v) + "/เดือน") if fmt is None else fmt.format
        better = change < 0  # ทั้งสามค่า ยิ่งน้อยยิ่งดี
        out.append(
            item(
                GOOD if better else MEDIUM,
                "trend",
                f"{label}{'ลดลง' if better else 'เพิ่มขึ้น'} {abs(change) * 100:.0f}%",
                f"{TREND_MONTHS} เดือนล่าสุดเฉลี่ย {show(recent)} จากช่วงก่อนหน้า {show(before)}",
            )
        )
    return out


def data_quality(data, rows, unmatched_total, no_dep_cars):
    """สิ่งที่ทำให้ตัวเลขเพี้ยน — แก้ที่ webstock"""
    problems = []
    if unmatched_total > 0:
        problems.append(f"ค่าซ่อม {baht(unmatched_total)} ยังจับคู่กับรถไม่ได้ (ดูในแท็บอื่นๆ)")
    negative = [r for r in rows if r["work_total"] < 0]
    if negative:
        problems.append(f"ชั่วโมงทำงานติดลบ {len(negative)} คัน (เลขไมล์คีย์ผิดในบันทึกการใช้รถ)")
    no_work = [r for r in rows if r["oil_total"] > 0 and r["work_total"] == 0]
    if no_work:
        problems.append(f"เติมน้ำมันแต่ไม่มีชั่วโมงทำงาน {len(no_work)} คัน")
    if no_dep_cars:
        problems.append(f"รถยังไม่ได้ตั้งแผนก {no_dep_cars} คัน")
    if not problems:
        return []
    worst = min(negative, key=lambda r: r["work_total"]) if negative else None
    return [
        item(
            INFO,
            "data",
            "ข้อมูลที่ทำให้ตัวเลขคลาดเคลื่อน",
            " · ".join(problems),
            car_target(worst) if worst else None,
            "ดูคันที่ชั่วโมงติดลบ",
        )
    ]


def selected_car_overview(data):
    """เลือกรถคันเดียว: เทียบคันนี้กับรถคันอื่นในตัวกรองเดียวกัน"""
    car = data["selected_car"]
    rows = data["car_table"]["rows"]
    ranked = sorted(rows, key=lambda r: -r["repair_total"])
    rank = next(
        (
            i + 1
            for i, r in enumerate(ranked)
            if r["car_id"] == car["car_id"]
            and str(r["branch_company_id"]) == str(car["branch_company_id"])
        ),
        None,
    )
    lines = [f"{car_name(car)} ค่าซ่อม {baht(car['repair_total'])}"]
    if rank:
        lines[0] += f" อันดับ {rank} จาก {len(rows)} คัน"

    def compare(field, label, unit, valid):
        values = [r[field] for r in rows if valid(r) and r[field]]
        if len(values) < MIN_CARS_TO_COMPARE or not car.get(field):
            return
        mid = median(values)
        if mid <= 0:
            return
        ratio = car[field] / mid
        word = "สูงกว่า" if ratio >= 1 else "ต่ำกว่า"
        lines.append(
            f"{label} {car[field]:,.2f} {unit} {word}ค่ากลาง ({mid:,.2f}) "
            + (f"{times(ratio)}" if ratio >= 1 else f"{(1 - ratio) * 100:.0f}%")
        )

    compare("repair_cost_per_hr", "ต้นทุนซ่อม", "บาท/ชม.", lambda r: r["work_total"] > 0)
    compare("fuel_rate", "น้ำมัน", "ลิตร/ชม.", lambda r: r["work_total"] > 0)
    if car["failure_count"]:
        lines.append(
            f"เสีย {car['failure_count']} ครั้ง"
            + (f" เวลาซ่อมเฉลี่ย {car['mttr']:,.0f} ชม./ครั้ง" if car.get("mttr") else "")
        )
    return lines


# ---------------------------------------------------------------- entry


def build_insights(data, *, partial_last_month=False, unmatched_total=0.0, no_dep_cars=0):
    rows = data["car_table"]["rows"]
    with_company = len({r["branch_company_id"] for r in rows}) > 1
    car = data["selected_car"]

    if car:
        lines = selected_car_overview(data)
        items = month_spikes(data, show_causes=False) + trends(data, partial_last_month)
        negative = car["work_total"] < 0
        if negative:
            items += [
                item(
                    INFO,
                    "data",
                    "ชั่วโมงทำงานติดลบ",
                    "เลขไมล์/ชั่วโมงในบันทึกการใช้รถของคันนี้น่าจะคีย์ผิด ตัวเลขต่อชั่วโมงจึงคลาดเคลื่อน",
                )
            ]
    else:
        lines = overview(data, with_company)
        items = (
            urgent_cars(rows, with_company)
            + costly_per_hour(rows, with_company)
            + month_spikes(data)
            + fuel_hungry(rows, with_company)
            + trends(data, partial_last_month)
            + data_quality(data, rows, unmatched_total, no_dep_cars)
        )

    items.sort(key=lambda i: SEVERITY_ORDER[i["severity"]])
    return {"overview": lines, "items": items}
