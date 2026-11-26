"""ดึงข้อมูลจาก webstock มาเก็บใน base_* / sum_* — ย้ายมาจาก views.py เดิม

ของเดิมมีฟังก์ชันซ้ำกัน 2 ชุด (createRepair / updateOrCreateRepair ฯลฯ) ต่างกันแค่ช่วงวันที่
ที่นี่รวมเป็นชุดเดียวที่รับ start_date, end_date และจะลบข้อมูลเก่าก็ต่อเมื่อ API ส่งข้อมูลมาแล้วเท่านั้น
"""

import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime

from dbapp.models import (
    BaseBranchCompany,
    BaseCar,
    BaseCarDepartment,
    BaseCarType,
    BaseRepairType,
    SummaryCarDep,
    SummaryCarJob,
    SummaryMaintenance,
    SummaryMaintenancePart,
    SummaryOil,
    SummaryRepair,
    SummaryRepairDoc,
    SummaryUnmatched,
    SummaryWork,
)

from .external_api import get_api_data, get_base_url
from .maintenance_stage import job_stage

logger = logging.getLogger(__name__)

# ข้อมูลสรุปเริ่มเก็บตั้งแต่ต้นปี 2026
SYNC_START_DATE = date(2026, 1, 1)


def _month_start(item):
    return date(int(item["year"]), int(item["month"]), 1)


def _delete_range(model, start_date, end_date):
    model.objects.filter(summary_date__range=(start_date, end_date)).delete()


# ---------------------------------------------------------------- base data


def _sync_simple_base(model, path, build_defaults):
    data = get_api_data(f"{get_base_url()}{path}")
    if not data:
        return False

    for item in data:
        try:
            with transaction.atomic():
                model.objects.update_or_create(id=item["id"], defaults=build_defaults(item))
        except Exception:
            logger.exception("sync %s id=%s failed", model.__name__, item.get("id"))
    return True


CAR_DETAIL_FIELDS = ("start_year", "brand", "car_model")


def sync_base_data():
    # summary มี FK ไป base ต้องโหลด base ก่อนเสมอ
    return {
        "car_type": _sync_simple_base(
            BaseCarType, "/exp/basecartype/api/", lambda i: {"name": i["name"]}
        ),
        "repair_type": _sync_simple_base(
            BaseRepairType, "/exp/baserepairtype/api/", lambda i: {"name": i["name"]}
        ),
        "car_department": _sync_simple_base(
            BaseCarDepartment, "/exp/basecardepartment/api/", lambda i: {"name": i["name"]}
        ),
        "car": _sync_simple_base(
            BaseCar,
            "/exp/basecar/api/",
            lambda i: {
                "code": i.get("code"),
                "name": i["name"],
                "car_dep_id": i["car_dep"],
                "car_type_id": i["car_type"],
                # webstock รุ่นเก่ายังไม่ส่ง 3 ช่องนี้ ถ้าไม่มี key ให้คงค่าเดิมไว้ ไม่เขียนทับเป็นค่าว่าง
                **{f: i[f] for f in CAR_DETAIL_FIELDS if f in i},
            },
        ),
    }


# ------------------------------------------------------------- summary data


def sync_car_dep(start_date, end_date):
    data = get_api_data(f"{get_base_url()}/all/car/department/api/between/{start_date}/{end_date}/")
    for item in data:
        SummaryCarDep.objects.update_or_create(
            ext_id=item["id"],
            branch_company_id=item["branch_company"],
            defaults={"code": item["code"], "name": item["name"], "car_dep_id": item["car_dep"]},
        )
    return bool(data)


@transaction.atomic
def sync_repair(start_date, end_date):
    data = get_api_data(f"{get_base_url()}/all/exp/repair/api/between/{start_date}/{end_date}/")
    if not data:
        return False

    _delete_range(SummaryRepair, start_date, end_date)
    SummaryRepair.objects.bulk_create(
        [
            SummaryRepair(
                branch_company_id=item["branch_company"],
                summary_date=_month_start(item),
                month=int(item["month"]),
                year=int(item["year"]),
                month_th=item["month_th"],
                repair_name=item["rt_name"],
                amount=item["amount"],
                car_id=item["car_id"],
                car_code=item["car_code"],
                repair_id=item["note2"],
                car_dep_id=item["car_dep"],
            )
            for item in data
        ],
        batch_size=1000,
    )
    return True


@transaction.atomic
def sync_unmatched(start_date, end_date):
    """ค่าซ่อม/น้ำมันที่ webstock จับคู่กับ BaseCar ไม่ได้ (แสดงแยกในหน้า dashboard)"""
    data = get_api_data(f"{get_base_url()}/all/exp/unmatched/api/between/{start_date}/{end_date}/")
    if not data:
        return False

    _delete_range(SummaryUnmatched, start_date, end_date)
    SummaryUnmatched.objects.bulk_create(
        [
            SummaryUnmatched(
                branch_company_id=item["branch_company"],
                summary_date=_month_start(item),
                month=int(item["month"]),
                year=int(item["year"]),
                month_th=item["month_th"],
                remark=(item["remark"] or "")[:255],
                repair_amount=item["repair_amount"],
                oil_qty=item["oil_qty"],
            )
            for item in data
        ],
        batch_size=1000,
    )
    return True


@transaction.atomic
def sync_oil(start_date, end_date):
    url = f"{get_base_url()}/all/exp/oil/by/month/api/between/{start_date}/{end_date}/"
    data = get_api_data(url)
    if not data:
        return False

    _delete_range(SummaryOil, start_date, end_date)
    SummaryOil.objects.bulk_create(
        [
            SummaryOil(
                branch_company_id=item["branch_company"],
                summary_date=_month_start(item),
                month=item["month"],
                year=item["year"],
                month_th=item["month_th"],
                car_dep_id=item["car_dep"],
                car_id=item["car_id"],
                sum_liter=item["sum_liter"],
                sum_km=item["sum_km"],
                liter_per_km=item["liter_per_km"],
            )
            for item in data
        ],
        batch_size=1000,
    )
    return True


@transaction.atomic
def sync_work(start_date, end_date):
    data = get_api_data(f"{get_base_url()}/all/exp/by/month/api/between/{start_date}/{end_date}/")
    if not data:
        return False

    _delete_range(SummaryWork, start_date, end_date)
    SummaryWork.objects.bulk_create(
        [
            SummaryWork(
                branch_company_id=item["branch_company"],
                summary_date=_month_start(item),
                month=item["month"],
                year=item["year"],
                month_th=item["month_th"],
                car_dep_id=item["car_dep"],
                car_id=item["car_id"],
                sum_diff_mile=item["sum_diff_mile"],
                count_diff_time=item["count_diff_time"],
                meter_hours=item.get("meter_hours"),
                percent=item["percent"],
            )
            for item in data
        ],
        batch_size=1000,
    )
    return True


@transaction.atomic
def sync_car_jobs(start_date, end_date):
    """งานจากบันทึกการใช้รถ: ชั่วโมงทำงาน/ระยะทาง แยกแผนกค่าใช้จ่ายและรายละเอียดงาน"""
    base_url = settings.CARLOG_JOBS_API_BASE or get_base_url()
    data = get_api_data(
        f"{base_url}/all/carlog/jobs/api/between/{start_date}/{end_date}/", base_url
    )
    if not data:
        return False

    _delete_range(SummaryCarJob, start_date, end_date)
    SummaryCarJob.objects.bulk_create(
        [
            SummaryCarJob(
                summary_date=_month_start(item),
                year=item["year"],
                month=item["month"],
                branch_company_id=item["branch_company"],
                car_dep_id=item["car_dep"],
                car_id=item["car_id"],
                expense_dept_id=item["expense_dept_id"],
                expense_dept_name=item["expense_dept_name"],
                job=(item["job"] or "")[:255],
                hours=item["hours"],
                km=item["km"],
                trips=item["trips"],
                days=item["days"],
            )
            for item in data
        ],
        batch_size=1000,
    )
    return True


@transaction.atomic
def sync_repair_docs(start_date, end_date):
    """ใบจ่ายอะไหล่รายใบ: นับการซ่อมของรถที่ไม่มีใบแจ้งซ่อม (webstock รุ่นเก่าไม่มี API นี้ -> ข้าม)"""
    url = f"{get_base_url()}/all/exp/repair/docs/api/between/{start_date}/{end_date}/"
    data = get_api_data(url)
    if not data:
        return False

    # กัน FK error กรณี base ยังไม่ได้อัปเดต
    car_ids = set(BaseCar.objects.values_list("id", flat=True))
    car_dep_ids = set(BaseCarDepartment.objects.values_list("id", flat=True))
    company_ids = set(BaseBranchCompany.objects.values_list("id", flat=True))

    objs = []
    for item in data:
        docdat = date.fromisoformat(item["docdat"])
        objs.append(
            SummaryRepairDoc(
                docnum=item["docnum"][:30],
                docdat=docdat,
                summary_date=docdat.replace(day=1),
                year=docdat.year,
                month=docdat.month,
                remark=(item["remark"] or "")[:255],
                requester=(item["requester"] or "")[:150],
                repair_type=(item["repair_type"] or "")[:10] or None,
                repair_name=(item.get("repair_name") or "")[:255],
                ma_ref=(item["ma_ref"] or "")[:30] or None,
                amount=item["amount"] or 0,
                parts=item.get("parts") or [],  # webstock รุ่นก่อนเพิ่มรายการอะไหล่ไม่มีค่านี้
                car_id=item["car_id"] if item["car_id"] in car_ids else None,
                car_dep_id=item["car_dep"] if item["car_dep"] in car_dep_ids else None,
                branch_company_id=(
                    item["branch_company"] if item["branch_company"] in company_ids else None
                ),
            )
        )

    _delete_range(SummaryRepairDoc, start_date, end_date)
    SummaryRepairDoc.objects.bulk_create(objs, batch_size=1000)
    return True


@transaction.atomic
def sync_maintenance(today=None):
    today = today or date.today()
    # ย้อนไปต้นปีก่อนหน้า เผื่อใบแจ้งซ่อมที่ซ่อมข้ามปี
    start_date = date(today.year - 1, 1, 1)

    base_url = settings.MAINTENANCE_API_BASE or get_base_url()
    data = get_api_data(f"{base_url}/all/maintenance/api/between/{start_date}/{today}/", base_url)
    if not data:
        return False

    # เส้นทางเอกสาร (ใบขอเบิก/PR/PO) — webstock รุ่นเก่ายังไม่มี API นี้ ได้ [] ก็ยัง sync ส่วนอื่นต่อได้
    process = {
        str(p["id"]): p
        for p in get_api_data(
            f"{base_url}/all/maintenance/api/process/{start_date}/{today}/", base_url
        )
    }

    _delete_range(SummaryMaintenance, start_date, today)

    # กัน FK error กรณี base ยังไม่ได้อัปเดต
    car_ids = set(BaseCar.objects.values_list("id", flat=True))
    car_dep_ids = set(BaseCarDepartment.objects.values_list("id", flat=True))
    company_ids = set(BaseBranchCompany.objects.values_list("id", flat=True))

    objs = []
    for item in data:
        reported_at = parse_datetime(item["created"] or "")
        if reported_at is None:
            continue

        objs.append(
            SummaryMaintenance(
                ext_id=item["id"],
                summary_date=reported_at.date().replace(day=1),
                year=reported_at.year,
                month=reported_at.month,
                reported_at=reported_at,
                finished_at=parse_datetime(item["chief_update"] or ""),
                mile=item["mile"],
                ma_type=item["ma_type"],
                car_state=item["car_state"],
                is_complete=item["is_complete"],
                **_process_fields(process.get(str(item["id"])), reported_at, item),
                car_id=item["car_id"] if item["car_id"] in car_ids else None,
                car_dep_id=item["car_dep"] if item["car_dep"] in car_dep_ids else None,
                branch_company_id=(
                    item["branch_company"] if item["branch_company"] in company_ids else None
                ),
            )
        )

    SummaryMaintenance.objects.bulk_create(objs, batch_size=1000)
    _sync_parts(process.values())
    return True


def _sync_parts(processes):
    """อะไหล่ของใบแจ้งซ่อม = ใบจ่ายสินค้าภายใน (Express) เท่านั้น ไม่นับ parts.purchased (PO)
    เพราะของที่ซื้อมารับเข้าคลังแล้วออกใบจ่ายทุกครั้ง นับ PO ด้วยจะซ้ำ

    แทนที่เฉพาะเมื่อ webstock ต่อ Express ได้ (issued = None แปลว่าไม่รู้ เก็บของเดิมไว้)
    """
    issued = [
        p
        for p in processes
        if isinstance(p.get("parts"), dict) and p["parts"].get("issued") is not None
    ]
    if not issued:
        return

    Part = SummaryMaintenancePart
    Part.objects.filter(ext_id__in=[p["id"] for p in issued]).delete()

    def rows(process):
        for part in process["parts"]["issued"]:
            yield Part(
                ext_id=process["id"],
                docnum=part["docnum"][:30],
                docdat=part["docdat"],
                stkcod=(part["stkcod"] or "")[:40],
                name=(part["name"] or "")[:255],
                stktyp=part["stktyp"] or "",
                qty=part["qty"] or 0,
                unit=part["unit"] or "",
                amount=part["amount"] or 0,
            )

    Part.objects.bulk_create([obj for p in issued for obj in rows(p)], batch_size=1000)


def _process_fields(process, reported_at, item):
    if process is None:
        return {}
    fields = {
        "ref_no": process["ref_no"],
        "broke_reason": (process["broke_reason"] or "")[:255] or None,
        "approve_status": process["approve_status"],
    }
    # คำนวณขั้นเฉพาะใบที่ยังไม่ปิด (ปิดงานแล้วไม่ต้องรู้ว่าค้างที่ไหน)
    if not item["chief_update"] and not item["is_complete"]:
        fields.update(job_stage(process, reported_at))
    return fields


def _safe_step(name, func, *args):
    """รันทีละขั้น: ขั้นไหนพังให้ rollback เฉพาะขั้นนั้น (แต่ละขั้นเป็น atomic) แล้วทำขั้นถัดไปต่อ"""
    try:
        return func(*args)
    except Exception:
        logger.exception("sync step %s failed", name)
        return False


def sync_summary(start_date, end_date):
    return {
        "car_dep": _safe_step("car_dep", sync_car_dep, start_date, end_date),
        "repair": _safe_step("repair", sync_repair, start_date, end_date),
        "oil": _safe_step("oil", sync_oil, start_date, end_date),
        "work": _safe_step("work", sync_work, start_date, end_date),
        "car_jobs": _safe_step("car_jobs", sync_car_jobs, start_date, end_date),
        "maintenance": _safe_step("maintenance", sync_maintenance),
        "repair_docs": _safe_step("repair_docs", sync_repair_docs, start_date, end_date),
        "unmatched": _safe_step("unmatched", sync_unmatched, start_date, end_date),
    }


# --------------------------------------------------------------- entrypoints


def run_full_sync(today=None):
    """ปุ่ม "อัปเดตข้อมูล" บน dashboard (เดิม: updateValueAPI)"""
    today = today or date.today()
    return {"base": sync_base_data(), "summary": sync_summary(SYNC_START_DATE, today)}


def run_recent_summary_sync(today=None, months=3):
    """อัปเดตข้อมูลสรุปย้อนหลัง N เดือน (เดิม: update_summary_from_api)"""
    today = today or date.today()
    start_date = (today - relativedelta(months=months)).replace(day=1)
    return sync_summary(start_date, today)


def run_daily_sync(today=None, months=3):
    """งานอัปเดตอัตโนมัติทุกวัน: base ก่อน (รถคันใหม่ต้องมีก่อนผูกข้อมูลสรุป) แล้วสรุปย้อนหลัง N เดือน

    ใบแจ้งซ่อมดึงตั้งแต่ต้นปีก่อนเสมอ (ดู sync_maintenance) ไม่ขึ้นกับ N
    """
    return {"base": sync_base_data(), "summary": run_recent_summary_sync(today, months)}
