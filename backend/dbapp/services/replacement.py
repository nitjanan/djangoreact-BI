"""รถที่ควรพิจารณาเปลี่ยนแทนการซ่อม: รวมหลายสัญญาณ ใช้เป็นเหตุผล "ควรพิจารณาเปลี่ยน"
ใน "รถที่ต้องจับตา" (watchlist.py) พร้อมค่าซ่อมต่อปีไว้เทียบกับราคารถใหม่

สัญญาณ (เทียบกับรถในตัวกรองเดียวกัน)
- old: อายุ >= REPLACE_AGE ปี
- costly: ต้นทุนซ่อม/ชม. เกิน REPLACE_COST_FACTOR เท่าของค่ากลางในชนิดเดียวกัน
  (ชนิดที่มีรถน้อยกว่า MIN_CARS_TO_COMPARE คัน เทียบกับค่ากลางของรถทั้งหมด)
- failure: เสียบ่อย (MTBF ต่ำกว่า MTBF_FACTOR ของค่ากลาง และเสียอย่างน้อย MIN_FAILURES ครั้ง)
- downtime: ชั่วโมงหยุดซ่อมเกิน DOWNTIME_FACTOR เท่าของค่ากลาง
- rising: ค่าซ่อมครึ่งหลังของช่วงสูงกว่าครึ่งแรก RISING_FACTOR เท่า (และค่าซ่อมไม่น้อย)

เป็นตัวเลือก = ติดอย่างน้อย MIN_SIGNALS สัญญาณ และหนึ่งในนั้นเป็น old หรือ costly
(เสียบ่อยอย่างเดียวในรถใหม่ที่ค่าซ่อมไม่แพง ควรแก้ที่การซ่อม ไม่ใช่เปลี่ยนรถ)
"""

from statistics import median

from django.db.models import Sum

from dbapp.models import SummaryRepair
from dbapp.services.dashboard import branch_ids
from dbapp.services.insights import MIN_CARS_TO_COMPARE
from dbapp.services.watchlist import (
    MIN_FAILURES,
    MTBF_FACTOR,
    REPLACE_AGE,
    REPLACE_COST_FACTOR,
)

DOWNTIME_FACTOR = 2.0
RISING_FACTOR = 1.5
MIN_SIGNALS = 2
TOP_CARS = 20

OLD, COSTLY, FAILURE, DOWNTIME, RISING = "old", "costly", "failure", "downtime", "rising"
SIGNAL_LABELS = {
    OLD: "อายุมาก",
    COSTLY: "ซ่อมแพงกว่าชนิดเดียวกัน",
    FAILURE: "เสียบ่อย",
    DOWNTIME: "หยุดซ่อมนาน",
    RISING: "ค่าซ่อมเพิ่มขึ้น",
}


def _mid(values):
    values = list(values)
    return median(values) if len(values) >= MIN_CARS_TO_COMPARE else None


def monthly_repairs(table_filter):
    """{(car_id, branch_company_id): {เดือน: ค่าซ่อม}}"""
    result = {}
    for r in (
        SummaryRepair.objects.filter(**table_filter, car_id__isnull=False)
        .values("car_id", "branch_company_id", "month")
        .annotate(amount=Sum("amount"))
    ):
        key = (r["car_id"], str(r["branch_company_id"]))
        result.setdefault(key, {})[int(r["month"])] = float(r["amount"] or 0)
    return result


def build_replacement(car_rows, table_filter, months, noun="รถ", limit=TOP_CARS):
    """car_rows: แถวตารางรถ · table_filter: ตัวกรองของตารางรถ (มีปี)
    months: เดือนที่จบแล้วในช่วงที่เลือก (ใช้ดูแนวโน้มและค่าซ่อมต่อปี)
    """
    months = list(months)
    with_cost = [r for r in car_rows if r["work_total"] > 0 and r["repair_total"] > 0]
    fleet_cost_mid = _mid(r["repair_cost_per_hr"] for r in with_cost)
    by_type = {}
    for r in with_cost:
        by_type.setdefault(r["car_type_id"], []).append(r["repair_cost_per_hr"])
    type_cost_mid = {t: median(v) for t, v in by_type.items() if len(v) >= MIN_CARS_TO_COMPARE}
    mtbf_mid = _mid(r["mtbf"] for r in car_rows if r["mtbf"] is not None)
    downtime_mid = _mid(r["downtime_hours"] for r in car_rows if r["downtime_hours"] > 0)
    repair_mid = _mid(r["repair_total"] for r in car_rows if r["repair_total"] > 0)

    monthly = monthly_repairs(table_filter)
    half = len(months) // 2
    early, late = months[:half], months[len(months) - half :]

    candidates = []
    for row in car_rows:
        per_month = {}
        for b in branch_ids(row["branch_company_id"]):
            for m, amount in monthly.get((row["car_id"], b), {}).items():
                per_month[m] = per_month.get(m, 0.0) + amount
        signals = []

        if row["age"] is not None and row["age"] >= REPLACE_AGE:
            signals.append((OLD, f"อายุ {row['age']} ปี (เกณฑ์ {REPLACE_AGE} ปี)"))

        type_mid = type_cost_mid.get(row["car_type_id"])
        cost_mid, cost_scope = (
            (type_mid, row["car_type_name"] or noun) if type_mid else (fleet_cost_mid, noun)
        )
        cost_ratio = (
            row["repair_cost_per_hr"] / cost_mid if cost_mid and row["work_total"] > 0 else None
        )
        if cost_ratio is not None and cost_ratio > REPLACE_COST_FACTOR:
            signals.append(
                (
                    COSTLY,
                    f"{row['repair_cost_per_hr']:,.0f} บาท/ชม. "
                    f"({cost_ratio:,.1f} เท่าของ{cost_scope}ส่วนใหญ่)",
                )
            )

        if (
            mtbf_mid
            and row["mtbf"] is not None
            and row["failure_count"] >= MIN_FAILURES
            and row["mtbf"] < mtbf_mid * MTBF_FACTOR
        ):
            signals.append(
                (FAILURE, f"เสีย {row['failure_count']} ครั้ง ทำงานเฉลี่ย {row['mtbf']:,.0f} ชม./ครั้ง")
            )

        if downtime_mid and row["downtime_hours"] > downtime_mid * DOWNTIME_FACTOR:
            signals.append(
                (
                    DOWNTIME,
                    f"หยุดซ่อม {row['downtime_hours']:,.0f} ชม. "
                    f"({row['downtime_hours'] / downtime_mid:,.1f} เท่าของ{noun}ส่วนใหญ่)",
                )
            )

        trend = None
        if half >= 2:
            first = sum(per_month.get(m, 0.0) for m in early)
            last = sum(per_month.get(m, 0.0) for m in late)
            trend = last / first if first > 0 else None
            if (
                trend is not None
                and trend > RISING_FACTOR
                and repair_mid
                and row["repair_total"] >= repair_mid
            ):
                signals.append(
                    (
                        RISING,
                        f"{half} เดือนหลังซ่อม {last:,.0f} บาท ({trend:,.1f} เท่าของ {half} เดือนแรก)",
                    )
                )

        codes = {code for code, _ in signals}
        if len(signals) < MIN_SIGNALS or not codes & {OLD, COSTLY}:
            continue
        full_months_total = sum(per_month.get(m, 0.0) for m in months)
        # ค่าสั้นๆ ของแต่ละสัญญาณ (แสดงเป็นป้ายบนหน้าเว็บ)
        short = {
            OLD: f"{row['age']} ปี",
            COSTLY: f"{cost_ratio or 0:,.1f} เท่าของ{cost_scope}",
            FAILURE: f"{row['failure_count']} ครั้ง",
            DOWNTIME: f"{row['downtime_hours']:,.0f} ชม.",
            RISING: f"{trend or 0:,.1f} เท่า",
        }
        candidates.append(
            {
                "car_id": row["car_id"],
                "branch_company_id": str(row["branch_company_id"]),
                "label": f"{row['name'] or 'ไม่ระบุ'}:{row['code']}".rstrip(":"),
                "company": row["branch_company_name"] or "",
                "car_type_name": row["car_type_name"] or "",
                "brand": row["brand"] or "",
                "car_model": row["car_model"] or "",
                "age": row["age"],
                "repair_total": row["repair_total"],
                # ค่าซ่อมต่อปี (ประมาณ) จากค่าเฉลี่ยรายเดือนของเดือนที่จบแล้ว
                "annual_repair": full_months_total / len(months) * 12 if months else None,
                "repair_cost_per_hr": row["repair_cost_per_hr"] if row["work_total"] > 0 else None,
                "cost_ratio": cost_ratio,
                "failure_count": row["failure_count"],
                "downtime_hours": row["downtime_hours"],
                "trend": trend,
                "monthly": [per_month.get(m, 0.0) for m in months],
                "score": len(signals),
                "signals": [
                    {
                        "code": code,
                        "label": SIGNAL_LABELS[code],
                        "detail": detail,
                        "short": short[code],
                    }
                    for code, detail in signals
                ],
            }
        )

    candidates.sort(key=lambda c: (-c["score"], -(c["annual_repair"] or 0)))
    return {
        "car_count": len(car_rows),
        "unknown_age_count": sum(1 for r in car_rows if r["age"] is None),
        "candidate_count": len(candidates),
        "annual_repair": sum(c["annual_repair"] or 0 for c in candidates),
        "replace_age": REPLACE_AGE,
        "min_signals": MIN_SIGNALS,
        "signals": [
            {
                "code": code,
                "label": label,
                "count": sum(1 for c in candidates if any(s["code"] == code for s in c["signals"])),
            }
            for code, label in SIGNAL_LABELS.items()
        ],
        "cars": candidates[:limit],
    }
