"""ส่งรายงาน PDF ทางอีเมลให้ผู้รับใน ReportSubscription"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from dbapp.models import ReportSubscription

from . import login_link
from .data import build_report
from .pdf import fmt, render_pdf, report_filename
from .period import BUDDHIST_ERA_OFFSET, MONTHS_SHORT_TH, WEEKLY, report_period, thai_date

logger = logging.getLogger(__name__)


@dataclass
class SendResult:
    period: object
    sent: list = field(default_factory=list)  # อีเมลที่ส่งสำเร็จ
    skipped: list = field(default_factory=list)  # ส่งช่วงนี้ไปแล้ว
    failed: list = field(default_factory=list)  # (อีเมล, ข้อความ error)
    files: list = field(default_factory=list)  # ไฟล์ที่บันทึก (โหมด output)


def _last_field(frequency):
    return "last_weekly_period" if frequency == WEEKLY else "last_monthly_period"


def _company_key(sub):
    return tuple(sorted(sub.companies.values_list("id", flat=True)))


UP_COLOR = "#c2410c"  # ค่าซ่อมเพิ่ม = แย่
DOWN_COLOR = "#15803d"


def _repair_kpi(d):
    return next(k for k in d["monthly_kpis"] if k["key"] == "repair")


def _change(value, prev, prev_name):
    """'↑ 12% จากเดือนก่อน' และสี · เทียบไม่ได้ = ('', None)"""
    if not prev or value is None:
        return "", None
    pct = (value - prev) / prev * 100
    if round(pct) == 0:
        return f"เท่ากับ{prev_name}", "#5b6f72"
    arrow, color = ("↑", UP_COLOR) if pct > 0 else ("↓", DOWN_COLOR)
    return f"{arrow} {abs(pct):,.0f}% จาก{prev_name}", color


def email_context(report, login=None):
    """ข้อมูลของอีเมล ใช้ทั้งแบบ HTML และข้อความธรรมดา

    login = (user, token, หมดอายุ) -> ลิงก์ในอีเมลเข้าสู่ระบบให้อัตโนมัติ
    """
    period = report["period"]
    deps = report["departments"]

    def link(url):
        return login_link.login_url(login[1], url) if login else url

    if period.is_weekly:
        period_short = period.label
        period_word = "สัปดาห์นี้"
    else:
        period_short = f"{MONTHS_SHORT_TH[period.month - 1]} {period.year + BUDDHIST_ERA_OFFSET}"
        period_word = "เดือนนี้"

    rows = []
    for d in deps:
        kpi = _repair_kpi(d)
        change, color = _change(kpi["value"], kpi["prev"], period.prev_name)
        rows.append(
            {
                "name": d["name"],
                "url": link(d["url"]),  # ใช้ในอีเมล HTML เท่านั้น (ข้อความธรรมดาลิงก์ยาวรก)
                "repair": fmt(kpi["value"]),
                "change": change,
                "change_color": color,
                "new_jobs": fmt(d["breakdown_count"]),
                "open_jobs": fmt(d["open_jobs"]["total"]),
                "watch": fmt(d["watchlist"]["count"]),
            }
        )

    repair_total = sum(_repair_kpi(d)["value"] or 0 for d in deps)
    prevs = [_repair_kpi(d)["prev"] for d in deps]
    prev_total = sum(prevs) if prevs and all(p is not None for p in prevs) else None
    change, color = _change(repair_total, prev_total, period.prev_name)
    tiles = [
        {
            "label": "ค่าซ่อมรวม",
            "value": f"{fmt(repair_total)} บาท",
            "note": change or ("ยอดสะสมของเดือน" if period.is_weekly else ""),
            "note_color": color,
        },
        {
            "label": "แจ้งซ่อมใหม่",
            "value": f"{fmt(sum(d['breakdown_count'] for d in deps))} ใบ",
            "note": f"เปิดใบแจ้งซ่อม{period_word}",
        },
        {
            "label": "งานซ่อมค้าง",
            "value": f"{fmt(sum(d['open_jobs']['total'] for d in deps))} ใบ",
            "note": "ยังไม่ปิดงาน ณ วันนี้",
        },
    ]

    notes = [
        f"แจ้งซ่อมใหม่ = ใบแจ้งซ่อมที่เปิดใน{period_word}",
        "งานค้าง = ใบแจ้งซ่อมที่ยังไม่ปิดงาน ณ วันที่ส่งรายงาน (รวมของช่วงก่อนหน้า)",
        "ควรจับตา = รถที่ซ่อมแพง เสียบ่อย ซ่อมซ้ำ หรือจอดซ่อมนาน เทียบกับคันอื่น (ตั้งแต่ต้นปี)",
    ]
    if period.is_weekly:
        notes.insert(0, f"ค่าซ่อมเป็น{period.monthly_label} เพราะระบบบันทึกค่าซ่อมเป็นรายเดือน")

    if report["all_companies"]:
        scope = "ทุกบริษัท · ทุกแผนก"
    else:
        scope = " · ".join(report["companies"])

    ctx = {
        "heading": f"{period.title} {period.label}",
        "scope": scope,
        "period_short": period_short,
        "url": link(report["url"]),
        "year_url": link(report["year_url"]),
        "year_label": report["year_label"],
        "tiles": tiles,
        "rows": rows,
        "notes": notes,
        "login": None,
    }
    if login:
        user, _, expires_at = login
        ctx["login"] = {"username": user.get_username(), "expires": thai_date(expires_at)}
    return ctx


def email_body(report, login=None):
    """อีเมลแบบข้อความธรรมดา (สำหรับโปรแกรมอีเมลที่ไม่แสดง HTML)"""
    c = email_context(report, login)
    lines = [
        c["heading"],
        c["scope"],
        "",
        f"เปิด dashboard {c['period_short']}: {c['url']}",
        f"ดู{c['year_label']}: {c['year_url']}",
        "",
    ]
    lines += [
        f"{t['label']}: {t['value']}" + (f" ({t['note']})" if t["note"] else "") for t in c["tiles"]
    ]
    lines += ["", "แยกตามแผนก:"]
    for r in c["rows"]:
        change = f" ({r['change']})" if r["change"] else ""
        lines.append(
            f"- {r['name']}: ค่าซ่อม {r['repair']} บาท{change} · แจ้งซ่อมใหม่ {r['new_jobs']} ใบ"
            f" · งานค้าง {r['open_jobs']} ใบ · ควรจับตา {r['watch']} คัน"
        )
    if not c["rows"]:
        lines.append("- ไม่มีข้อมูลในช่วงนี้")
    lines += ["", *c["notes"], "รายละเอียดทั้งหมดอยู่ในไฟล์ PDF ที่แนบมา", ""]
    if c["login"]:
        lines += [
            f"ลิงก์ในอีเมลนี้เข้าสู่ระบบให้อัตโนมัติในชื่อ {c['login']['username']} "
            f"ใช้ได้ครั้งเดียว ภายในวันที่ {c['login']['expires']} · กรุณาอย่าส่งต่ออีเมลนี้",
            "(ลิงก์ในไฟล์ PDF ต้องเข้าสู่ระบบด้วยรหัสผ่านตามปกติ)",
            "",
        ]
    lines.append("อีเมลนี้ส่งอัตโนมัติจาก STG Dashboard · หากไม่ต้องการรับแล้ว แจ้งผู้ดูแลระบบให้ปิดการส่ง")
    return "\n".join(lines)


def email_html(report, login=None):
    return render_to_string("reports/email.html", email_context(report, login))


def send_reports(
    frequency,
    today=None,
    now=None,
    subscriptions=None,
    force=False,
    output_dir=None,
):
    """ส่งรายงานของช่วงล่าสุดที่จบแล้ว

    subscriptions: กำหนดผู้รับเอง (เช่นปุ่มส่งทดสอบใน Admin) ไม่ระบุ = ผู้รับที่เปิดส่งความถี่นี้
    force: ส่งซ้ำได้แม้เคยส่งช่วงนี้แล้ว
    output_dir: บันทึก PDF ลงโฟลเดอร์แทนการส่งอีเมล (ใช้ตรวจหน้าตารายงาน)
    """
    today = today or date.today()
    now = now or datetime.now()
    period = report_period(frequency, today)
    result = SendResult(period)
    last_field = _last_field(frequency)

    if subscriptions is None:
        subscriptions = ReportSubscription.objects.filter(is_active=True, **{frequency: True})
    subscriptions = list(subscriptions.prefetch_related("companies"))

    if output_dir is not None and not subscriptions:
        # ยังไม่มีผู้รับ: บันทึกรายงานทุกบริษัทไว้ตรวจหน้าตา
        subscriptions = [None]

    groups = {}
    for sub in subscriptions:
        if sub is not None and not force and getattr(sub, last_field) == period.start:
            result.skipped.append(sub.email)
            continue
        groups.setdefault(_company_key(sub) if sub else (), []).append(sub)

    for company_ids, subs in groups.items():
        report = build_report(period, list(company_ids) or None, now=now)
        pdf = render_pdf(report)
        filename = report_filename(period)

        if output_dir is not None:
            suffix = "-".join(company_ids) if company_ids else "all"
            path = Path(output_dir) / filename.replace(".pdf", f"-{suffix}.pdf")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pdf)
            result.files.append(path)
            continue

        subject = f"[STG] {period.title} {period.label}"
        expires_at = now + login_link.valid_for(frequency)
        for sub in subs:
            user = login_link.user_for_email(sub.email) if sub.auto_login else None
            login = None
            if user is not None:
                login = (user, login_link.make_token(user, expires_at), expires_at)
            message = EmailMultiAlternatives(subject, email_body(report, login), to=[sub.email])
            message.attach_alternative(email_html(report, login), "text/html")
            message.attach(filename, pdf, "application/pdf")
            try:
                message.send()
            except Exception as exc:  # ส่งไม่ได้คนหนึ่ง คนอื่นยังได้รับ
                logger.exception("ส่งรายงานไม่สำเร็จ: %s", sub.email)
                result.failed.append((sub.email, str(exc)))
                continue
            setattr(sub, last_field, period.start)
            sub.save(update_fields=[last_field])
            result.sent.append(sub.email)
    return result
