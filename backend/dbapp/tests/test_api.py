from datetime import date, datetime

import pytest
from django.contrib.auth.models import User
from django.core import mail
from rest_framework.test import APIClient

from dbapp.models import (
    BaseBranchCompany,
    BaseCar,
    BaseCarDepartment,
    BaseCarType,
    BaseVisible,
    SummaryCarJob,
    SummaryMaintenance,
    SummaryOil,
    SummaryRepair,
    SummaryRepairDoc,
    SummaryUnmatched,
    SummaryWork,
    UserProfile,
)

YEAR = 2026


@pytest.fixture
def data(db):
    all_co = BaseBranchCompany.objects.create(id="00", code="ALL", name="ทั้งหมด")
    co1 = BaseBranchCompany.objects.create(id="01", code="C01", name="สาขา 1")
    co2 = BaseBranchCompany.objects.create(id="02", code="C02", name="สาขา 2")
    other = BaseBranchCompany.objects.create(id="09", code="C09", name="สาขาอื่น")

    dep = BaseCarDepartment.objects.create(id=1, name="แผนกรถ")
    ctype = BaseCarType.objects.create(id=1, name="รถบรรทุก")
    car1 = BaseCar.objects.create(id=1, code="CAR1", name="รถ 1", car_dep=dep, car_type=ctype)
    car2 = BaseCar.objects.create(id=2, code="CAR2", name="รถ 2", car_dep=dep, car_type=ctype)

    user = User.objects.create_user("alice", "alice@example.com", "s3cret-pass!")
    profile = UserProfile.objects.create(user=user)
    profile.branch_company.set([all_co, co1, co2])
    profile.visible.add(BaseVisible.objects.create(name="MT"))

    def add(company, car, amount, month=1):
        common = dict(
            branch_company=company, car=car, car_dep=dep, year=YEAR, month=month,
            month_th="มกราคม", summary_date=date(YEAR, month, 1),
        )  # fmt: skip
        SummaryRepair.objects.create(**common, repair_name="เครื่องยนต์", amount=amount)
        SummaryOil.objects.create(**common, sum_liter=100, sum_km=50, liter_per_km=2)
        SummaryWork.objects.create(**common, sum_diff_mile=80, count_diff_time=10, percent=0)

    add(co1, car1, 1000)
    add(co2, car2, 500)
    add(other, car1, 99999)  # บริษัทที่ alice มองไม่เห็น

    SummaryMaintenance.objects.create(
        ext_id=1, branch_company=co1, car=car1, car_dep=dep, year=YEAR, month=1,
        summary_date=date(YEAR, 1, 1), ma_type="02",
        reported_at=datetime(YEAR, 1, 5, 8), finished_at=datetime(YEAR, 1, 5, 12),
    )  # fmt: skip
    return {"user": user}


@pytest.fixture
def client(data):
    c = APIClient()
    c.force_authenticate(data["user"])
    return c


def dashboard(client, **params):
    return client.get("/api/dashboard/", {"year": YEAR, "car_dep": 1, **params})


def test_requires_login(db):
    assert APIClient().get("/api/me/").status_code == 403


def test_login_with_csrf_then_me(data):
    c = APIClient(enforce_csrf_checks=True)
    creds = {"username": "alice", "password": "s3cret-pass!"}

    assert c.post("/api/auth/login/", creds, format="json").status_code == 403  # ไม่มี CSRF

    token = c.get("/api/auth/csrf/").cookies["fleet_csrftoken"].value
    res = c.post("/api/auth/login/", creds, format="json", HTTP_X_CSRFTOKEN=token)
    assert res.status_code == 200
    assert res.json()["default_company"] == "ALL"

    me = c.get("/api/me/").json()
    assert [co["code"] for co in me["companies"]] == ["ALL", "C01", "C02"]
    assert me["visible_tabs"] == ["MT"]


def test_wrong_password(data):
    res = APIClient().post("/api/auth/login/", {"username": "alice", "password": "x"})
    assert res.status_code == 400


def test_dashboard_all_companies_only_includes_visible_ones(client):
    res = dashboard(client, company="ALL")
    assert res.status_code == 200
    body = res.json()
    assert body["charts"]["repair_by_type"]["total"] == 1500
    assert len(body["car_table"]["rows"]) == 2
    assert body["car_types"] == [{"id": 1, "name": "รถบรรทุก"}]
    assert body["reliability"]["failure_count"] == 1
    assert body["reliability"]["mttr"] == 4
    assert body["open_jobs"]["total"] == 0
    assert body["watchlist"]["cars"] == []


def test_dashboard_single_company(client):
    body = dashboard(client, company="C02").json()
    assert body["charts"]["repair_by_type"]["total"] == 500
    assert body["reliability"]["failure_count"] == 0


def test_dashboard_forbidden_company(client):
    assert dashboard(client, company="C09").status_code == 403


def test_dashboard_select_car(client):
    body = dashboard(client, company="ALL", car_id=1, branch_company_id="01").json()
    assert body["selected_car"]["code"] == "CAR1"
    assert body["charts"]["repair_by_car"]["total"] == 1000
    heatmap = body["charts"]["repair_heatmap"]
    assert len(heatmap["rows"]) == 1
    assert heatmap["rows"][0]["company"]
    assert len(body["charts"]["repair_by_car"]["companies"]) == len(
        body["charts"]["repair_by_car"]["labels"]
    )
    assert len(heatmap["rows"][0]["data"]) == len(heatmap["labels"])
    assert sum(heatmap["rows"][0]["data"]) == 1000


def test_dashboard_cannot_select_car_of_hidden_company(client):
    body = dashboard(client, company="ALL", car_id=1, branch_company_id="09").json()
    assert body["selected_car"] is None
    assert body["filters"]["car_id"] is None
    assert body["charts"]["repair_by_type"]["total"] == 1500


def test_dashboard_requires_company(client):
    assert client.get("/api/dashboard/").status_code == 400


def test_lookups_exclude_department_4(client):
    BaseCarDepartment.objects.create(id=4, name="ซ่อน")
    names = [d["name"] for d in client.get("/api/car-departments/").json()]
    assert names == ["แผนกรถ", "อื่นๆ"]
    assert len(client.get("/api/cars/", {"code": "CAR2"}).json()) == 1


def test_password_reset_flow(data):
    c = APIClient()
    assert c.post("/api/auth/password-reset/", {"email": "alice@example.com"}).status_code == 200
    assert len(mail.outbox) == 1
    link = mail.outbox[0].body.split("reset-password/")[1].split()[0]
    uid, token = link.strip("/").split("/")

    res = c.post(
        "/api/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "new_password": "brand-new-Pass-77"},
    )
    assert res.status_code == 200
    assert c.login(username="alice", password="brand-new-Pass-77")

    # ใช้ token ซ้ำไม่ได้
    res = c.post(
        "/api/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "new_password": "another-Pass-88"},
    )
    assert res.status_code == 400


def test_sync_requires_superuser(client, data, monkeypatch):
    from dbapp.services import sync

    monkeypatch.setattr(sync, "run_full_sync", lambda: {"base": {}, "summary": {}})
    assert client.post("/api/sync/").status_code == 403

    data["user"].is_superuser = True
    data["user"].save()
    res = client.post("/api/sync/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_update_summary_from_api_needs_token_and_returns_text(client, data, settings, monkeypatch):
    from dbapp.services import sync

    calls = []
    monkeypatch.setattr(
        sync,
        "run_daily_sync",
        lambda: calls.append(1) or {"base": {"car": True}, "summary": {"repair": False}},
    )
    url = "/api/update_summary_from_api/"
    settings.SYNC_TOKEN = ""
    assert client.get(url, HTTP_X_SYNC_TOKEN="").status_code == 403  # ยังไม่ตั้งรหัส: ปิด

    settings.SYNC_TOKEN = "s3cret"
    assert client.get(url, HTTP_X_SYNC_TOKEN="wrong").status_code == 403
    assert client.get(url, {"token": "s3cret"}).status_code == 403  # ไม่รับรหัสใน URL
    from django.contrib.auth import get_user_model

    superuser = get_user_model().objects.create_superuser("admin2", password="x")
    client.force_login(superuser)
    assert client.get(url).status_code == 403  # GET ไม่ใช้ session (กัน CSRF)
    assert calls == []
    res = client.get(url, HTTP_X_SYNC_TOKEN="s3cret")
    assert (res.status_code, res.content.decode()) == (200, "update summary from api success")
    assert len(calls) == 1

    # ดึงไม่ได้เลยสักขั้น: ไม่บอกว่าสำเร็จ
    monkeypatch.setattr(
        sync, "run_daily_sync", lambda: {"base": {"car": False}, "summary": {"repair": False}}
    )
    res = client.get(url, HTTP_X_SYNC_TOKEN="s3cret")
    assert res.status_code == 502 and "car, repair" in res.content.decode()


def test_daily_sync_runs_base_then_recent_summary(monkeypatch):
    from datetime import date

    from dbapp.services import sync

    order = []
    monkeypatch.setattr(sync, "sync_base_data", lambda: order.append("base") or {})
    monkeypatch.setattr(
        sync, "sync_summary", lambda start, end: order.append(("summary", start, end)) or {}
    )
    sync.run_daily_sync(today=date(2026, 11, 20))
    assert order == ["base", ("summary", date(2026, 8, 1), date(2026, 11, 20))]


def test_sync_without_webstock_config_explains_instead_of_500(client, data):
    # ไม่มี BaseAPI "webstock" -> บอกให้ไปตั้งค่า แทน error 500 ที่ไม่บอกอะไร
    data["user"].is_superuser = True
    data["user"].save()
    res = client.post("/api/sync/")
    assert res.status_code == 503
    assert "webstock" in res.json()["detail"]


def test_car_table_shows_start_year_brand_and_model(client):
    BaseCar.objects.filter(id=1).update(start_year=2019, brand="SANY", car_model="SY215C")
    rows = {r["code"]: r for r in dashboard(client, company="ALL").json()["car_table"]["rows"]}
    assert rows["CAR1"]["age"] == YEAR - 2019
    assert rows["CAR2"]["age"] is None
    assert rows["CAR1"]["car_type_name"] == "รถบรรทุก"
    assert (rows["CAR1"]["start_year"], rows["CAR1"]["brand"], rows["CAR1"]["car_model"]) == (
        2019,
        "SANY",
        "SY215C",
    )
    assert (rows["CAR2"]["start_year"], rows["CAR2"]["brand"], rows["CAR2"]["car_model"]) == (
        None,
        None,
        None,
    )


def test_sync_base_car_copies_start_year_brand_and_model(db, monkeypatch):
    from dbapp.services import sync

    cars = [
        {"id": 7, "code": "S20", "name": "รถจีน9", "car_dep": None, "car_type": None,
         "start_year": 2019, "brand": "SANY", "car_model": "SY215C"},
        # webstock ที่ยังไม่ได้อัปเดตไม่มี 3 ช่องนี้
        {"id": 8, "code": "S21", "name": "รถจีน10", "car_dep": None, "car_type": None},
    ]  # fmt: skip
    monkeypatch.setattr(sync, "get_base_url", lambda: "")
    monkeypatch.setattr(
        sync, "get_api_data", lambda url: cars if url == "/exp/basecar/api/" else []
    )

    assert sync.sync_base_data()["car"] is True
    car = BaseCar.objects.get(id=7)
    assert (car.start_year, car.brand, car.car_model) == (2019, "SANY", "SY215C")
    assert BaseCar.objects.get(id=8).brand is None

    # sync ซ้ำจาก webstock ที่ยังไม่ส่ง 3 ช่องนี้ ต้องไม่ล้างค่าเดิม แต่ยังอัปเดตช่องอื่น
    cars[:] = [{"id": 7, "code": "S20", "name": "รถจีน9 ใหม่", "car_dep": None, "car_type": None}]
    assert sync.sync_base_data()["car"] is True
    car = BaseCar.objects.get(id=7)
    assert car.name == "รถจีน9 ใหม่"
    assert (car.start_year, car.brand, car.car_model) == (2019, "SANY", "SY215C")

    # ส่ง key มาเป็น null = ตั้งใจล้างค่า
    cars[:] = [{**cars[0], "start_year": None, "brand": None, "car_model": None}]
    sync.sync_base_data()
    assert BaseCar.objects.get(id=7).brand is None


def test_sync_summary_continues_after_failed_step(monkeypatch):
    from dbapp.services import sync

    def boom(*args):
        raise ValueError("bad row")

    monkeypatch.setattr(sync, "sync_car_dep", lambda *a: True)
    monkeypatch.setattr(sync, "sync_repair", boom)
    monkeypatch.setattr(sync, "sync_oil", lambda *a: True)
    monkeypatch.setattr(sync, "sync_work", lambda *a: False)
    monkeypatch.setattr(sync, "sync_maintenance", lambda *a: True)
    monkeypatch.setattr(sync, "sync_unmatched", lambda *a: True)
    monkeypatch.setattr(sync, "sync_car_jobs", lambda *a: True)
    monkeypatch.setattr(sync, "sync_repair_docs", lambda *a: True)

    result = sync.sync_summary(None, None)
    assert result == {
        "car_dep": True,
        "repair": False,
        "oil": True,
        "work": False,
        "car_jobs": True,
        "maintenance": True,
        "repair_docs": True,
        "unmatched": True,
    }


def test_other_tab_shows_cars_without_department_and_unmatched_expenses(client):
    co1, co2, other = (BaseBranchCompany.objects.get(id=i) for i in ("01", "02", "09"))
    no_dep_car = BaseCar.objects.create(id=3, code="X1", name="ตาชั่ง")
    SummaryRepair.objects.create(
        branch_company=co1, car=no_dep_car, car_dep=None, year=YEAR, month=1,
        month_th="มกราคม", summary_date=date(YEAR, 1, 1), repair_name="อื่นๆ", amount=50,
    )  # fmt: skip

    def add(company, remark, amount, oil=0, month=1):
        SummaryUnmatched.objects.create(
            branch_company=company, year=YEAR, month=month, month_th="", remark=remark,
            summary_date=date(YEAR, month, 1), repair_amount=amount, oil_qty=oil,
        )  # fmt: skip

    add(co1, "ปุ๋ยแอมโมเนียมไนเตรท", 300, month=1)
    add(co1, "ปุ๋ยแอมโมเนียมไนเตรท", 200, month=2)  # รวมทั้งปีเป็นแถวเดียว
    add(co2, "ZX210LC", 700, oil=40)
    add(other, "บริษัทที่มองไม่เห็น", 99999)

    body = dashboard(client, company="ALL", car_dep=0).json()
    # รถที่ไม่มีแผนกอยู่ในตารางรถ ตัวเลขยังเป็นของรถจริงเท่านั้น
    assert [r["code"] for r in body["car_table"]["rows"]] == ["X1"]
    assert body["car_table"]["totals"]["repair_total"] == 50
    unmatched = body["unmatched"]
    assert [(r["remark"], r["repair_amount"]) for r in unmatched["rows"]] == [
        ("ZX210LC", 700),
        ("ปุ๋ยแอมโมเนียมไนเตรท", 500),
    ]
    assert unmatched["repair_total"] == 1200
    assert unmatched["oil_total"] == 40
    # ยอดรายเดือนรวมทั้งรถไม่มีแผนกและรายการที่จับคู่ไม่ได้: ม.ค. 50+300+700, ก.พ. 200
    assert body["charts"]["repair_by_month"]["series"] == [1050, 200]

    # แท็บแผนกปกติไม่มีรายการเหล่านี้
    normal = dashboard(client, company="ALL").json()
    assert normal["unmatched"]["rows"] == []
    assert normal["charts"]["repair_by_type"]["total"] == 1500


def test_repair_hours_handles_buddhist_year_and_typos():
    from datetime import datetime

    from dbapp.services.dashboard import repair_hours

    reported = datetime(2026, 9, 25, 10, 0)
    assert repair_hours(reported, datetime(2569, 9, 25, 13, 0)) == 3
    assert repair_hours(reported, datetime(2599, 9, 25, 13, 0)) is None
    assert repair_hours(reported, datetime(2026, 9, 25, 9, 0)) is None
    assert repair_hours(reported, None) is None


def _repair(company_id, car_id, amount, year=YEAR, month=1):
    SummaryRepair.objects.create(
        branch_company_id=company_id, car_id=car_id, car_dep_id=1, year=year, month=month,
        month_th="", summary_date=date(year, month, 1), repair_name="ช่วงล่าง", amount=amount,
    )  # fmt: skip


def test_dashboard_month_range(client):
    _repair("01", 1, 300, month=3)
    full = dashboard(client, company="ALL").json()
    assert full["charts"]["repair_by_type"]["total"] == 1800

    body = dashboard(client, company="ALL", month_from=3, month_to=3).json()
    assert (body["filters"]["month_from"], body["filters"]["month_to"]) == (3, 3)
    assert body["charts"]["repair_by_type"]["total"] == 300
    assert body["car_table"]["totals"]["repair_total"] == 300
    assert body["charts"]["repair_vs_work"]["labels"] == ["มีนาคม"]
    assert body["reliability"]["failure_count"] == 0  # ใบแจ้งซ่อมอยู่เดือน ม.ค.


def test_dashboard_month_range_start_after_end_is_clamped(client):
    body = dashboard(client, company="ALL", month_from=5, month_to=2).json()
    assert (body["filters"]["month_from"], body["filters"]["month_to"]) == (2, 2)


def test_dashboard_compares_with_same_months_last_year(client):
    _repair("01", 1, 400, year=YEAR - 1)
    _repair("01", 1, 9000, year=YEAR - 1, month=6)  # นอกช่วงที่เลือก
    _repair("09", 1, 7777, year=YEAR - 1)  # บริษัทที่มองไม่เห็น

    body = dashboard(client, company="ALL", month_from=1, month_to=3).json()
    compare = body["compare"]
    assert (compare["year"], compare["month_from"], compare["month_to"]) == (YEAR - 1, 1, 3)
    assert compare["has_data"] is True
    assert compare["repair_total"] == 400
    assert compare["totals"]["repair_total"] == 400

    # บริษัทที่ไม่มีข้อมูลปีก่อน
    empty = dashboard(client, company="C02", month_from=1, month_to=3).json()["compare"]
    assert empty["has_data"] is False
    assert empty["totals"] is None


def test_dashboard_unit_noun_is_department_name(client):
    assert dashboard(client, company="ALL").json()["filters"]["unit_noun"] == "แผนกรถ"
    other = dashboard(client, company="ALL", car_dep=0).json()["filters"]["unit_noun"]
    assert other == "รถ/เครื่องจักร"


def test_dashboard_last_synced_at_is_latest_summary_row(client):
    body = dashboard(client, company="ALL").json()
    latest = max(
        SummaryRepair.objects.latest("created_at").created_at,
        SummaryMaintenance.objects.latest("created_at").created_at,
    )
    assert body["last_synced_at"] == latest.isoformat()


def test_truck_department_uses_liters_per_km(client):
    truck = BaseCarDepartment.objects.create(id=2, name="รถบรรทุก")
    co1 = BaseBranchCompany.objects.get(id="01")
    t1 = BaseCar.objects.create(id=10, code="T1", name="รถบรรทุก 1", car_dep=truck)

    def oil(month, liters, km):
        SummaryOil.objects.create(
            branch_company=co1, car=t1, car_dep=truck, year=YEAR, month=month,
            month_th="", summary_date=date(YEAR, month, 1), sum_liter=liters, sum_km=km,
        )  # fmt: skip

    oil(1, 300, 1000)
    oil(2, 200, 1000)
    oil(3, 900, 0)  # เติมน้ำมันแต่ไม่ได้บันทึกไมล์ -> ไม่นับใน ลิตร/กม.

    body = dashboard(client, company="ALL", car_dep=2).json()
    assert (body["filters"]["fuel_field"], body["filters"]["fuel_unit"]) == (
        "liter_per_km",
        "ลิตร/กม.",
    )
    [row] = body["car_table"]["rows"]
    assert (row["oil_total"], row["km_total"], row["liter_per_km"]) == (1400, 2000, 0.25)
    assert body["car_table"]["totals"]["liter_per_km"] == 0.25

    # แท็บอื่นๆ (มีเครื่องจักรปน) ยังเทียบเป็น ลิตร/ชม.
    other = dashboard(client, company="ALL", car_dep=0).json()["filters"]
    assert (other["fuel_field"], other["fuel_unit"]) == ("fuel_rate", "ลิตร/ชม.")


def test_truck_hours_come_from_carlog_jobs_and_summarise_by_expense_department(client):
    truck = BaseCarDepartment.objects.create(id=2, name="รถบรรทุก")
    co1 = BaseBranchCompany.objects.get(id="01")
    t1 = BaseCar.objects.create(id=10, code="T1", name="รถบรรทุก 1", car_dep=truck)
    t2 = BaseCar.objects.create(id=11, code="T2", name="รถบรรทุก 2", car_dep=truck)
    common = dict(branch_company=co1, car_dep=truck, year=YEAR, month=1,
                  summary_date=date(YEAR, 1, 1))  # fmt: skip
    # เลขไมล์ 500 กม. ไม่ใช่ชั่วโมง -> ไม่ใช้เป็นชั่วโมงทำงานแล้ว แต่ยังใช้นับวัน
    SummaryWork.objects.create(**common, car=t1, sum_diff_mile=500, count_diff_time=2)

    def job(car, dept, name, hours, km=0, trips=1):
        SummaryCarJob.objects.create(
            **common, car=car, expense_dept_id=dept and dept[:2], expense_dept_name=dept,
            job=name, hours=hours, km=km, trips=trips, days=trips,
        )  # fmt: skip

    job(t1, "โรงโม่ 1", "หินใหญ่-เข้าโม่", 10, km=40, trips=2)
    job(t2, "โรงโม่ 1", "หินใหญ่-เข้าโม่", 4)
    job(t1, "เปิดหน้าดิน", "บรรทุกดิน", 2)
    job(t1, None, "วางบิล", 1)

    body = dashboard(client, company="ALL", car_dep=2).json()
    rows = {r["code"]: r for r in body["car_table"]["rows"]}
    assert rows["T1"]["work_total"] == 13
    assert rows["T1"]["percent_ma"] == 13 / (2 * 8) * 100  # มาตรฐาน 8 ชม./วัน
    assert rows["T2"]["work_total"] == 4
    assert body["charts"]["work_by_month"]["hours"][0] == 17

    jobs = body["jobs"]
    assert (jobs["hours"], jobs["km"], jobs["trips"]) == (17, 40, 5)
    names = [d["name"] for d in jobs["departments"]]
    assert names == ["โรงโม่ 1", "เปิดหน้าดิน", "ไม่ระบุแผนกค่าใช้จ่าย"]  # ไม่ระบุอยู่ท้าย
    crusher = jobs["departments"][0]
    assert (crusher["hours"], crusher["trips"], crusher["cars"]) == (14, 3, 2)
    assert crusher["jobs"] == [{"job": "หินใหญ่-เข้าโม่", "hours": 14, "km": 40, "trips": 3, "cars": 2}]

    # เลือกรถคันเดียว: เห็นเฉพาะงานของคันนั้น
    one = dashboard(client, company="ALL", car_dep=2, car_id=11, branch_company_id="01").json()
    assert one["jobs"]["hours"] == 4


def test_dashboard_years_only_from_visible_companies(client):
    _repair("01", 1, 1, year=2024)
    _repair("09", 1, 1, year=2019)
    years = dashboard(client, company="ALL").json()["filters"]["years"]
    assert {date.today().year, YEAR} <= set(years)
    assert 2024 in years
    assert 2019 not in years
    assert years == sorted(years, reverse=True)


def test_sync_car_jobs_uses_carlog_jobs_api_base(db, settings, monkeypatch):
    from dbapp.services import sync

    settings.CARLOG_JOBS_API_BASE = "http://local-webstock"
    calls = []
    monkeypatch.setattr(sync, "get_base_url", lambda: "http://prod")
    monkeypatch.setattr(
        sync, "get_api_data", lambda url, base_url=None: calls.append((url, base_url)) or []
    )

    sync.sync_car_jobs(date(YEAR, 1, 1), date(YEAR, 1, 31))
    assert calls == [
        (
            f"http://local-webstock/all/carlog/jobs/api/between/{YEAR}-01-01/{YEAR}-01-31/",
            "http://local-webstock",
        )
    ]


# ------------------------------------------- PM / downtime / สาขา / ประวัติรถ


def add_pm(ext_id, company_id="01", car_id=1, month=1, open_=False):
    SummaryMaintenance.objects.create(
        ext_id=ext_id, branch_company_id=company_id, car_id=car_id, car_dep_id=1, year=YEAR,
        month=month, summary_date=date(YEAR, month, 1), ma_type="04",
        reported_at=datetime(YEAR, month, 10, 8),
        finished_at=None if open_ else datetime(YEAR, month, 10, 10),
    )  # fmt: skip


def test_reliability_has_pm_ratio_and_downtime(client):
    add_pm(2)
    add_pm(3)
    rel = dashboard(client, company="ALL").json()["reliability"]

    assert rel["pm_count"] == 2
    assert rel["pm_ratio"] == pytest.approx(200 / 3)  # PM 2 ใบ จาก PM + ซ่อม 3 ใบ
    assert rel["downtime_hours"] == 4  # ใบซ่อม 1 ใบ 4 ชม. (PM ไม่นับ)
    assert rel["trend"]["pm"][0] == 2 and rel["trend"]["downtime"][0] == 4
    assert rel["top_downtime"]["labels"] == ["รถ 1:CAR1"]


def test_branch_compare_only_when_several_companies(client):
    body = dashboard(client, company="ALL").json()
    branches = {b["branch_company_name"]: b for b in body["branch_compare"]}
    assert set(branches) == {"สาขา 1", "สาขา 2"}  # สาขาที่ alice มองไม่เห็นไม่อยู่
    assert branches["สาขา 1"]["repair_total"] == 1000
    assert branches["สาขา 1"]["failure_count"] == 1 and branches["สาขา 2"]["failure_count"] == 0
    assert branches["สาขา 1"]["downtime_hours"] == 4

    assert dashboard(client, company="C01").json()["branch_compare"] == []


def test_car_history(client):
    add_pm(2, open_=True)
    res = client.get("/api/car-history/1/", {"branch_company_id": "01"})
    assert res.status_code == 200
    body = res.json()

    assert body["car"]["code"] == "CAR1"
    assert body["car"]["branch_company_name"] == "สาขา 1"
    # ไม่รวมค่าซ่อมของรถทะเบียนเดียวกันในบริษัทอื่น
    assert body["totals"]["repair_total"] == 1000
    assert body["totals"]["ticket_count"] == 2
    assert body["totals"]["open_count"] == 1
    assert body["totals"]["downtime_hours"] == 4
    assert [t["ma_type_name"] for t in body["tickets"]] == ["PM", "ซ่อม"]  # ใหม่ -> เก่า
    assert body["monthly"]["repair"] == [1000]


def test_car_history_checks_company_access(client):
    assert client.get("/api/car-history/1/", {"branch_company_id": "09"}).status_code == 403
    assert client.get("/api/car-history/999/", {"branch_company_id": "01"}).status_code == 404


def test_overlapping_repairs_count_downtime_once(client):
    # ใบที่สองเปิดระหว่างใบแรก (5 ม.ค. 08-12) จนถึง 14:00 -> รวม 08-14 = 6 ชม. ไม่ใช่ 4 + 4
    SummaryMaintenance.objects.create(
        ext_id=5, branch_company_id="01", car_id=1, car_dep_id=1, year=YEAR, month=1,
        summary_date=date(YEAR, 1, 1), ma_type="02",
        reported_at=datetime(YEAR, 1, 5, 10), finished_at=datetime(YEAR, 1, 5, 14),
    )  # fmt: skip
    body = dashboard(client, company="ALL").json()
    assert body["reliability"]["downtime_hours"] == 6
    assert body["reliability"]["mttr"] == 4  # เวลาซ่อมต่อใบยังเฉลี่ยตามใบ
    row = next(r for r in body["car_table"]["rows"] if r["code"] == "CAR1")
    assert row["downtime_hours"] == 6
    history = client.get("/api/car-history/1/", {"branch_company_id": "01"}).json()
    assert history["totals"]["downtime_hours"] == 6


def test_car_history_lists_parts_and_repair_costs(client):
    from dbapp.models import SummaryMaintenancePart

    SummaryMaintenancePart.objects.create(
        ext_id=1, docnum="IS-001", docdat=date(YEAR, 1, 6), stkcod="FLT-01",
        name="ไส้กรองน้ำมันเครื่อง", qty=2, unit="ชิ้น", amount=850,
    )  # fmt: skip
    body = client.get("/api/car-history/1/", {"branch_company_id": "01"}).json()

    ticket = body["tickets"][0]
    assert [p["name"] for p in ticket["parts"]] == ["ไส้กรองน้ำมันเครื่อง"]
    assert ticket["parts_amount"] == 850
    assert body["totals"]["parts_total"] == 850
    assert body["repair_items"] == [
        {"year": YEAR, "month": 1, "label": "ม.ค. 69", "repair_name": "เครื่องยนต์", "amount": 1000}
    ]


def add_doc(docnum, day, company_id="02", car_id=2, ma_ref=None, amount=500, month=1, name=""):
    SummaryRepairDoc.objects.create(
        docnum=docnum, docdat=date(YEAR, month, day), summary_date=date(YEAR, month, 1),
        year=YEAR, month=month, ma_ref=ma_ref, amount=amount, repair_name=name,
        branch_company_id=company_id, car_id=car_id, car_dep_id=1,
    )  # fmt: skip


def test_cars_without_tickets_count_repairs_from_issue_docs(client):
    # รถ 2 ไม่มีใบแจ้งซ่อม: ใบจ่ายวันเดียวกัน/อ้างใบแจ้งซ่อมเดียวกัน = ซ่อม 1 ครั้ง
    add_doc("OU1", 3)
    add_doc("OU2", 3)
    add_doc("OU3", 10, ma_ref="MJ16901001")
    add_doc("OU4", 12, ma_ref="MJ16901001")
    add_doc("OU5", 20, amount=0)  # มีแต่น้ำมัน ไม่นับ
    # รถ 1 มีใบแจ้งซ่อมแล้ว: ไม่นับจากใบจ่ายซ้ำ
    add_doc("OU6", 7, company_id="01", car_id=1)

    body = dashboard(client, company="ALL").json()
    rel = body["reliability"]
    assert rel["failure_count"] == 3 and rel["doc_failure_count"] == 2
    assert rel["trend"]["count"][0] == 3
    assert rel["repair_closed"] == 1  # ใบจ่ายไม่มีเวลาปิดงาน ไม่เข้า MTTR
    assert rel["top_cars"]["labels"] == ["รถ 2:CAR2", "รถ 1:CAR1"]
    rows = {r["code"]: r for r in body["car_table"]["rows"]}
    assert rows["CAR2"]["failure_count"] == 2 and rows["CAR1"]["failure_count"] == 1

    history = client.get("/api/car-history/2/", {"branch_company_id": "02"}).json()
    assert history["totals"]["breakdown_count"] == 2
    assert history["doc_jobs"] == []  # ใบจ่ายในเทสต์นี้ไม่มีรายการอะไหล่
    assert history["totals"]["doc_breakdown_count"] == 2
    assert history["monthly"]["breakdowns"] == [2]


def test_issue_docs_of_type_pm_count_as_pm_not_failures(client):
    add_doc("OU1", 3)
    add_doc("OU2", 3, name="PM")  # วันเดียวกัน แต่เป็น PM: PM 1 + ซ่อม 1
    add_doc("OU3", 15, name=" pm ")

    body = dashboard(client, company="ALL").json()
    rel = body["reliability"]
    assert rel["failure_count"] == 2 and rel["doc_failure_count"] == 1
    assert rel["pm_count"] == 2 and rel["doc_pm_count"] == 2
    assert rel["trend"]["pm"][0] == 2
    rows = {r["code"]: r for r in body["car_table"]["rows"]}
    assert rows["CAR2"]["failure_count"] == 1

    totals = client.get("/api/car-history/2/", {"branch_company_id": "02"}).json()["totals"]
    assert (totals["breakdown_count"], totals["pm_count"], totals["doc_pm_count"]) == (1, 2, 2)


def test_all_companies_merges_same_car_in_several_companies(client, data):
    co2 = BaseBranchCompany.objects.get(id="02")
    car1 = BaseCar.objects.get(id=1)
    common = dict(
        branch_company=co2, car=car1, car_dep_id=1, year=YEAR, month=2,
        month_th="กุมภาพันธ์", summary_date=date(YEAR, 2, 1),
    )  # fmt: skip
    SummaryRepair.objects.create(**common, repair_name="เครื่องยนต์", amount=300)
    SummaryWork.objects.create(**common, sum_diff_mile=40, count_diff_time=5, percent=0)
    # แผนก 1 ใช้ชั่วโมงจากบันทึกการใช้รถ
    for company, month, hours in ((BaseBranchCompany.objects.get(id="01"), 1, 80), (co2, 2, 40)):
        SummaryCarJob.objects.create(
            branch_company=company, car=car1, car_dep_id=1, year=YEAR, month=month,
            summary_date=date(YEAR, month, 1), expense_dept_id="01", expense_dept_name="งาน",
            job="ขนส่ง", hours=hours, km=0, trips=1, days=1,
        )  # fmt: skip

    body = dashboard(client, company="ALL").json()
    rows = {r["car_id"]: r for r in body["car_table"]["rows"]}
    assert len(body["car_table"]["rows"]) == 2  # รถ 1 ของสาขา 1 + สาขา 2 เป็นแถวเดียว
    assert rows[1]["branch_company_id"] == "01,02"
    assert rows[1]["branch_company_name"] == "สาขา 1, สาขา 2"
    assert rows[1]["repair_total"] == 1300
    assert rows[1]["work_total"] == 120
    assert rows[1]["repair_cost_per_hr"] == pytest.approx(1300 / 120)
    assert rows[1]["avg_work_per_day"] == pytest.approx(120 / 15)  # วันทำงาน 10 + 5
    assert rows[1]["failure_count"] == 1
    assert body["car_table"]["totals"]["repair_total"] == 1800
    # เทียบสาขายังแยกตามบริษัท
    branches = {b["branch_company_name"]: b for b in body["branch_compare"]}
    assert branches["สาขา 2"]["car_count"] == 2
    assert branches["สาขา 2"]["repair_total"] == 800

    # กดจากกราฟ (บริษัทเดียว) หรือจากแถวที่รวมไว้ ได้รถคันเดียวกันทุกบริษัท
    for branch in ("01", "01,02"):
        body = dashboard(client, company="ALL", car_id=1, branch_company_id=branch).json()
        assert body["selected_car"]["branch_company_id"] == "01,02"
        assert body["filters"]["branch_company_id"] == "01,02"
        assert body["charts"]["repair_by_type"]["total"] == 1300

    # ดูบริษัทเดียวไม่รวม
    rows = dashboard(client, company="C02").json()["car_table"]["rows"]
    assert {(r["car_id"], r["branch_company_id"]) for r in rows} == {(1, "02"), (2, "02")}

    history = client.get("/api/car-history/1/", {"branch_company_id": "01,02"}).json()
    assert history["car"]["branch_company_name"] == "สาขา 1, สาขา 2"
    assert history["totals"]["repair_total"] == 1300
    assert client.get("/api/car-history/1/", {"branch_company_id": "01,09"}).status_code == 403


def test_merge_only_for_vehicle_truck_heavy_machine_and_drill():
    from dbapp.services.dashboard import merges_companies

    assert [d for d in range(1, 7) if merges_companies("ALL", d, ["01", "02"])] == [1, 2, 3, 6]
    assert not merges_companies("C01", 1, ["01", "02"])
    assert not merges_companies("ALL", 1, ["01"])
