"""คำสั่ง sync_webstock (งานตั้งเวลาบนเครื่อง server) — ไม่ต่อ webstock จริง"""

from datetime import date
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from dbapp.services import sync
from dbapp.services.external_api import WebstockNotConfigured

BASE_OK = {"car_type": True, "repair_type": True, "car_department": True, "car": True}
SUMMARY_OK = {"car_dep": True, "repair": True, "oil": True, "work": True}


def run(*args):
    out = StringIO()
    call_command("sync_webstock", *args, stdout=out, stderr=StringIO())
    return out.getvalue()


def test_daily_sync_by_default(monkeypatch):
    calls = []

    def fake_daily(today=None, months=3):
        calls.append((today, months))
        return {"base": BASE_OK, "summary": SUMMARY_OK}

    monkeypatch.setattr(sync, "run_daily_sync", fake_daily)
    out = run("--date", "2026-11-26")
    assert calls == [(date(2026, 11, 26), 3)]
    assert "ผ่าน  repair" in out
    assert "สำเร็จทุกขั้น" in out


def test_months_and_full_choose_the_range(monkeypatch):
    calls = []
    monkeypatch.setattr(
        sync,
        "run_daily_sync",
        lambda today=None, months=3: (
            calls.append(("daily", months)) or {"base": BASE_OK, "summary": SUMMARY_OK}
        ),
    )
    monkeypatch.setattr(
        sync,
        "run_full_sync",
        lambda today=None: calls.append(("full", None)) or {"base": BASE_OK, "summary": SUMMARY_OK},
    )
    run("--months", "6")
    run("--full")
    assert calls == [("daily", 6), ("full", None)]


def test_failed_step_exits_with_error_naming_it(monkeypatch):
    # ขั้นที่ล้มต้องทำให้ Task Scheduler เห็นว่างานไม่สำเร็จ (ไม่ใช่ "success" แบบ API เดิม)
    monkeypatch.setattr(
        sync,
        "run_daily_sync",
        lambda today=None, months=3: {"base": BASE_OK, "summary": {**SUMMARY_OK, "repair": False}},
    )
    with pytest.raises(CommandError, match="ดึงไม่สำเร็จ 1 ขั้น: repair"):
        run()


def test_webstock_not_configured_is_a_clear_error(monkeypatch):
    def not_configured(today=None, months=3):
        raise WebstockNotConfigured

    monkeypatch.setattr(sync, "run_daily_sync", not_configured)
    with pytest.raises(CommandError, match="ยังไม่ได้ตั้งค่าการเชื่อมต่อ webstock"):
        run()


def test_months_must_be_positive():
    with pytest.raises(CommandError, match="--months"):
        run("--months", "0")
