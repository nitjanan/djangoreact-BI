"""สรุปและข้อสังเกตอัตโนมัติของหน้า dashboard (คำนวณตามกฎ ไม่ใช้ AI)

ทำงานกับผลลัพธ์ของ build_dashboard() ที่คำนวณเสร็จแล้ว ไม่ query เพิ่ม
(ยกเว้นตัวเลขคุณภาพข้อมูลที่ส่งมาเป็น argument) จึงทดสอบได้โดยไม่ต้องมีฐานข้อมูล

เกณฑ์ทุกข้อเทียบกับรถในตัวกรองเดียวกัน (บริษัท/แผนก/ประเภทรถ) ใช้ค่ากลาง (median)
แทนค่าเฉลี่ย เพื่อไม่ให้รถคันที่ค่าสูงผิดปกติดึงเกณฑ์ขึ้นไปเอง
บนหน้าเว็บเรียกค่ากลางว่า "<แผนก>ส่วนใหญ่" เช่น "รถบรรทุกส่วนใหญ่" ให้ผู้ใช้ทั่วไปเข้าใจได้ทันที

การ์ดแต่ละใบ: หัวข้อ (เกิดอะไรขึ้น) + ตัวเลขเทียบ 2 ค่า (compare) + รถที่เกี่ยวข้อง (cars)
+ สิ่งที่ควรทำ (hint) — detail เป็นข้อความสรุปสั้น ๆ ของการ์ดทั้งใบ
"""

from statistics import mean, median, pstdev

# ระดับความสำคัญ เรียงจากสำคัญมากไปน้อย
HIGH = "high"
MEDIUM = "medium"
GOOD = "good"
INFO = "info"
SEVERITY_ORDER = {HIGH: 0, MEDIUM: 1, GOOD: 2, INFO: 3}

TOP_N = 10  # อันดับที่ถือว่า "สูง"
MAX_LISTED = 5  # จำนวนรถสูงสุดที่แสดงในการ์ดเดียว
COST_PER_HR_FACTOR = 3  # ต้นทุนซ่อม/ชม. สูงกว่าค่ากลางกี่เท่าจึงผิดปกติ
FUEL_RATE_FACTOR = 1.5  # น้ำมัน/ชม. สูงกว่าค่ากลางกี่เท่าจึงผิดปกติ
MIN_CARS_TO_COMPARE = 5  # รถน้อยกว่านี้ ค่ากลางไม่น่าเชื่อถือ ไม่เทียบ
TREND_MONTHS = 3  # ช่วงล่าสุดที่ใช้ดูแนวโน้ม
TREND_CHANGE = 0.2  # เปลี่ยนเกิน 20% จึงรายงาน

# อัตราการใช้น้ำมันที่ใช้เทียบของแต่ละแผนก
# เครื่องจักร: ลิตรต่อชั่วโมงทำงาน / รถบรรทุก: ลิตรต่อกิโลเมตร (เลขไมล์ในบันทึกการใช้รถ)
FUEL_PER_HOUR = {
    "field": "fuel_rate",
    "base": "work_total",
    "unit": "ลิตร/ชม.",
    "label": "น้ำมันต่อชั่วโมงทำงาน",
    "one": "ทำงาน 1 ชั่วโมง",
    "hint": "ตรวจเครื่องยนต์ หรือตรวจว่าบันทึกเติมน้ำมันและชั่วโมงทำงานครบหรือไม่",
}
FUEL_PER_KM = {
    "field": "liter_per_km",
    "base": "km_total",
    "unit": "ลิตร/กม.",
    "label": "น้ำมันต่อกิโลเมตร",
    "one": "วิ่ง 1 กม.",
    "hint": "ตรวจเครื่องยนต์ หรือตรวจว่าบันทึกเติมน้ำมันและเลขไมล์ครบหรือไม่",
}

DEFAULT_NOUN = "รถ"  # ชื่อแผนกที่เลือก (ยานพาหนะ, เครื่องจักรกลหนัก, ...) ใช้แทนคำว่า "รถ"


def typical(noun):
    """คำที่ใช้แทน "ค่ากลาง" บนหน้าเว็บ เช่น รถบรรทุกส่วนใหญ่"""
    return f"{noun}ส่วนใหญ่"


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


def car_entry(row, value, with_company=True):
    """รถหนึ่งคันในการ์ด: ชื่อ + ตัวเลขของคันนั้น กดไปดูรถได้"""
    return {
        "name": car_name(row),
        "company": (row.get("branch_company_name") or "") if with_company else "",
        "value": value,
        "target": car_target(row) if row.get("car_id") is not None else None,
    }


def compare(value, baseline, value_text, baseline_text, value_label, baseline_label):
    """ตัวเลข 2 ค่าที่แสดงคู่กันเป็นแถบ: ค่าที่ผิดปกติ เทียบกับค่าปกติ"""
    return {
        "value": float(value),
        "baseline": float(baseline),
        "value_text": value_text,
        "baseline_text": baseline_text,
        "value_label": value_label,
        "baseline_label": baseline_label,
    }


def item(
    severity,
    kind,
    title,
    detail,
    target=None,
    action="ดูคันนี้",
    *,
    compare=None,
    cars=(),
    points=(),
    hint="",
    chart=None,
):
    return {
        "severity": severity,
        "kind": kind,
        "title": title,
        "detail": detail,
        "target": target,
        # ข้อความปุ่มไปดูรถ (ไม่มี target = ไม่มีปุ่ม)
        "action": action if target else None,
        "compare": compare,
        "cars": list(cars),
        "points": list(points),
        "hint": hint,
        # กราฟที่เกี่ยวข้อง: กด hint แล้วเลื่อนไปที่กราฟนั้น (None = ไม่มีลิงก์)
        "chart": chart,
    }


def heat_name(label):
    """ชื่อจาก car_label() แบบ "ชื่อ:รหัส" -> "ชื่อ (รหัส)" """
    name, _, code = label.partition(":")
    return f"{name} ({code})" if code else name


def month_range(labels):
    """["กันยายน", "ตุลาคม", "พฤศจิกายน"] -> "กันยายน–พฤศจิกายน" """
    if not labels:
        return ""
    return labels[0] if len(labels) == 1 else f"{labels[0]}–{labels[-1]}"


# ---------------------------------------------------------------- rules


def fact(label, value, note="", *, share=None, tone=None):
    """ตัวเลขสรุป 1 ช่อง: หัวข้อสั้น + ตัวเลขใหญ่ + คำอธิบาย 1 บรรทัด
    share = สัดส่วน 0-100 (แสดงเป็นแถบเล็ก), tone = "bad"/"good" (สีของตัวเลข)
    """
    return {"label": label, "value": value, "note": note, "share": share, "tone": tone}


def overview(data, with_company, noun=DEFAULT_NOUN):
    """ตัวเลขสรุปภาพรวม: ยอดรวม, รถส่วนน้อยที่ใช้ค่าซ่อมส่วนใหญ่, งานซ่อมหลัก, เดือนสูงสุด"""
    charts = data["charts"]
    rows = data["car_table"]["rows"]

    months = charts["repair_by_month"]
    total = sum(months["series"])
    if total <= 0:
        return [fact("ค่าซ่อมรวม", "0 บาท", "ยังไม่มีค่าซ่อมในตัวกรองนี้")]
    facts = [fact("ค่าซ่อมรวม", baht(total), f"จาก{noun} {len(rows):,} คัน")]

    by_car = charts["repair_by_car"]
    if by_car["total"] > 0 and len(by_car["series"]) >= MIN_CARS_TO_COMPARE:
        running, count = 0.0, 0
        for v in by_car["series"]:
            running += v
            count += 1
            if running >= by_car["total"] * 0.8:
                break
        with_cost = len(by_car["series"])
        facts.append(
            fact(
                "ค่าซ่อมส่วนใหญ่มาจาก",
                f"{count} จาก {with_cost} คัน",
                f"{noun}กลุ่มนี้ใช้ค่าซ่อมรวมกัน 80%",
                share=count / with_cost * 100,
            )
        )

    by_type = charts["repair_by_type"]
    if by_type["total"] > 0 and by_type["series"]:
        share = by_type["series"][0] / by_type["total"] * 100
        facts.append(
            fact(
                "ซ่อมอะไรมากที่สุด",
                by_type["labels"][0],
                f"{share:.0f}% ของค่าซ่อมทั้งหมด",
                share=share,
            )
        )

    values = [v for v in months["series"] if v > 0]
    if len(values) >= 2:
        top = max(range(len(months["series"])), key=lambda i: months["series"][i])
        avg = mean(values)
        ratio = months["series"][top] / avg if avg else 0
        facts.append(
            fact(
                "เดือนที่จ่ายมากที่สุด",
                months["labels"][top],
                baht(months["series"][top])
                + (f" · {times(ratio)}ของเดือนทั่วไป" if ratio >= 1.1 else ""),
            )
        )
    return facts


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
        month = chart["labels"][i]
        causes = sorted(
            (r for r in heat["rows"] if i < len(r["data"]) and r["data"][i] > 0),
            key=lambda r: -r["data"][i],
        )[:3]
        cars = (
            [
                {
                    "name": heat_name(r["name"]),
                    "company": r.get("company") or "",
                    "value": baht(r["data"][i]),
                    "target": (
                        {"car_id": r["car_id"], "branch_company_id": str(r["branch_company_id"])}
                        if r.get("car_id") is not None
                        else None
                    ),
                }
                for r in causes
            ]
            if show_causes
            else []
        )
        cause_text = (
            " ส่วนใหญ่มาจาก " + ", ".join(f"{c['name']} {c['value']}" for c in cars) if cars else ""
        )
        out.append(
            item(
                MEDIUM,
                "anomaly",
                f"เดือน{month}จ่ายค่าซ่อมมากกว่าปกติ",
                f"{baht(v)} ({times(v / avg)}ของเดือนทั่วไป ที่เฉลี่ย {baht(avg)})" + cause_text,
                compare=compare(v, avg, baht(v), baht(avg), f"เดือน{month}", "เดือนทั่วไป (เฉลี่ย)"),
                cars=cars,
                hint="ดูว่าเป็นงานซ่อมใหญ่ที่วางแผนไว้ หรือเสียกะทันหัน",
                chart="repair_by_month",
            )
        )
    return out[:2]


def _change(values):
    """เทียบค่าเฉลี่ย TREND_MONTHS เดือนล่าสุด กับช่วงก่อนหน้า (ข้ามค่า None)"""
    recent = [v for v in values[-TREND_MONTHS:] if v is not None]
    before = [v for v in values[:-TREND_MONTHS] if v is not None]
    if len(recent) < 2 or len(before) < 2:
        return None
    a, b = mean(before), mean(recent)
    return (a, b, (b - a) / a) if a > 0 else None


def trends(data, partial_last_month, noun=DEFAULT_NOUN):
    """แนวโน้ม 3 เดือนล่าสุดเทียบช่วงก่อนหน้า: จำนวนครั้งที่เสีย, เวลาซ่อมเฉลี่ย, ค่าซ่อม"""
    trim = slice(None, -1) if partial_last_month else slice(None)
    rel = data["reliability"]["trend"]
    labels = list(rel["labels"])[trim]
    recent_label = month_range(labels[-TREND_MONTHS:])
    before_label = month_range(labels[:-TREND_MONTHS])
    checks = [
        ("จำนวนครั้งที่เสีย", rel["count"][trim], "{:,.1f} ครั้ง/เดือน", "reliability"),
        ("เวลาซ่อมเฉลี่ย", rel["mttr"][trim], "{:,.0f} ชม./ครั้ง", "reliability"),
        ("ค่าซ่อม", data["charts"]["repair_vs_work"]["repair"][trim], None, "repair_by_month"),
    ]
    out = []
    for label, values, fmt, chart in checks:
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
                f"{label}{'ลดลง' if better else 'เพิ่มขึ้น'} {abs(change) * 100:.0f}% ช่วงหลัง",
                f"{recent_label} เฉลี่ย {show(recent)} จาก {before_label} ที่เฉลี่ย {show(before)}",
                compare=compare(
                    recent,
                    before,
                    show(recent),
                    show(before),
                    f"{TREND_MONTHS} เดือนล่าสุด ({recent_label})",
                    f"ก่อนหน้านั้น ({before_label})",
                ),
                hint=""
                if better
                else f"ดูกราฟรายเดือนด้านล่างว่าเพิ่มขึ้นจาก{noun}คันไหนหรือประเภทงานซ่อมอะไร",
                chart=None if better else chart,
            )
        )
    return out


def data_quality(data, rows, unmatched_total, no_dep_cars):
    """สิ่งที่ทำให้ตัวเลขเพี้ยน — แก้ที่ webstock"""
    problems = []
    if unmatched_total > 0:
        problems.append(
            f"ค่าซ่อม {baht(unmatched_total)} ยังไม่รู้ว่าเป็นของรถ/เครื่องจักรคันไหน (ดูรายการในแท็บอื่นๆ)"
        )
    negative = [r for r in rows if r["work_total"] < 0]
    if negative:
        problems.append(f"{len(negative)} คันชั่วโมงทำงานติดลบ (เลขไมล์ในบันทึกการใช้รถคีย์ผิด)")
    no_work = [r for r in rows if r["oil_total"] > 0 and r["work_total"] == 0]
    if no_work:
        problems.append(f"{len(no_work)} คันเติมน้ำมันแต่ไม่มีบันทึกชั่วโมงทำงาน")
    if no_dep_cars:
        problems.append(f"{no_dep_cars} คันยังไม่ได้กำหนดแผนกใน webstock")
    if not problems:
        return []
    worst = min(negative, key=lambda r: r["work_total"]) if negative else None
    return [
        item(
            INFO,
            "data",
            "ข้อมูลบางส่วนยังไม่ครบ ตัวเลขอาจคลาดเคลื่อน",
            " · ".join(problems),
            car_target(worst) if worst else None,
            "ดูคันที่ชั่วโมงติดลบ",
            points=problems,
            hint="แก้ที่ webstock แล้วกดอัปเดตข้อมูล ตัวเลขในหน้านี้จะถูกต้องขึ้น",
        )
    ]


def selected_car_overview(data, noun=DEFAULT_NOUN, fuel=FUEL_PER_HOUR):
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
    facts = [
        fact(
            "ค่าซ่อมรวม",
            baht(car["repair_total"]),
            f"มากเป็นอันดับ {rank} จาก {len(rows)} คัน" if rank else car_name(car),
        )
    ]

    def versus(field, label, unit, digits, valid):
        values = [r[field] for r in rows if valid(r) and r[field]]
        if len(values) < MIN_CARS_TO_COMPARE or not car.get(field):
            return
        mid = median(values)
        if mid <= 0:
            return
        ratio = car[field] / mid
        diff = (
            f"สูงกว่า{typical(noun)} {times(ratio)}"
            if ratio >= 1
            else f"ต่ำกว่า{typical(noun)} {(1 - ratio) * 100:.0f}%"
        )
        facts.append(
            fact(
                label,
                f"{car[field]:,.{digits}f} {unit}",
                f"{diff} ({mid:,.{digits}f} {unit})",
                tone="bad" if ratio >= 1.5 else "good" if ratio < 1 else None,
            )
        )

    versus(
        "repair_cost_per_hr",
        "ค่าซ่อมต่อชั่วโมงทำงาน",
        "บาท",
        0,
        lambda r: r["work_total"] > 0,
    )
    versus(fuel["field"], fuel["label"], fuel["unit"], 2, lambda r: r[fuel["base"]] > 0)
    if car["failure_count"]:
        facts.append(
            fact(
                "เสีย",
                f"{car['failure_count']} ครั้ง",
                f"ซ่อมนานเฉลี่ย {car['mttr']:,.0f} ชม./ครั้ง" if car.get("mttr") else "",
            )
        )
    return facts


# ---------------------------------------------------------------- entry


def build_insights(
    data,
    *,
    partial_last_month=False,
    unmatched_total=0.0,
    no_dep_cars=0,
    noun=DEFAULT_NOUN,
    fuel=FUEL_PER_HOUR,
):
    rows = data["car_table"]["rows"]
    with_company = len({r["branch_company_id"] for r in rows}) > 1
    car = data["selected_car"]

    if car:
        lines = selected_car_overview(data, noun, fuel)
        items = month_spikes(data, show_causes=False) + trends(data, partial_last_month, noun)
        negative = car["work_total"] < 0
        if negative:
            items += [
                item(
                    INFO,
                    "data",
                    "ชั่วโมงทำงานติดลบ",
                    "เลขไมล์/ชั่วโมงในบันทึกการใช้รถของคันนี้น่าจะคีย์ผิด ตัวเลขต่อชั่วโมงจึงคลาดเคลื่อน",
                    hint="แก้บันทึกการใช้รถที่ webstock แล้วกดอัปเดตข้อมูล",
                )
            ]
    else:
        lines = overview(data, with_company, noun)
        # รายชื่อรถที่ผิดปกติ (ซ่อมแพง/เสียบ่อย/กินน้ำมัน) อยู่ใน "รถที่ต้องจับตา" ที่เดียว
        # ส่วนนี้เหลือเฉพาะภาพรวม: เดือนที่พุ่ง แนวโน้ม และคุณภาพข้อมูล
        items = (
            month_spikes(data)
            + trends(data, partial_last_month, noun)
            + data_quality(data, rows, unmatched_total, no_dep_cars)
        )

    items.sort(key=lambda i: SEVERITY_ORDER[i["severity"]])
    return {"overview": lines, "items": items}
