"""รถที่ต้องจับตา: รวมสัญญาณผิดปกติของรถแต่ละคันไว้ที่เดียว

ข้อสังเกต (insights.py) สรุปเป็นข้อความตามกฎทีละข้อ ส่วนนี้กลับด้าน: แสดงทีละคัน
ว่าติดเกณฑ์อะไรบ้าง เกณฑ์เดียวกับข้อสังเกต (เทียบค่ากลางของรถในตัวกรองเดียวกัน)
ตัวเลขทั้งสองส่วนจึงตรงกัน

- ซ่อมแพงเทียบกับงาน: ต้นทุนซ่อม/ชม. เกิน COST_PER_HR_FACTOR เท่าของค่ากลาง
- เสียบ่อย: ชั่วโมงทำงานเฉลี่ยก่อนเสีย (MTBF) ต่ำกว่าครึ่งหนึ่งของค่ากลาง
- ซ่อมซ้ำ: แจ้งซ่อมประเภทซ่อมอีกภายใน REPEAT_DAYS วันหลังครั้งก่อน (ซ่อมแล้วอาจยังไม่หาย)
- ใช้น้ำมันสูง: ลิตร/ชม. เกิน FUEL_RATE_FACTOR เท่าของค่ากลาง
- จอดซ่อมนาน: มีใบแจ้งซ่อมยังไม่ปิดงานนานเกิน STALE_DAYS วัน (สถานะ ณ ตอนนี้)
- ควรพิจารณาเปลี่ยน: อายุ >= REPLACE_AGE ปี และต้นทุนซ่อม/ชม. เกิน REPLACE_COST_FACTOR เท่า
  ของค่ากลางในชนิดรถเดียวกัน (รถเก่าที่ซ่อมแพงกว่าคันอื่นในงานแบบเดียวกัน)
"""

from statistics import median

from dbapp.models import SummaryMaintenance
from dbapp.services.dashboard import MA_TYPE_BREAKDOWN, branch_ids, to_gregorian
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

# ลำดับความสำคัญของเหตุผล (ใช้เรียงรถที่ติดจำนวนข้อเท่ากัน)
REASON_WEIGHT = {STALE: 3, COST: 3, REPLACE: 2, REPEAT: 2, FAILURE: 2, FUEL: 1}


def _key(row):
    return (row["car_id"], str(row["branch_company_id"]))


def _keys(row):
    """แถวที่รวมหลายบริษัท (branch_company_id = "06,15") -> key ของแต่ละบริษัท"""
    return [(row["car_id"], b) for b in branch_ids(row["branch_company_id"])]


def _median_of(rows, field, valid):
    values = [r[field] for r in rows if valid(r)]
    return median(values) if len(values) >= MIN_CARS_TO_COMPARE else None


def _cost_mid_by_type(car_rows):
    """ค่ากลางต้นทุนซ่อม/ชม. แยกตามชนิดรถ (ชนิดที่รถน้อยกว่า MIN_CARS_TO_COMPARE ไม่เทียบ)"""
    by_type = {}
    for r in car_rows:
        if r["work_total"] > 0 and r["repair_total"] > 0:
            by_type.setdefault(r["car_type_id"], []).append(r["repair_cost_per_hr"])
    return {
        t: median(values) for t, values in by_type.items() if len(values) >= MIN_CARS_TO_COMPARE
    }


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


def build_watchlist(car_rows, maintenance_filter, open_jobs, noun="รถ", fuel=FUEL_PER_HOUR):
    """car_rows: แถวของตารางรถ (build_car_table)
    maintenance_filter: ตัวกรองใบแจ้งซ่อมของรถทั้งตาราง (มีปี ไม่กรองคันเดียว)
    open_jobs: ผลของ build_open_jobs (สถานะ ณ ตอนนี้)
    """
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
    type_cost_mid = _cost_mid_by_type(car_rows)

    repeats = repeat_repairs(maintenance_filter)

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
                }
            )

        type_mid = type_cost_mid.get(row["car_type_id"])
        if (
            type_mid
            and row["age"] is not None
            and row["age"] >= REPLACE_AGE
            and row["work_total"] > 0
            and row["repair_cost_per_hr"] > type_mid * REPLACE_COST_FACTOR
        ):
            type_name = row["car_type_name"] or noun
            reasons.append(
                {
                    "code": REPLACE,
                    "label": "ควรพิจารณาเปลี่ยน",
                    "detail": f"อายุ {row['age']} ปี "
                    f"ต้นทุนซ่อม {row['repair_cost_per_hr']:,.0f} บาท/ชม. "
                    f"({row['repair_cost_per_hr'] / type_mid:,.1f} เท่าของ{type_name}ส่วนใหญ่)",
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
            ]
        ],
        "cars": cars,
    }
