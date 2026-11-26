"""คาดการณ์ค่าซ่อมและน้ำมัน เดือนนี้และเดือนหน้า

ข้อมูลมีแค่ปีปัจจุบัน ยังเทียบฤดูกาลกับปีก่อนไม่ได้ จึงใช้วิธีที่อธิบายง่าย
- คาดการณ์ = ค่าเฉลี่ย BASE_MONTHS เดือนล่าสุดที่จบแล้ว
- ช่วงที่น่าจะเป็น = ต่ำสุด-สูงสุดของ RANGE_MONTHS เดือนล่าสุดที่จบแล้ว
- เดือนนี้แสดงยอดที่บันทึกแล้วด้วย แต่ไม่คำนวณ "ถ้าใช้ต่อในอัตรานี้" เพราะเอกสารค่าใช้จ่าย
  ส่วนใหญ่เข้าระบบช่วงปลายเดือน (ยอดกลางเดือนต่ำกว่าจริงมาก)
คำนวณเฉพาะตอนดูปีปัจจุบันถึงเดือนปัจจุบัน (ไม่งั้นคืน None)
"""

from calendar import monthrange

from dbapp.services.dashboard import MONTHS_TH

BASE_MONTHS = 3
RANGE_MONTHS = 6


def _series(values, full_months, current):
    base = [values.get(m, 0.0) for m in full_months[-BASE_MONTHS:]]
    window = [values.get(m, 0.0) for m in full_months[-RANGE_MONTHS:]]
    expected = sum(base) / len(base)
    return {
        "expected": expected,
        "low": min(window),
        "high": max(window),
        "month_to_date": values.get(current, 0.0),
        "history": [values.get(m, 0.0) for m in full_months],
    }


def build_forecast(repair_by_month, oil_by_month, year, months, today):
    """repair_by_month / oil_by_month: {เดือน: ยอด} ของปีที่เลือก"""
    months = list(months)
    if year != today.year or months[-1] != today.month:
        return None
    full_months = [m for m in months if m < today.month]
    if len(full_months) < BASE_MONTHS:
        return None
    next_month = today.month % 12 + 1
    return {
        "labels": [MONTHS_TH[m - 1] for m in full_months],
        "current_label": MONTHS_TH[today.month - 1],
        "next_label": MONTHS_TH[next_month - 1],
        "day": today.day,
        "days_in_month": monthrange(today.year, today.month)[1],
        "base_months": BASE_MONTHS,
        "range_months": RANGE_MONTHS,
        "repair": _series(repair_by_month, full_months, today.month),
        "oil": _series(oil_by_month, full_months, today.month),
    }
