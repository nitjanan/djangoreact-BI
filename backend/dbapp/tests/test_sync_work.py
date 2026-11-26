import pytest

from dbapp.models import BaseBranchCompany, BaseCar, BaseCarDepartment, SummaryWork
from dbapp.services import sync


@pytest.mark.django_db
def test_sync_work_stores_meter_hours_when_webstock_sends_it(monkeypatch):
    BaseBranchCompany.objects.create(id="01", code="C01", name="บริษัท 1")
    dep = BaseCarDepartment.objects.create(id=3, name="เครื่องจักรกลหนัก")
    BaseCar.objects.create(id=1, code="C21", name="EC360", car_dep=dep)
    BaseCar.objects.create(id=2, code="C22", name="EC360", car_dep=dep)
    row = dict(
        branch_company="01", month=2, year=2026, month_th="ก.พ.", car_dep=3,
        sum_diff_mile=-542, count_diff_time=4, percent=0,
    )  # fmt: skip
    data = [{**row, "car_id": 1, "meter_hours": 33.5}, {**row, "car_id": 2}]  # 2 = webstock เก่า
    monkeypatch.setattr(sync, "get_base_url", lambda: "")
    monkeypatch.setattr(sync, "get_api_data", lambda url, base_url=None: data)

    assert sync.sync_work("2026-02-01", "2026-02-28")

    hours = dict(SummaryWork.objects.values_list("car_id", "meter_hours"))
    assert hours == {1: pytest.approx(33.5), 2: None}
