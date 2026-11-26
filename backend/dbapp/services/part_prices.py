"""ราคาอะไหล่ที่เปลี่ยนไป: ราคาต่อหน่วยครั้งแรกเทียบครั้งล่าสุด ของรหัสสินค้าเดียวกัน

ใช้ใบจ่ายสินค้าภายใน (SummaryRepairDoc.parts) ซึ่งมีทุกใบ ไม่ขึ้นกับว่าคลังกรอกเลขที่ใบแจ้งซ่อมหรือไม่
ราคาต่อหน่วย = มูลค่า / จำนวน ของวันที่จ่าย (วันเดียวกันหลายรายการใช้ค่าเฉลี่ยถ่วงจำนวน)
ราคาเดิม/ล่าสุด = ค่ากลางของ EDGE_POINTS วันแรก/วันล่าสุด (ไม่ซ้อนกัน)
ไม่เทียบรายการที่ราคาแกว่งเกิน MAX_SPREAD เท่า (ค่าแรง จ้างเหมา ฯลฯ ราคาขึ้นกับงาน)
ดูย้อนไปถึงต้นปีก่อนหน้า เพื่อให้มีราคาเดิมไว้เทียบ แต่แสดงเฉพาะอะไหล่ที่จ่ายในช่วงที่เลือก
impact = ส่วนต่างราคาต่อหน่วย x จำนวนที่ใช้ในช่วงที่เลือก (จ่ายเพิ่มเพราะราคาเปลี่ยน โดยประมาณ)
"""

from statistics import median

from django.db.models import Q

from dbapp.models import SummaryRepairDoc
from dbapp.services.dashboard import PERIOD_KEYS
from dbapp.services.parts import is_part

MIN_CHANGE = 0.05  # เปลี่ยนน้อยกว่า 5% ถือว่าราคาเดิม (ปัดเศษ/ต้นทุนเฉลี่ยแกว่งเล็กน้อย)
# ราคาสูงสุด/ต่ำสุดห่างกันเกินนี้ = ไม่ใช่สินค้าราคามาตรฐาน (ค่าแรง/จ้างทำ ราคาตามงาน) ไม่เทียบ
MAX_SPREAD = 2.0
# ราคาเดิม/ราคาล่าสุด = ค่ากลางของการจ่าย N ครั้งแรก/ครั้งล่าสุด (กันครั้งเดียวที่ผิดปกติ)
EDGE_POINTS = 3
TOP_PARTS = 15
MAX_POINTS = 24


def build_part_prices(base_filter, year, months):
    scope = {k: v for k, v in base_filter.items() if k not in PERIOD_KEYS}
    docs = (
        SummaryRepairDoc.objects.filter(
            Q(year=year - 1) | Q(year=year, month__lte=months[-1]), **scope
        )
        .exclude(parts=[])
        .values("docdat", "year", "month", "parts")
        .order_by("docdat")
    )

    items = {}
    for d in docs:
        in_period = d["year"] == year and months[0] <= d["month"] <= months[-1]
        for p in d["parts"]:
            qty, amount = float(p.get("qty") or 0), float(p.get("amount") or 0)
            code = (p.get("stkcod") or "").strip()
            if not code or qty <= 0 or amount <= 0 or not is_part(p.get("stktyp")):
                continue
            item = items.setdefault(
                code.upper(),
                {"stkcod": code, "name": "", "unit": "", "days": {}, "period_qty": 0.0},
            )
            item["name"] = item["name"] or p.get("name") or ""
            item["unit"] = item["unit"] or p.get("unit") or ""
            day = item["days"].setdefault(d["docdat"], [0.0, 0.0])
            day[0] += qty
            day[1] += amount
            if in_period:
                item["period_qty"] += qty

    rows = []
    compared = 0
    for item in items.values():
        if item["period_qty"] <= 0 or len(item["days"]) < 2:
            continue
        points = [(day, amount / qty) for day, (qty, amount) in sorted(item["days"].items())]
        prices = [price for _, price in points]
        if max(prices) > min(prices) * MAX_SPREAD:
            continue
        compared += 1
        edge = min(EDGE_POINTS, len(points) // 2)
        first, last = median(prices[:edge]), median(prices[-edge:])
        change = (last - first) / first
        if abs(change) < MIN_CHANGE:
            continue
        rows.append(
            {
                "stkcod": item["stkcod"],
                "name": item["name"],
                "unit": item["unit"],
                "first_date": points[0][0],
                "first_price": first,
                "last_date": points[-1][0],
                "last_price": last,
                "change": change * 100,
                "period_qty": item["period_qty"],
                "impact": (last - first) * item["period_qty"],
                "prices": [price for _, price in points[-MAX_POINTS:]],
            }
        )

    up = sorted((r for r in rows if r["change"] > 0), key=lambda r: r["impact"], reverse=True)
    down = sorted((r for r in rows if r["change"] < 0), key=lambda r: r["impact"])
    return {
        "compared": compared,
        "up_count": len(up),
        "down_count": len(down),
        "impact": sum(r["impact"] for r in rows),
        "min_change": MIN_CHANGE * 100,
        "up": up[:TOP_PARTS],
        "down": down[:TOP_PARTS],
    }
