"""ดึงข้อมูลจาก webstock มาเก็บในฐานข้อมูล dashboard (งานตั้งเวลาบนเครื่อง server)

ตั้งใน Windows Task Scheduler (ดู README) Start in = โฟลเดอร์ backend:
    ทุกวัน 06:00   uv run python manage.py sync_webstock

รันตรงผ่าน Django ไม่ผ่าน HTTP: ไม่ต้องใช้ SYNC_TOKEN และไม่ต้องเปิด runserver ค้างไว้
ขั้นไหนดึงไม่ได้จะข้ามไปและเก็บข้อมูลเดิมไว้ แต่คำสั่งจะจบด้วย error (exit code 1)
เพื่อให้ Task Scheduler แสดงว่างานรอบนี้ไม่สำเร็จ
"""

import time
from datetime import date

from django.core.management.base import CommandError

from dbapp.management.utf8 import Utf8OutputCommand
from dbapp.services import sync
from dbapp.services.external_api import WebstockNotConfigured


class Command(Utf8OutputCommand):
    help = "ดึงข้อมูลหลัก + ข้อมูลสรุปย้อนหลังจาก webstock (แทนการเรียก /api/update_summary_from_api/)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--months",
            type=int,
            default=3,
            help="ดึงข้อมูลสรุปย้อนหลังกี่เดือน (ค่าเริ่มต้น 3) ใบแจ้งซ่อมดึงตั้งแต่ต้นปีเสมอ",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help=f'ดึงตั้งแต่ {sync.SYNC_START_DATE:%d/%m/%Y} เหมือนปุ่ม "อัปเดตข้อมูล" (ใช้เวลานานกว่า)',
        )
        parser.add_argument(
            "--date",
            type=date.fromisoformat,
            help="ถือว่าวันนี้คือวันที่นี้ (YYYY-MM-DD) ค่าเริ่มต้น = วันนี้",
        )

    def handle(self, months=3, full=False, date=None, **options):
        if months < 1:
            raise CommandError("--months ต้องมากกว่า 0")

        started = time.monotonic()
        scope = "ทั้งหมดตั้งแต่ต้นปี" if full else f"ย้อนหลัง {months} เดือน"
        self.stdout.write(f"ดึงข้อมูลจาก webstock ({scope})")
        try:
            if full:
                result = sync.run_full_sync(today=date)
            else:
                result = sync.run_daily_sync(today=date, months=months)
        except WebstockNotConfigured as exc:
            raise CommandError(str(exc)) from exc

        failed = []
        for group, title in (("base", "ข้อมูลหลัก"), ("summary", "ข้อมูลสรุป")):
            self.stdout.write(title)
            for step, ok in result[group].items():
                if ok:
                    self.stdout.write(self.style.SUCCESS(f"  ผ่าน  {step}"))
                else:
                    failed.append(step)
                    self.stdout.write(self.style.ERROR(f"  ล้ม   {step}"))

        seconds = time.monotonic() - started
        if failed:
            # ขั้นที่ล้มเก็บข้อมูลเดิมไว้ ดูสาเหตุได้ใน log ด้านบน (webstock API error ...)
            raise CommandError(
                f"ดึงไม่สำเร็จ {len(failed)} ขั้น: {', '.join(failed)} "
                f"(เก็บข้อมูลเดิมของขั้นนั้นไว้) ใช้เวลา {seconds:.0f} วินาที"
            )
        self.stdout.write(self.style.SUCCESS(f"สำเร็จทุกขั้น ใช้เวลา {seconds:.0f} วินาที"))
