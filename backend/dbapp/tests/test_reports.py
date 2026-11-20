import re
from datetime import date, datetime, timedelta
from urllib.parse import unquote

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.core.mail import EmailMessage
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APIClient

from dbapp.models import (
    BaseBranchCompany,
    BaseCar,
    BaseCarDepartment,
    ReportSubscription,
    SummaryMaintenance,
    SummaryOil,
    SummaryRepair,
    SummaryWork,
)
from dbapp.reports.data import build_report
from dbapp.reports.login_link import check_token, make_token, safe_next
from dbapp.reports.pdf import render_pdf
from dbapp.reports.period import report_period
from dbapp.reports.send import send_reports

MONDAY = date(2026, 11, 16)  # วันที่ Task Scheduler รันรายสัปดาห์
NOW = datetime(2026, 11, 16, 7)


def test_weekly_period_is_last_monday_to_sunday():
    p = report_period("weekly", date(2026, 11, 18))  # วันพุธ
    assert (p.start, p.end) == (date(2026, 11, 9), date(2026, 11, 15))
    assert (p.prev_start, p.prev_end) == (date(2026, 11, 2), date(2026, 11, 8))
    assert (p.year, p.month) == (2026, 11)
    assert p.label == "9–15 พ.ย. 2569"
    assert (p.last_year_start.weekday(), p.last_year_end.weekday()) == (0, 6)


def test_monthly_period_is_last_month_and_crosses_year():
    p = report_period("monthly", date(2026, 1, 1))
    assert (p.start, p.end) == (date(2025, 12, 1), date(2025, 12, 31))
    assert (p.prev_start, p.prev_end) == (date(2025, 11, 1), date(2025, 11, 30))
    assert p.prev_month == (2025, 11)
    assert p.label == "ธันวาคม 2568"


def test_unknown_frequency_is_rejected():
    with pytest.raises(ValueError):
        report_period("daily", MONDAY)


@pytest.fixture
def fleet(db):
    BaseBranchCompany.objects.create(id="00", code="ALL", name="ทั้งหมด")
    co1 = BaseBranchCompany.objects.create(id="01", code="C01", name="สาขา 1")
    co2 = BaseBranchCompany.objects.create(id="02", code="C02", name="สาขา 2")
    dep = BaseCarDepartment.objects.create(id=3, name="เครื่องจักรกลหนัก")
    BaseCarDepartment.objects.create(id=5, name="เครื่องจักรโรงโม่")  # ไม่มีข้อมูล -> ไม่ขึ้นในรายงาน
    car1 = BaseCar.objects.create(id=1, code="C1", name="รถขุด 1", car_dep=dep)
    car2 = BaseCar.objects.create(id=2, code="C2", name="รถขุด 2", car_dep=dep)

    def month(company, car, year, m, amount, hours=100):
        common = dict(
            branch_company=company, car=car, car_dep=dep, year=year, month=m,
            summary_date=date(year, m, 1),
        )  # fmt: skip
        SummaryRepair.objects.create(**common, repair_name="เครื่องยนต์", amount=amount)
        SummaryOil.objects.create(**common, sum_liter=hours * 2, sum_km=0, liter_per_km=0)
        SummaryWork.objects.create(**common, sum_diff_mile=hours, count_diff_time=10, percent=0)

    month(co1, car1, 2026, 10, 1000)
    month(co1, car1, 2026, 9, 500)
    month(co1, car1, 2025, 10, 2000)
    month(co2, car2, 2026, 10, 300)

    seq = iter(range(1, 100))

    def breakdown(company, car, reported_at, finished_at=None):
        SummaryMaintenance.objects.create(
            ext_id=next(seq), branch_company=company, car=car, car_dep=dep,
            year=reported_at.year, month=reported_at.month, ma_type="02",
            reported_at=reported_at, finished_at=finished_at, broke_reason="ไฮดรอลิกรั่ว",
        )  # fmt: skip

    breakdown(co1, car1, datetime(2026, 11, 10, 8), datetime(2026, 11, 10, 14))  # สัปดาห์นี้ ปิดแล้ว
    breakdown(co1, car2, datetime(2569, 11, 12, 9))  # กรอกปีเป็น พ.ศ. ยังเปิดอยู่
    breakdown(co1, car1, datetime(2026, 11, 3, 8), datetime(2026, 11, 4, 8))  # สัปดาห์ก่อน
    breakdown(co2, car2, datetime(2026, 11, 11, 8))  # อีกบริษัท
    return {"co1": co1, "co2": co2}


def department(report, name="เครื่องจักรกลหนัก"):
    return next(d for d in report["departments"] if d["name"] == name)


def kpi(dep, key):
    return next(k for k in dep["monthly_kpis"] + dep["breakdown_kpis"] if k["key"] == key)


def test_weekly_report_counts_breakdowns_by_date_and_skips_empty_departments(fleet):
    report = build_report(report_period("weekly", MONDAY), ["01"], now=NOW)

    assert [d["name"] for d in report["departments"]] == ["เครื่องจักรกลหนัก"]
    dep = department(report)
    # 10 พ.ย. + 12 พ.ย. (ปี พ.ศ.) ของสาขา 1 · ไม่นับของสาขา 2
    assert kpi(dep, "reported")["value"] == 2
    assert kpi(dep, "reported")["prev"] == 1
    assert kpi(dep, "closed")["value"] == 1
    assert kpi(dep, "mttr")["value"] == 6
    assert [b["closed"] for b in dep["breakdowns"]] == [True, False]
    assert dep["open_jobs"]["total"] == 1
    # ตัวเลขรายเดือนเป็นยอดสะสม ไม่เทียบกับช่วงก่อน
    assert kpi(dep, "repair")["prev"] is None


@override_settings(FRONTEND_URL="http://testserver")
def test_monthly_report_compares_previous_month_and_last_year(fleet):
    report = build_report(report_period("monthly", date(2026, 11, 1)), ["01"], now=NOW)
    repair = kpi(department(report), "repair")
    assert (repair["value"], repair["prev"], repair["last_year"]) == (1000, 500, 2000)
    assert kpi(department(report), "fuel_rate")["value"] == 2
    # ลิงก์เปิด dashboard ด้วยตัวกรองเดียวกับรายงาน
    assert report["url"] == "http://testserver/?company=C01&year=2026&month_from=10&month_to=10"
    assert department(report)["url"].endswith("&car_dep=3")


def test_report_without_companies_covers_every_company_except_all_row(fleet):
    report = build_report(report_period("monthly", date(2026, 11, 1)), now=NOW)
    assert report["all_companies"]
    assert report["companies"] == ["สาขา 1", "สาขา 2"]
    assert "company=ALL" in report["url"]
    assert kpi(department(report), "repair")["value"] == 1300


def test_pdf_renders_thai_report(fleet):
    for frequency in ("weekly", "monthly"):
        pdf = render_pdf(build_report(report_period(frequency, MONDAY), now=NOW))
        assert pdf.startswith(b"%PDF")


def subscribe(email, companies=(), **fields):
    sub = ReportSubscription.objects.create(email=email, **fields)
    sub.companies.set(companies)
    return sub


def test_send_reports_emails_pdf_once_per_period(fleet):
    subscribe("all@example.com")
    subscribe("branch1@example.com", [fleet["co1"]])
    subscribe("monthly-only@example.com", weekly=False)
    subscribe("off@example.com", is_active=False)

    result = send_reports("weekly", today=MONDAY, now=NOW)

    assert sorted(result.sent) == ["all@example.com", "branch1@example.com"]
    assert len(mail.outbox) == 2
    message = mail.outbox[0]
    assert message.subject == "[STG] สรุปรายงานประจำสัปดาห์ 9–15 พ.ย. 2569"
    filename, content, mimetype = message.attachments[0]
    assert filename == "fleet-report-weekly-2026-11-09.pdf"
    assert mimetype == "application/pdf" and content.startswith(b"%PDF")
    assert "เครื่องจักรกลหนัก" in message.body
    # เนื้ออีเมลมีแค่ลิงก์ช่วงรายงานกับทั้งปี (ลิงก์รายแผนกอยู่ใน PDF)
    assert message.body.count("http://") == 2
    assert "company=ALL&year=2026&month_from=11&month_to=11\n" in message.body
    assert "ดูทั้งปี 2569 (ม.ค. – พ.ย.): " in message.body
    assert "company=ALL&year=2026&month_from=1&month_to=11\n" in message.body
    # ลิงก์อยู่ใต้หัวเรื่องและขอบเขตรายงานเลย
    assert message.body.splitlines()[3].startswith("เปิด dashboard 9–15 พ.ย. 2569: http")
    html = message.alternatives[0][0]
    assert message.alternatives[0][1] == "text/html"
    assert "แยกตามแผนก" in html and "เครื่องจักรกลหนัก" in html
    assert "month_from=1&amp;month_to=11" in html
    # ชื่อแผนกในตาราง HTML เป็นลิงก์ไปแผนกนั้น
    assert "month_to=11&amp;car_dep=3" in html
    assert ReportSubscription.objects.get(email="all@example.com").last_weekly_period == date(
        2026, 11, 9
    )

    # รันซ้ำวันเดียวกัน (Task Scheduler รันซ้ำ) ไม่ส่งซ้ำ
    again = send_reports("weekly", today=MONDAY, now=NOW)
    assert again.sent == [] and len(again.skipped) == 2
    assert len(mail.outbox) == 2

    assert len(send_reports("weekly", today=MONDAY, now=NOW, force=True).sent) == 2


def test_one_failed_recipient_does_not_stop_the_others(fleet, monkeypatch):
    subscribe("broken@example.com")
    subscribe("ok@example.com")
    original = EmailMessage.send

    def send(self, *args, **kwargs):
        if self.to == ["broken@example.com"]:
            raise OSError("mailbox unavailable")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(EmailMessage, "send", send)
    result = send_reports("monthly", today=MONDAY, now=NOW)

    assert result.sent == ["ok@example.com"]
    assert result.failed == [("broken@example.com", "mailbox unavailable")]
    # ส่งไม่สำเร็จ = ยังไม่บันทึกว่าส่งแล้ว รอบหน้าจะลองใหม่
    assert ReportSubscription.objects.get(email="broken@example.com").last_monthly_period is None


def test_command_output_writes_pdf_without_sending(fleet, tmp_path):
    subscribe("all@example.com")
    call_command("send_fleet_reports", "monthly", "--date", "2026-11-01", "--output", tmp_path)

    assert mail.outbox == []
    files = list(tmp_path.glob("*.pdf"))
    assert [f.name for f in files] == ["fleet-report-monthly-2026-10-01-all.pdf"]
    assert ReportSubscription.objects.get().last_monthly_period is None


# ------------------------------------------------------------ auto-login link

AUTO_LOGIN = re.compile(r"/auto-login\?token=([^&\s]+)&next=(\S+)")


def login_with(token):
    client = APIClient(enforce_csrf_checks=False)
    return client, client.post("/api/auth/report-login/", {"token": token}, format="json")


def test_email_link_logs_in_matching_user_once(fleet):
    User.objects.create_user("somchai", "Somchai@Example.com", "pw-123456")
    subscribe("somchai@example.com")

    send_reports("weekly", today=MONDAY, now=datetime.now())
    body = mail.outbox[0].body
    token, next_url = AUTO_LOGIN.search(body).groups()
    assert unquote(next_url).startswith("/?company=ALL&year=2026")
    assert "เข้าสู่ระบบให้อัตโนมัติในชื่อ somchai" in body
    assert "<b>somchai</b>" in mail.outbox[0].alternatives[0][0]
    # ลิงก์ใน PDF เป็นลิงก์ปกติ (PDF มักถูกส่งต่อ)
    assert b"auto-login" not in mail.outbox[0].attachments[0][1]

    client, res = login_with(unquote(token))
    assert res.status_code == 200
    assert res.json()["user"]["username"] == "somchai"
    assert client.get("/api/me/").status_code == 200

    # ใช้ซ้ำไม่ได้ (login แล้ว last_login เปลี่ยน)
    assert login_with(unquote(token))[1].status_code == 400


def test_no_auto_login_for_superuser_unknown_or_disabled(fleet):
    User.objects.create_superuser("admin", "admin@example.com", "pw-123456")
    User.objects.create_user("off", "off@example.com", "pw-123456")
    subscribe("admin@example.com")
    subscribe("nobody@example.com")
    subscribe("off@example.com", auto_login=False)

    send_reports("weekly", today=MONDAY, now=NOW)

    assert len(mail.outbox) == 3
    assert not any("auto-login" in m.body for m in mail.outbox)


def test_token_rejected_when_expired_or_password_changed(fleet):
    user = User.objects.create_user("somchai", "somchai@example.com", "pw-123456")
    now = datetime(2026, 11, 16, 7)
    token = make_token(user, now + timedelta(days=7))

    assert check_token(token, now=now) == user
    assert check_token(token, now=now + timedelta(days=8)) is None
    assert check_token(token[:-2] + "xx", now=now) is None

    user.set_password("new-pw-654321")
    user.save()
    assert check_token(token, now=now) is None


def test_safe_next_only_allows_internal_paths():
    assert safe_next("/?company=ALL") == "/?company=ALL"
    for bad in ("https://evil.example", "//evil.example", r"/\evil", "", None):
        assert safe_next(bad) == "/"
