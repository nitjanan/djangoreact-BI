"""เทียบยี่ห้อ/รุ่น ภายในชนิดรถเดียวกัน

รวมแถวของตารางรถ (ตัวกรองเดียวกัน) เป็นกลุ่ม ชนิดรถ + ยี่ห้อ + รุ่น
ค่าต่อชั่วโมง/ต่อกม. คิดจากผลรวมของกลุ่ม (ไม่ใช่เฉลี่ยของแต่ละคัน)
คันที่ทำงานน้อยจึงไม่ดึงค่าของทั้งรุ่นให้เพี้ยน

ค่าต่อชั่วโมง (ต้นทุนซ่อม, ลิตร/ชม.) นับเฉพาะคันที่ชั่วโมงทำงาน > 0
คันที่ชั่วโมงติดลบ (เลขมิเตอร์ถูกรีเซ็ต) หรือไม่มีชั่วโมง ถ้านับรวมจะทำให้ทั้งรุ่นเพี้ยน

เทียบข้ามชนิดรถไม่ได้ (รถขุดกับรถตักใช้งานต่างกัน) จึงคิด vs_type
เทียบกับค่าของทั้งชนิดรถนั้น ซึ่งรวมคันที่ยังไม่ได้กรอกยี่ห้อด้วย
"""

import re

from dbapp.services.dashboard import cal_mean, cal_mtbf

MIN_CARS = 3  # รุ่นที่มีรถน้อยกว่านี้ หน้าเว็บเตือนว่ายังสรุปไม่ได้
NO_TYPE = "ไม่ระบุชนิด"


def _clean(value):
    return " ".join((value or "").split())


def _key(value):
    """กรอกต่างกันแค่ช่องว่าง/ขีด/วงเล็บ/ตัวพิมพ์ นับเป็นรุ่นเดียวกัน (MS25 = MS 25, D-Max = D - Max)"""
    return re.sub(r"[\W_]+", "", value.upper())


class _Group:
    def __init__(self):
        self.car_ids = set()
        self.ages = {}
        self.repair_total = 0.0  # ค่าซ่อมทุกคัน (แสดงเป็นยอดรวม)
        # เฉพาะคันที่ชั่วโมง > 0 สำหรับค่าต่อชั่วโมง
        self.work = self.repair = self.oil = 0.0
        self.km = self.km_liters = 0.0
        self.failures = 0
        self.percent_ma = []

    def add(self, row):
        self.car_ids.add(row["car_id"])
        if row["age"] is not None:
            self.ages[row["car_id"]] = row["age"]
        self.repair_total += row["repair_total"]
        if row["work_total"] > 0:
            self.work += row["work_total"]
            self.repair += row["repair_total"]
            self.oil += row["oil_total"]
        self.km += row["km_total"]
        # km_liters ถูกตัดออกจากแถวไปแล้ว คิดกลับจาก ลิตร/กม. ของคันนั้น
        self.km_liters += row["liter_per_km"] * row["km_total"]
        self.failures += row["failure_count"]
        if row["percent_ma"] > 0:
            self.percent_ma.append(row["percent_ma"])

    def cost_per_hr(self):
        return self.repair / self.work if self.work > 0 else None

    def fuel(self, field):
        if field == "liter_per_km":
            return self.km_liters / self.km if self.km > 0 else None
        return self.oil / self.work if self.work > 0 else None

    def metrics(self, fuel_field):
        return {
            "cars": len(self.car_ids),
            "avg_age": cal_mean(list(self.ages.values())),
            "repair_cost_per_hr": self.cost_per_hr(),
            "fuel": self.fuel(fuel_field),
            "mtbf": cal_mtbf(self.work, self.failures),
            "percent_ma": cal_mean(self.percent_ma),
        }


def _group(rows):
    group = _Group()
    for r in rows:
        group.add(r)
    return group


def _model_key(row):
    return (row["car_type_id"], _key(_clean(row["brand"])), _key(_clean(row["car_model"])))


def build_model_benchmark(car_rows, selected, fuel):
    """รถที่เลือก เทียบกับคันอื่นรุ่นเดียวกัน และคันอื่นในชนิดรถเดียวกัน (ไม่รวมคันนี้)

    None เมื่อยังไม่ได้เลือกรถ หรือรถคันนี้ยังไม่ได้กรอกยี่ห้อ
    """
    if not selected or not _clean(selected["brand"]):
        return None

    # คันเดียวกันที่อยู่หลายบริษัทไม่นับเป็นคันอื่น
    others = [r for r in car_rows if r["car_id"] != selected["car_id"]]
    peers = [r for r in others if _clean(r["brand"]) and _model_key(r) == _model_key(selected)]
    same_type = [r for r in others if r["car_type_id"] == selected["car_type_id"]]
    field = fuel["field"]
    return {
        "brand": _clean(selected["brand"]),
        "car_model": _clean(selected["car_model"]) or None,
        "car_type_name": selected["car_type_name"] or NO_TYPE,
        "car": _group([selected]).metrics(field),
        "model": _group(peers).metrics(field) if peers else None,
        "type": _group(same_type).metrics(field) if same_type else None,
    }


def build_model_comparison(car_rows, fuel):
    by_type = {}  # car_type -> _Group ของทั้งชนิด
    by_model = {}  # (car_type, BRAND, MODEL) -> (ชื่อที่แสดง, _Group)
    missing = set()

    for row in car_rows:
        type_key = row["car_type_id"]
        by_type.setdefault(type_key, _Group()).add(row)

        brand = _clean(row["brand"])
        if not brand:
            missing.add(row["car_id"])
            continue
        model = _clean(row["car_model"])
        # ตัวพิมพ์เล็ก/ใหญ่ต่างกัน (Sany / SANY) นับเป็นรุ่นเดียวกัน
        key = (type_key, _key(brand), _key(model))
        if key not in by_model:
            by_model[key] = (
                {
                    "car_type_id": type_key,
                    "car_type_name": row["car_type_name"] or NO_TYPE,
                    "brand": brand,
                    "car_model": model or None,
                },
                _Group(),
            )
        by_model[key][1].add(row)

    rows = []
    for (type_key, *_), (label, group) in by_model.items():
        type_cost = by_type[type_key].cost_per_hr()
        cost = group.cost_per_hr()
        rows.append(
            {
                **label,
                "cars": len(group.car_ids),
                "avg_age": cal_mean(list(group.ages.values())),
                "work_total": group.work,
                "repair_total": group.repair_total,
                "repair_cost_per_hr": cost,
                "type_repair_cost_per_hr": type_cost,
                "vs_type": cost / type_cost if cost is not None and type_cost else None,
                "fuel": group.fuel(fuel["field"]),
                "failure_count": group.failures,
                "mtbf": cal_mtbf(group.work, group.failures),
                "percent_ma": cal_mean(group.percent_ma),
            }
        )

    # ชนิดรถเรียงตามชื่อ ในชนิดเดียวกันรุ่นที่ต้นทุนซ่อมต่อชั่วโมงต่ำสุดขึ้นก่อน (ไม่มีชั่วโมงไว้ท้าย)
    rows.sort(
        key=lambda r: (
            r["car_type_name"] == NO_TYPE,
            r["car_type_name"],
            r["repair_cost_per_hr"] is None,
            r["repair_cost_per_hr"] or 0,
            r["brand"],
        )
    )
    total_cars = len({r["car_id"] for r in car_rows})
    return {
        "rows": rows,
        "min_cars": MIN_CARS,
        "total_cars": total_cars,
        "missing_cars": len(missing),
    }
