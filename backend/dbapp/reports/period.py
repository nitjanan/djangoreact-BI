"""ช่วงเวลาของรายงาน

- รายสัปดาห์: จันทร์-อาทิตย์ของสัปดาห์ที่แล้ว เทียบกับสัปดาห์ก่อนหน้า
- รายเดือน: เดือนที่แล้วทั้งเดือน เทียบกับเดือนก่อนหน้า

ค่าซ่อม/น้ำมัน/ชั่วโมงทำงานในฐานข้อมูลเก็บเป็นรายเดือน รายงานรายสัปดาห์จึงแสดงเป็น
"ยอดสะสมเดือนนี้" ส่วนการแจ้งซ่อม/ปิดงานมีวันที่จริง นับรายสัปดาห์ได้
"""

from dataclasses import dataclass
from datetime import date, timedelta

WEEKLY = "weekly"
MONTHLY = "monthly"
FREQUENCIES = (WEEKLY, MONTHLY)

MONTHS_SHORT_TH = [
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]  # fmt: skip
MONTHS_TH = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]  # fmt: skip
BUDDHIST_ERA_OFFSET = 543


def thai_date(d):
    return f"{d.day} {MONTHS_SHORT_TH[d.month - 1]} {d.year + BUDDHIST_ERA_OFFSET}"


def thai_range(start, end):
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day}–{thai_date(end)}"
    if start.year == end.year:
        return f"{start.day} {MONTHS_SHORT_TH[start.month - 1]} – {thai_date(end)}"
    return f"{thai_date(start)} – {thai_date(end)}"


def thai_month(year, month):
    return f"{MONTHS_TH[month - 1]} {year + BUDDHIST_ERA_OFFSET}"


def shift_year(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 ก.พ.
        return d.replace(year=d.year + years, day=28)


@dataclass(frozen=True)
class ReportPeriod:
    frequency: str
    start: date  # วันแรกของช่วง
    end: date  # วันสุดท้าย (รวมวันนี้ด้วย)
    prev_start: date
    prev_end: date
    # ตัวเลขรายเดือน (ค่าซ่อม น้ำมัน ชั่วโมง): ปี + เดือน
    year: int
    month: int

    @property
    def is_weekly(self):
        return self.frequency == WEEKLY

    @property
    def title(self):
        return "สรุปรายงานประจำสัปดาห์" if self.is_weekly else "สรุปรายงานประจำเดือน"

    @property
    def label(self):
        if self.is_weekly:
            return thai_range(self.start, self.end)
        return thai_month(self.year, self.month)

    @property
    def prev_name(self):
        return "สัปดาห์ก่อน" if self.is_weekly else "เดือนก่อน"

    @property
    def last_year_start(self):
        # รายสัปดาห์: ถอย 52 สัปดาห์ ได้วันจันทร์-อาทิตย์เหมือนกัน
        return self.start - timedelta(weeks=52) if self.is_weekly else shift_year(self.start, -1)

    @property
    def last_year_end(self):
        return self.end - timedelta(weeks=52) if self.is_weekly else shift_year(self.end, -1)

    @property
    def monthly_label(self):
        """ป้ายของตัวเลขรายเดือน"""
        if self.is_weekly:
            return f"ยอดสะสมเดือน{thai_month(self.year, self.month)} ถึง {thai_date(self.end)}"
        return f"เดือน{thai_month(self.year, self.month)}"

    @property
    def prev_month(self):
        """(ปี, เดือน) ก่อนหน้า สำหรับเทียบตัวเลขรายเดือน (เฉพาะรายงานรายเดือน)"""
        return (self.year, self.month - 1) if self.month > 1 else (self.year - 1, 12)


def report_period(frequency, today):
    """ช่วงที่จบก่อน today (รันวันจันทร์ = สัปดาห์ที่แล้ว, รันวันที่ 1 = เดือนที่แล้ว)"""
    if frequency == WEEKLY:
        end = today - timedelta(days=today.weekday() + 1)  # วันอาทิตย์ที่ผ่านมา
        start = end - timedelta(days=6)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=6)
    elif frequency == MONTHLY:
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
    else:
        raise ValueError(f"frequency ต้องเป็น {' หรือ '.join(FREQUENCIES)}")
    return ReportPeriod(frequency, start, end, prev_start, prev_end, end.year, end.month)
