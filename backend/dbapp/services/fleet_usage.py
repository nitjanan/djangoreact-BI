"""การใช้งานรถรายเดือนต่อคัน: น้ำมันผิดปกติ (เทียบกับตัวเอง) และรถที่ใช้งานน้อย

ใช้เป็นเหตุผล "น้ำมันพุ่ง" และ "ใช้งานน้อย" ใน "รถที่ต้องจับตา" (watchlist.py)
ต่างจากเกณฑ์อื่นที่เทียบรถแต่ละคันกับค่ากลางของรถคันอื่นทั้งช่วง ส่วนนี้ดูทีละเดือน:

- น้ำมันผิดปกติ: เดือนที่อัตราสิ้นเปลืองสูงกว่าค่ากลางของรถคันเดียวกันเกิน FUEL_SPIKE_FACTOR เท่า
  (รถแต่ละคันใช้น้ำมันไม่เท่ากันตามงาน จึงเทียบกับตัวเอง ใช้หาน้ำมันรั่ว/เครื่องผิดปกติ/บันทึกผิด)
- ใช้งานน้อย: ชั่วโมงทำงานเฉลี่ยต่อเดือนต่ำกว่า LOW_USE_FACTOR ของค่ากลางรถในตัวกรองเดียวกัน
  หรือไม่มีชั่วโมงทำงานติดกัน IDLE_STREAK เดือนขึ้นไปจนถึงเดือนล่าสุด (ควรย้ายไปใช้ที่อื่นหรือขาย)
"""

from statistics import median

from django.db.models import Case, F, FloatField, Sum, Value, When

from dbapp.models import SummaryCarJob, SummaryOil
from dbapp.services.dashboard import (
    MONTHS_TH,
    car_label,
    summary_work,
    work_source,
)
from dbapp.services.insights import FUEL_PER_HOUR, MIN_CARS_TO_COMPARE

FUEL_SPIKE_FACTOR = 1.3  # สูงกว่าค่ากลางของคันเดียวกันกี่เท่าจึงถือว่าผิดปกติ
FUEL_MIN_MONTHS = 3  # เดือนที่มีทั้งน้ำมันและงานอย่างน้อยกี่เดือน ค่ากลางของคันจึงเชื่อได้
# เดือนที่งานน้อยกว่าสัดส่วนนี้ของเดือนปกติของคันนั้น ตัวหารเล็กเกินไป อัตราแกว่งมาก ไม่นับ
FUEL_MIN_BASE_SHARE = 0.25

LOW_USE_FACTOR = 0.3
IDLE_STREAK = 2

CAR_FIELDS = ("car_id", "branch_company_id", "car__code", "car__name", "branch_company__name")


def _empty_month():
    return {"hours": 0.0, "oil": 0.0, "km": 0.0, "km_liters": 0.0}


def car_months(base_filter):
    """{(car_id, branch_company_id): {"car": {...}, "months": {เดือน: ยอดของเดือน}}}

    ชั่วโมงทำงานใช้แหล่งเดียวกับตารางรถ (work_source)
    """
    car_dep_id = base_filter.get("car_dep_id")
    base_filter = {**base_filter, "car_id__isnull": False}
    cars = {}

    def month_of(item):
        key = (item["car_id"], item["branch_company_id"])
        entry = cars.setdefault(
            key,
            {
                "car": {
                    "car_id": item["car_id"],
                    "branch_company_id": str(item["branch_company_id"]),
                    "label": car_label(item),
                    "company": item["branch_company__name"] or "",
                },
                "months": {},
            },
        )
        return entry["months"].setdefault(int(item["month"]), _empty_month())

    for item in (
        SummaryOil.objects.filter(**base_filter)
        .values(*CAR_FIELDS, "month")
        .annotate(
            oil=Sum("sum_liter"),
            km=Sum("sum_km"),
            km_liters=Sum(
                Case(
                    When(sum_km__gt=0, then=F("sum_liter")),
                    default=Value(0),
                    output_field=FloatField(),
                ),
                output_field=FloatField(),
            ),
        )
    ):
        m = month_of(item)
        m["oil"] = float(item["oil"] or 0)
        m["km"] = float(item["km"] or 0)
        m["km_liters"] = float(item["km_liters"] or 0)

    if work_source(car_dep_id)[0] is SummaryCarJob:
        work = SummaryCarJob.objects.filter(**base_filter)
    else:
        work = summary_work(car_dep_id, **base_filter)
    for item in work.values(*CAR_FIELDS, "month").annotate(total=Sum("hours")):
        month_of(item)["hours"] = float(item["total"] or 0)

    return cars


def _rate(month, fuel):
    """(อัตราสิ้นเปลือง, ตัวหาร) ของเดือน หรือ None ถ้าคำนวณไม่ได้"""
    if fuel["base"] == "km_total":
        base, liters = month["km"], month["km_liters"]
    else:
        base, liters = month["hours"], month["oil"]
    if base <= 0 or liters <= 0:
        return None
    return liters / base, base


def build_fuel_anomalies(cars, months, fuel=FUEL_PER_HOUR):
    """เดือนที่รถใช้น้ำมันสูงกว่าปกติของตัวเอง

    cars: ผลของ car_months · months: เดือนในช่วงที่เลือก
    extra_liters = ลิตรที่ใช้เกินจากอัตราปกติของคันนั้น (ประมาณการ)
    """
    flagged = []
    for entry in cars.values():
        rates = {m: r for m in months if (r := _rate(entry["months"].get(m, _empty_month()), fuel))}
        if len(rates) < FUEL_MIN_MONTHS:
            continue
        typical_base = median(base for _, base in rates.values())
        usable = {m: r for m, r in rates.items() if r[1] >= typical_base * FUEL_MIN_BASE_SHARE}
        if len(usable) < FUEL_MIN_MONTHS:
            continue
        baseline = median(rate for rate, _ in usable.values())
        spikes = []
        for m, (rate, base) in sorted(usable.items()):
            if rate > baseline * FUEL_SPIKE_FACTOR:
                spikes.append(
                    {
                        "month": m,
                        "label": MONTHS_TH[m - 1],
                        "rate": rate,
                        "ratio": rate / baseline,
                        "extra_liters": (rate - baseline) * base,
                    }
                )
        if spikes:
            flagged.append(
                {
                    **entry["car"],
                    "baseline": baseline,
                    "rates": [usable[m][0] if m in usable else None for m in months],
                    "spikes": spikes,
                    "extra_liters": sum(s["extra_liters"] for s in spikes),
                }
            )

    flagged.sort(key=lambda c: c["extra_liters"], reverse=True)
    return {
        "unit": fuel["unit"],
        "factor": FUEL_SPIKE_FACTOR,
        "labels": [MONTHS_TH[m - 1] for m in months],
        "car_count": len(flagged),
        "extra_liters": sum(c["extra_liters"] for c in flagged),
        "cars": flagged,
    }


def build_low_use(cars, months):
    """รถที่ใช้งานน้อย

    months: เดือนที่จบแล้ว (ไม่รวมเดือนปัจจุบันที่ยังไม่จบ ไม่งั้นทุกคันดูใช้งานน้อย)
    รถหลายคันไม่ได้บันทึกชั่วโมงเลยแต่ยังเติมน้ำมัน จึงแยกเป็นสองเกณฑ์
    - จอดนิ่ง: ไม่มีทั้งชั่วโมงทำงานและการเติมน้ำมันติดกัน IDLE_STREAK เดือนจนถึงเดือนล่าสุด
    - ชั่วโมงต่ำ: เฉพาะรถที่บันทึกชั่วโมง ชั่วโมงเฉลี่ยต่อเดือนต่ำกว่า LOW_USE_FACTOR ของค่ากลาง
    """
    months = list(months)
    rows = []
    for entry in cars.values():
        data = [entry["months"].get(m, _empty_month()) for m in months]
        hours = [d["hours"] for d in data]
        streak = 0
        for d in reversed(data):
            if d["hours"] > 0 or d["oil"] > 0:
                break
            streak += 1
        rows.append(
            {
                **entry["car"],
                "hours": hours,
                "oil": [d["oil"] for d in data],
                "avg_hours": sum(hours) / len(hours) if hours else 0.0,
                "records_hours": any(h > 0 for h in hours),
                "idle_months": sum(1 for d in data if d["hours"] <= 0 and d["oil"] <= 0),
                "idle_streak": streak,
            }
        )

    with_hours = [r for r in rows if r["records_hours"]]
    mid = (
        median(r["avg_hours"] for r in with_hours)
        if len(with_hours) >= MIN_CARS_TO_COMPARE
        else None
    )
    low = []
    for r in rows:
        r["ratio"] = r["avg_hours"] / mid if mid and r["records_hours"] else None
        r["idle"] = r["idle_streak"] >= IDLE_STREAK
        r["low_hours"] = r["ratio"] is not None and r["ratio"] < LOW_USE_FACTOR
        if months and (r["idle"] or r["low_hours"]):
            low.append(r)
    low.sort(key=lambda r: (-r["idle_streak"], r["avg_hours"]))
    return {
        "labels": [MONTHS_TH[m - 1] for m in months],
        "median_hours": mid,
        "factor": LOW_USE_FACTOR,
        "idle_streak": IDLE_STREAK,
        "car_count": len(rows),
        "hours_car_count": len(with_hours),
        "idle_count": sum(1 for r in low if r["idle"]),
        "low_hours_count": sum(1 for r in low if r["low_hours"]),
        "cars": low,
    }
