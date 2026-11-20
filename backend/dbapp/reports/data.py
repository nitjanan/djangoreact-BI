"""รวบรวมตัวเลขของรายงาน (ใช้ฟังก์ชันเดียวกับหน้า dashboard ตัวเลขจึงตรงกัน)"""

from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Q

from dbapp.models import BaseBranchCompany, BaseCarDepartment, SummaryMaintenance
from dbapp.services.dashboard import (
    ALL_COMPANIES,
    MA_TYPE_BREAKDOWN,
    build_car_table,
    cal_mean,
    fuel_spec,
    last_synced_at,
    period_filter,
    repair_hours,
    to_gregorian,
    unit_noun,
)
from dbapp.services.open_jobs import build_open_jobs
from dbapp.services.watchlist import build_watchlist

from .period import BUDDHIST_ERA_OFFSET, MONTHS_SHORT_TH, shift_year

TOP_ROWS = 10
BREAKDOWN_ROWS = 15


def all_company_ids():
    return list(
        BaseBranchCompany.objects.exclude(code=ALL_COMPANIES)
        .order_by("id")
        .values_list("id", flat=True)
    )


def _date_range(field, start, end):
    """ช่วงวันที่ รวมแถวที่กรอกปีเป็น พ.ศ. (เช่น 2569) ด้วย"""
    be = (shift_year(start, BUDDHIST_ERA_OFFSET), shift_year(end, BUDDHIST_ERA_OFFSET))
    return Q(**{f"{field}__date__range": (start, end)}) | Q(**{f"{field}__date__range": be})


def breakdown_stats(base, start, end, with_rows=False):
    """ใบแจ้งซ่อมประเภท "ซ่อม": แจ้งในช่วงนี้กี่ใบ ปิดงานกี่ใบ เวลาซ่อมเฉลี่ยของใบที่ปิด"""
    qs = SummaryMaintenance.objects.filter(**base, ma_type=MA_TYPE_BREAKDOWN)
    reported = qs.filter(_date_range("reported_at", start, end))
    durations = [
        h
        for r, f in qs.filter(_date_range("finished_at", start, end)).values_list(
            "reported_at", "finished_at"
        )
        if (h := repair_hours(r, f)) is not None
    ]
    stats = {
        "reported": reported.count(),
        "closed": len(durations),
        "mttr": cal_mean(durations),
    }
    if with_rows:
        stats["rows"] = [
            {
                "reported_at": to_gregorian(r["reported_at"]),
                "code": r["car__code"] or "",
                "name": r["car__name"] or "",
                "company": r["branch_company__name"] or "",
                "broke_reason": r["broke_reason"] or "",
                "closed": r["finished_at"] is not None or bool(r["is_complete"]),
            }
            for r in reported.order_by("reported_at").values(
                "reported_at",
                "finished_at",
                "is_complete",
                "car__code",
                "car__name",
                "branch_company__name",
                "broke_reason",
            )[:BREAKDOWN_ROWS]
        ]
    return stats


def _kpi(key, label, unit, value, prev=None, last_year=None, digits=0, lower_is_better=True):
    return {
        "key": key,
        "label": label,
        "unit": unit,
        "value": value,
        "prev": prev,
        "last_year": last_year,
        "digits": digits,
        "lower_is_better": lower_is_better,
    }


def _monthly_kpis(period, cur, prev, last_year, fuel):
    """ตัวเลขรายเดือน: รายสัปดาห์เทียบไม่ได้ (ยอดสะสมยังไม่ครบเดือน) จึงไม่มีตัวเทียบ"""

    def pick(totals, key):
        if totals is None:
            return None
        # อัตราเชื้อเพลิง 0 = ไม่มีชั่วโมง/ระยะทางให้หาร ไม่ใช่ "ไม่ใช้น้ำมัน"
        if key == fuel["field"]:
            return totals[key] or None
        return totals[key]

    if period.is_weekly:
        prev = last_year = None
    return [
        _kpi(
            "repair",
            "ค่าซ่อม",
            "บาท",
            cur["repair_total"],
            pick(prev, "repair_total"),
            pick(last_year, "repair_total"),
        ),
        _kpi(
            "oil",
            "น้ำมัน",
            "ลิตร",
            cur["oil_total"],
            pick(prev, "oil_total"),
            pick(last_year, "oil_total"),
        ),
        _kpi(
            "work",
            "ชั่วโมงทำงาน",
            "ชม.",
            cur["work_total"],
            pick(prev, "work_total"),
            pick(last_year, "work_total"),
            lower_is_better=False,
        ),
        _kpi(
            "fuel_rate",
            "อัตราเชื้อเพลิง",
            fuel["unit"],
            pick(cur, fuel["field"]),
            pick(prev, fuel["field"]),
            pick(last_year, fuel["field"]),
            digits=2,
        ),
    ]


def _breakdown_kpis(cur, prev, last_year):
    return [
        _kpi("reported", "แจ้งซ่อม", "ใบ", cur["reported"], prev["reported"], last_year["reported"]),
        _kpi(
            "closed",
            "ซ่อมเสร็จ",
            "ใบ",
            cur["closed"],
            prev["closed"],
            last_year["closed"],
            lower_is_better=False,
        ),
        _kpi("mttr", "เวลาซ่อมเฉลี่ย", "ชม.", cur["mttr"], prev["mttr"], last_year["mttr"], 1),
    ]


def build_department(dep, period, company_ids, now):
    car_dep_id = dep.id
    noun = unit_noun(car_dep_id, False)
    fuel = fuel_spec(car_dep_id)
    month = range(period.month, period.month + 1)

    _, cur = build_car_table(car_dep_id, period.year, company_ids, None, month)
    prev = last_year = None
    if not period.is_weekly:
        prev_year, prev_month = period.prev_month
        _, prev = build_car_table(
            car_dep_id, prev_year, company_ids, None, range(prev_month, prev_month + 1)
        )
        _, last_year = build_car_table(car_dep_id, period.year - 1, company_ids, None, month)

    base = {"car_dep_id": car_dep_id, "branch_company_id__in": company_ids}
    breakdowns = breakdown_stats(base, period.start, period.end, with_rows=True)
    breakdowns_prev = breakdown_stats(base, period.prev_start, period.prev_end)
    breakdowns_last_year = breakdown_stats(base, period.last_year_start, period.last_year_end)

    # ตั้งแต่ต้นปีถึงเดือนของรายงาน: ใช้จัดอันดับรถ (เดือนเดียวข้อมูลน้อยเกินไป)
    ytd = range(1, period.month + 1)
    ytd_rows, _ = build_car_table(car_dep_id, period.year, company_ids, None, ytd)
    open_jobs = build_open_jobs(base, now=now)
    watchlist = build_watchlist(
        ytd_rows,
        {**base, **period_filter(period.year, ytd)},
        open_jobs,
        noun,
        fuel,
    )

    if not ytd_rows and not open_jobs["total"] and not breakdowns["reported"]:
        return None

    top_cost = sorted(
        (r for r in ytd_rows if r["work_total"] > 0 and r["repair_total"] > 0),
        key=lambda r: r["repair_cost_per_hr"],
        reverse=True,
    )[:TOP_ROWS]

    return {
        "id": car_dep_id,
        "name": dep.name,
        "noun": noun,
        "fuel": {"field": fuel["field"], "unit": fuel["unit"], "label": fuel["label"]},
        "car_count": len(ytd_rows),
        "monthly_kpis": _monthly_kpis(period, cur, prev, last_year, fuel),
        "breakdown_kpis": _breakdown_kpis(breakdowns, breakdowns_prev, breakdowns_last_year),
        "breakdowns": breakdowns["rows"],
        "breakdown_count": breakdowns["reported"],
        "open_jobs": {
            "total": open_jobs["total"],
            "car_count": open_jobs["car_count"],
            "immobile_car_count": open_jobs["immobile_car_count"],
            "stale_count": open_jobs["stale_count"],
            "stale_days": open_jobs["stale_days"],
            "jobs": open_jobs["jobs"][:TOP_ROWS],
        },
        "watchlist": {
            "count": len(watchlist["cars"]),
            "cars": watchlist["cars"][:TOP_ROWS],
        },
        "top_cost": [
            {
                "code": r["code"] or "",
                "name": r["name"] or "",
                "company": r["branch_company_name"] or "",
                "work_total": r["work_total"],
                "repair_total": r["repair_total"],
                "repair_cost_per_hr": r["repair_cost_per_hr"],
            }
            for r in top_cost
        ],
    }


def dashboard_url(period, company_code, car_dep=None, whole_year=False):
    """ลิงก์หน้า dashboard ที่ตั้งตัวกรองตรงกับรายงาน (ยังไม่ login จะไปหน้า login แล้วกลับมาที่นี่)

    whole_year: ต้นปีถึงเดือนของรายงาน (ม.ค. – เดือนนี้)
    """
    params = {
        "company": company_code,
        "year": period.year,
        "month_from": 1 if whole_year else period.month,
        "month_to": period.month,
    }
    if car_dep is not None:
        params["car_dep"] = car_dep
    return f"{settings.FRONTEND_URL}/?{urlencode(params)}"


def build_report(period, company_ids=None, now=None):
    """company_ids=None = ทุกบริษัท"""
    now = now or datetime.now()
    if not company_ids:
        company_ids = all_company_ids()
    rows = list(
        BaseBranchCompany.objects.filter(id__in=company_ids)
        .order_by("id")
        .values_list("name", "code")
    )
    companies = [name for name, _ in rows]
    # บริษัทเดียวเปิดตรงบริษัทนั้น หลายบริษัทเปิด "ทั้งหมด" (ตามสิทธิ์ของคนที่ login)
    company_code = rows[0][1] if len(rows) == 1 else ALL_COMPANIES
    departments = [
        section
        for dep in BaseCarDepartment.objects.order_by("id")
        if (section := build_department(dep, period, company_ids, now))
    ]
    for d in departments:
        d["url"] = dashboard_url(period, company_code, d["id"])
    return {
        "period": period,
        "company_ids": list(company_ids),
        "companies": [c for c in companies if c],
        "all_companies": set(company_ids) == set(all_company_ids()),
        "departments": departments,
        "url": dashboard_url(period, company_code),
        "year_url": dashboard_url(period, company_code, whole_year=True),
        "year_label": (
            f"ทั้งปี {period.year + BUDDHIST_ERA_OFFSET} (ม.ค. – {MONTHS_SHORT_TH[period.month - 1]})"
        ),
        "generated_at": now,
        "last_synced_at": last_synced_at(),
    }
