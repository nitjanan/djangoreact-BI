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
    SummaryMaintenance,
    SummaryOil,
    SummaryRepair,
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
    assert names == ["แผนกรถ"]
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
