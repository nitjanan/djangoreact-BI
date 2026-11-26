"""รถที่ต้องจับตา: รวมสัญญาณผิดปกติของรถแต่ละคันไว้ที่เดียว

ข้อสังเกต (insights.py) สรุปเป็นข้อความตามกฎทีละข้อ ส่วนนี้กลับด้าน: แสดงทีละคัน
ว่าติดเกณฑ์อะไรบ้าง เกณฑ์เดียวกับข้อสังเกต (เทียบค่ากลางของรถในตัวกรองเดียวกัน)
ตัวเลขทั้งสองส่วนจึงตรงกัน

- ซ่อมแพงเทียบกับงาน: ต้นทุนซ่อม/ชม. เกิน COST_PER_HR_FACTOR เท่าของค่ากลาง
- เสียบ่อย: ชั่วโมงทำงานเฉลี่ยก่อนเสีย (MTBF) ต่ำกว่าครึ่งหนึ่งของค่ากลาง
- ซ่อมซ้ำ: แจ้งซ่อมประเภทซ่อมอีกภายใน REPEAT_DAYS วันหลังครั้งก่อน (ซ่อมแล้วอาจยังไม่หาย)
- ใช้น้ำมันสูง: ลิตร/ชม. เกิน FUEL_RATE_FACTOR เท่าของค่ากลาง
- จอดซ่อมนาน: มีใบแจ้งซ่อมยังไม่ปิดงานนานเกิน STALE_DAYS วัน (สถานะ ณ ตอนนี้)
- น้ำมันพุ่ง: เดือนที่อัตราสิ้นเปลืองสูงกว่าปกติของคันเดียวกัน (fleet_usage.py)
- ใช้งานน้อย: จอดนิ่งหลายเดือน หรือชั่วโมงทำงานต่ำกว่าคันอื่นมาก (fleet_usage.py)
- ควรพิจารณาเปลี่ยน: ติดหลายสัญญาณพร้อมกัน (อายุมาก ซ่อมแพงกว่าชนิดเดียวกัน เสียบ่อย
  หยุดซ่อมนาน ค่าซ่อมเพิ่มขึ้น) ดูเกณฑ์ใน replacement.py
"""

from statistics import median

from dbapp.models import SummaryMaintenance
from dbapp.services.dashboard import MA_TYPE_BREAKDOWN, MONTHS_TH, branch_ids, to_gregorian
from dbapp.services.insights import (
    COST_PER_HR_FACTOR,
    FUEL_PER_HOUR,
    FUEL_RATE_FACTOR,
    MIN_CARS_TO_COMPARE,
)
from dbapp.services.open_jobs import STALE_DAYS

MTBF_FACTOR = 0.5  # MTBF ต่ำกว่าค่ากลางกี่เท่าจึงถือว่าเสียบ่อย
MIN_FAILURES = 2  # เสียครั้งเดียว MTBF ยังเชื่อไม่ได้
REPEAT_DAYS = 30
REPLACE_AGE = 10  # ปี
REPLACE_COST_FACTOR = 1.5

COST = "cost"
FAILURE = "failure"
REPEAT = "repeat"
FUEL = "fuel"
STALE = "stale"
REPLACE = "replace"
FUEL_SPIKE = "fuel_spike"
LOW_USE = "low_use"

# ลำดับความสำคัญของเหตุผล (ใช้เรียงรถที่ติดจำนวนข้อเท่ากัน)
# สัญญาณของ replacement.py ที่ตรงกับป้ายในส่วนนี้
SIGNAL_BADGE = {"costly": COST, "failure": FAILURE}

REASON_WEIGHT = {
    STALE: 3,
    COST: 3,
    REPLACE: 2,
    REPEAT: 2,
    FAILURE: 2,
    FUEL: 1,
    FUEL_SPIKE: 1,
    LOW_USE: 1,
}


def _key(row):
    return (row["car_id"], str(row["branch_company_id"]))


def _keys(row):
    """แถวที่รวมหลายบริษัท (branch_company_id = "06,15") -> key ของแต่ละบริษัท"""
    return [(row["car_id"], b) for b in branch_ids(row["branch_company_id"])]


def _hours(value):
    """ชั่วโมงน้อยกว่า 10 แสดงทศนิยม 1 ตำแหน่ง (ไม่ให้ปัดเป็น 0)"""
    return f"{value:,.1f}" if value < 10 else f"{value:,.0f}"


def _median_of(rows, field, valid):
    values = [r[field] for r in rows if valid(r)]
    return median(values) if len(values) >= MIN_CARS_TO_COMPARE else None


def repeat_repairs(maintenance_filter):
    """{(car_id, branch_company_id): [(วันที่แจ้งครั้งก่อน, วันที่แจ้งซ้ำ)]}"""
    rows = (
        SummaryMaintenance.objects.filter(
            **maintenance_filter, ma_type=MA_TYPE_BREAKDOWN, car_id__isnull=False
        )
        .exclude(reported_at=None)
        .values_list("car_id", "branch_company_id", "reported_at")
    )
    # บางใบบันทึกปีเป็น พ.ศ. แปลงก่อนเรียงและนับวัน
    rows = sorted((c, str(b), to_gregorian(r)) for c, b, r in rows)
    result = {}
    previous = {}
    for car_id, company_id, reported_at in rows:
        key = (car_id, str(company_id))
        last = previous.get(key)
        if last is not None and (reported_at - last).days <= REPEAT_DAYS:
            result.setdefault(key, []).append((last, reported_at))
        previous[key] = reported_at
    return result


def _by_car(entries):
    """{(car_id, branch_company_id): แถว} จากผลของ fleet_usage (หนึ่งแถวต่อบริษัท)"""
    return {(e["car_id"], str(e["branch_company_id"])): e for e in entries}


def build_watchlist(
    car_rows,
    maintenance_filter,
    open_jobs,
    noun="รถ",
    fuel=FUEL_PER_HOUR,
    months=None,
    fuel_anomalies=None,
    low_use=None,
):
    """car_rows: แถวของตารางรถ (build_car_table)
    maintenance_filter: ตัวกรองใบแจ้งซ่อมของรถทั้งตาราง (มีปี ไม่กรองคันเดียว)
    open_jobs: ผลของ build_open_jobs (สถานะ ณ ตอนนี้)
    fuel_anomalies / low_use: ผลของ build_fuel_anomalies / build_low_use (None = ไม่ตรวจ)
    months: เดือนที่จบแล้ว ใช้ดูแนวโน้มค่าซ่อม/ค่าซ่อมต่อปีของเหตุผลควรพิจารณาเปลี่ยน
      (None = ทุกเดือนในตัวกรอง)
    """
    # import ในฟังก์ชัน: replacement ใช้ค่าคงที่จากไฟล์นี้
    from dbapp.services.replacement import build_replacement, monthly_repairs

    if months is None:
        months = range(
            maintenance_filter.get("month__gte", 1), maintenance_filter.get("month__lte", 12) + 1
        )
    replace = {
        (c["car_id"], c["branch_company_id"]): c
        for c in build_replacement(car_rows, maintenance_filter, months, noun, limit=None)["cars"]
    }
    cost_mid = _median_of(
        car_rows, "repair_cost_per_hr", lambda r: r["work_total"] > 0 and r["repair_total"] > 0
    )
    repair_mid = _median_of(
        car_rows, "repair_total", lambda r: r["work_total"] > 0 and r["repair_total"] > 0
    )
    fuel_field = fuel["field"]
    fuel_mid = _median_of(
        car_rows, fuel_field, lambda r: r[fuel["base"]] > 0 and r["oil_total"] > 0
    )
    mtbf_mid = _median_of(car_rows, "mtbf", lambda r: r["mtbf"] is not None)

    repeats = repeat_repairs(maintenance_filter)
    spikes = _by_car(fuel_anomalies["cars"]) if fuel_anomalies else {}
    low = _by_car(low_use["cars"]) if low_use else {}
    low_mid = low_use["median_hours"] if low_use else None
    monthly = monthly_repairs(maintenance_filter)

    # ใบค้างนานที่สุดของแต่ละคัน
    stale = {}
    for job in open_jobs["jobs"]:
        if job["car_id"] is None or job["days"] <= STALE_DAYS:
            continue
        key = _key(job)
        if key not in stale or job["days"] > stale[key]["days"]:
            stale[key] = job

    cars = []
    for row in car_rows:
        keys = _keys(row)
        pairs = sorted(p for k in keys for p in repeats.get(k, []))
        stale_job = max(
            (stale[k] for k in keys if k in stale), key=lambda j: j["days"], default=None
        )
        reasons = []

        if (
            cost_mid
            and row["work_total"] > 0
            and row["repair_cost_per_hr"] > cost_mid * COST_PER_HR_FACTOR
            and row["repair_total"] >= repair_mid
        ):
            reasons.append(
                {
                    "code": COST,
                    "label": "ซ่อมแพงเทียบกับงาน",
                    "detail": f"{row['repair_cost_per_hr']:,.0f} บาท/ชม. "
                    f"({row['repair_cost_per_hr'] / cost_mid:,.1f} เท่าของ{noun}ส่วนใหญ่)",
                    "value": f"{row['repair_cost_per_hr']:,.0f} บาท/ชม.",
                    "note": f"{row['repair_cost_per_hr'] / cost_mid:,.1f} เท่าของ{noun}ส่วนใหญ่",
                    "sort": row["repair_cost_per_hr"] / cost_mid,
                }
            )

        if (
            mtbf_mid
            and row["mtbf"] is not None
            and row["failure_count"] >= MIN_FAILURES
            and row["mtbf"] < mtbf_mid * MTBF_FACTOR
        ):
            reasons.append(
                {
                    "code": FAILURE,
                    "label": "เสียบ่อย",
                    "detail": f"เสีย {row['failure_count']} ครั้ง ทำงานเฉลี่ย "
                    f"{row['mtbf']:,.0f} ชม. ต่อครั้ง ({noun}ส่วนใหญ่ {mtbf_mid:,.0f} ชม.)",
                    "value": f"{row['failure_count']} ครั้ง",
                    "note": f"ทำงาน {_hours(row['mtbf'])} ชม./ครั้ง "
                    f"({noun}ส่วนใหญ่ {_hours(mtbf_mid)})",
                    "sort": mtbf_mid / row["mtbf"] if row["mtbf"] else row["failure_count"],
                }
            )

        if pairs:
            gap = min((b - a).days for a, b in pairs)
            reasons.append(
                {
                    "code": REPEAT,
                    "label": "ซ่อมซ้ำ",
                    "detail": f"แจ้งซ่อมซ้ำภายใน {REPEAT_DAYS} วัน {len(pairs)} ครั้ง "
                    f"(ห่างกันน้อยสุด {gap} วัน)",
                    "value": f"{len(pairs)} ครั้ง",
                    "note": f"ห่างกันน้อยสุด {gap} วัน",
                    "sort": len(pairs) - gap / 1000,
                }
            )

        if (
            fuel_mid
            and row[fuel["base"]] > 0
            and row["oil_total"] > 0
            and row[fuel_field] > fuel_mid * FUEL_RATE_FACTOR
        ):
            reasons.append(
                {
                    "code": FUEL,
                    "label": "ใช้น้ำมันสูง",
                    "detail": f"{row[fuel_field]:,.2f} {fuel['unit']} "
                    f"({row[fuel_field] / fuel_mid:,.1f} เท่าของ{noun}ส่วนใหญ่)",
                    "value": f"{row[fuel_field]:,.2f} {fuel['unit']}",
                    "note": f"{row[fuel_field] / fuel_mid:,.1f} เท่าของ{noun}ส่วนใหญ่",
                    "sort": row[fuel_field] / fuel_mid,
                }
            )

        spike = max(
            (spikes[k] for k in keys if k in spikes), key=lambda c: c["extra_liters"], default=None
        )
        if spike:
            worst = max(spike["spikes"], key=lambda m: m["ratio"])
            months_text = ", ".join(m["label"] for m in spike["spikes"])
            reasons.append(
                {
                    "code": FUEL_SPIKE,
                    "label": "น้ำมันพุ่ง",
                    "detail": f"เดือน{months_text} ใช้น้ำมันสูงกว่าปกติของคันนี้ "
                    f"(สูงสุด {worst['ratio']:,.1f} เท่า) เกินประมาณ {spike['extra_liters']:,.0f} ลิตร",
                    "value": f"เกิน {spike['extra_liters']:,.0f} ลิตร",
                    "note": f"{len(spike['spikes'])} เดือน · สูงสุด {worst['label']} "
                    f"{worst['ratio']:,.1f} เท่าของปกติ",
                    "sort": spike["extra_liters"],
                }
            )

        idle = [low[k] for k in keys if k in low]
        if idle:
            u = max(idle, key=lambda c: (c["idle_streak"], -c["avg_hours"]))
            if u["idle"]:
                reasons.append(
                    {
                        "code": LOW_USE,
                        "label": "ใช้งานน้อย",
                        "detail": f"ไม่มีชั่วโมงทำงานและไม่เติมน้ำมัน {u['idle_streak']} เดือนล่าสุด",
                        "value": f"จอด {u['idle_streak']} เดือน",
                        "note": "ไม่มีงานและไม่เติมน้ำมัน",
                        "sort": 1000 + u["idle_streak"],
                    }
                )
            elif u["low_hours"]:
                reasons.append(
                    {
                        "code": LOW_USE,
                        "label": "ใช้งานน้อย",
                        "detail": f"ทำงานเฉลี่ย {u['avg_hours']:,.0f} ชม./เดือน "
                        f"({u['ratio'] * 100:,.0f}% ของ{noun}ส่วนใหญ่ ที่ {low_mid or 0:,.0f} ชม.)",
                        "value": f"{u['avg_hours']:,.0f} ชม./เดือน",
                        "note": f"{u['ratio'] * 100:,.0f}% ของ{noun}ส่วนใหญ่ "
                        f"({low_mid or 0:,.0f} ชม.)",
                        "sort": 1 - u["ratio"],
                    }
                )

        candidate = replace.get((row["car_id"], str(row["branch_company_id"])))
        shown, covered = [], []
        if candidate:
            # สัญญาณที่มีป้ายของตัวเองแล้ว (ซ่อมแพง/เสียบ่อย) ไม่เขียนซ้ำ บอกแค่ว่านับรวมด้วย
            badged = {r["code"] for r in reasons}
            shown = [s for s in candidate["signals"] if SIGNAL_BADGE.get(s["code"]) not in badged]
            parts = [s["detail"] for s in shown]
            if candidate["annual_repair"]:
                parts.append(f"ค่าซ่อมประมาณ {candidate['annual_repair']:,.0f} บาท/ปี")
            covered = [
                r["label"]
                for r in reasons
                if r["code"] in {SIGNAL_BADGE.get(s["code"]) for s in candidate["signals"]}
            ]
            if covered:
                parts.append("ร่วมกับ" + "และ".join(covered))
            annual = candidate["annual_repair"]
            reasons.append(
                {
                    "code": REPLACE,
                    "label": "ควรพิจารณาเปลี่ยน",
                    "detail": " · ".join(parts),
                    "value": (
                        f"{annual:,.0f} บาท/ปี" if annual else f"{len(candidate['signals'])} สัญญาณ"
                    ),
                    "note": ", ".join(s["label"] for s in candidate["signals"]),
                    "sort": annual or 0,
                }
            )

        if stale_job:
            job = stale_job
            reasons.append(
                {
                    "code": STALE,
                    "label": "จอดซ่อมนาน",
                    "detail": f"{job['ref_no'] or 'ใบแจ้งซ่อม'} ค้าง {job['days']} วัน"
                    + (" · เคลื่อนย้ายไม่ได้" if job["immobile"] else ""),
                    "value": f"{job['days']} วัน",
                    "note": (job["ref_no"] or "ใบแจ้งซ่อม")
                    + (" · เคลื่อนย้ายไม่ได้" if job["immobile"] else ""),
                    "sort": job["days"],
                }
            )

        if reasons:
            cars.append(
                {
                    "car_id": row["car_id"],
                    "branch_company_id": str(row["branch_company_id"]),
                    "branch_company_name": row["branch_company_name"],
                    "code": row["code"],
                    "name": row["name"],
                    "repair_total": row["repair_total"],
                    "failure_count": row["failure_count"],
                    "reasons": reasons,
                    "age": row["age"],
                    "car_type_name": row["car_type_name"] or "",
                    # ค่าซ่อมรายเดือน (เดือนที่จบแล้ว) ตรงกับ months
                    "monthly": [sum(monthly.get(k, {}).get(m, 0.0) for k in keys) for m in months],
                    # รายละเอียดแบบแยกช่อง ของเหตุผลควรพิจารณาเปลี่ยน (หน้าเว็บแสดงเป็นป้าย + กราฟ)
                    "replace": (
                        {
                            "signals": [
                                {"code": s["code"], "label": s["label"], "value": s["short"]}
                                for s in shown
                            ],
                            "covered": covered,
                            "annual_repair": candidate["annual_repair"],
                        }
                        if candidate
                        else None
                    ),
                }
            )

    cars.sort(
        key=lambda c: (
            -len(c["reasons"]),
            -sum(REASON_WEIGHT[r["code"]] for r in c["reasons"]),
            -c["repair_total"],
        )
    )
    counts = {}
    for car in cars:
        for r in car["reasons"]:
            counts[r["code"]] = counts.get(r["code"], 0) + 1

    return {
        "car_count": len(car_rows),
        "months": [MONTHS_TH[m - 1] for m in months],
        # เทียบค่ากลางได้ไหม (รถน้อยกว่า MIN_CARS_TO_COMPARE คัน เกณฑ์ที่ใช้ค่ากลางจะไม่ทำงาน)
        "compared": cost_mid is not None or mtbf_mid is not None or fuel_mid is not None,
        "reasons": [
            {"code": code, "label": label, "count": counts.get(code, 0)}
            for code, label in [
                (STALE, "จอดซ่อมนาน"),
                (COST, "ซ่อมแพงเทียบกับงาน"),
                (REPLACE, "ควรพิจารณาเปลี่ยน"),
                (REPEAT, "ซ่อมซ้ำ"),
                (FAILURE, "เสียบ่อย"),
                (FUEL, "ใช้น้ำมันสูง"),
                (FUEL_SPIKE, "น้ำมันพุ่ง"),
                (LOW_USE, "ใช้งานน้อย"),
            ]
        ],
        "cars": cars,
    }
