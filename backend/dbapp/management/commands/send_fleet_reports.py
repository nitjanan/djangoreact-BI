"""ส่งรายงานสรุป PDF ทางอีเมล

ตั้งใน Windows Task Scheduler (ดู README):
    รายสัปดาห์ ทุกวันจันทร์ 07:00   uv run python manage.py send_fleet_reports weekly --sync
    รายเดือน   ทุกวันที่ 1 07:00     uv run python manage.py send_fleet_reports monthly --sync

ตรวจหน้าตารายงานโดยไม่ส่งอีเมล:
    uv run python manage.py send_fleet_reports weekly --output reports/
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from dbapp.reports.period import FREQUENCIES
from dbapp.reports.send import send_reports


class Command(BaseCommand):
    help = "ส่งรายงานสรุปรายสัปดาห์/รายเดือน (PDF) ให้ผู้รับที่ตั้งไว้ใน Admin"

    def add_arguments(self, parser):
        parser.add_argument("frequency", choices=FREQUENCIES)
        parser.add_argument(
            "--date",
            type=date.fromisoformat,
            help="วันที่รัน (YYYY-MM-DD) ค่าเริ่มต้น = วันนี้ รายงานคือช่วงที่จบก่อนวันนี้",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="ดึงข้อมูลล่าสุดจาก webstock ก่อนสร้างรายงาน",
        )
        parser.add_argument("--force", action="store_true", help="ส่งซ้ำแม้เคยส่งช่วงนี้แล้ว")
        parser.add_argument(
            "--output",
            metavar="DIR",
            help="บันทึก PDF ลงโฟลเดอร์นี้แทนการส่งอีเมล",
        )

    def handle(self, frequency, date=None, sync=False, force=False, output=None, **options):
        if sync:
            from dbapp.services.sync import run_recent_summary_sync

            try:
                steps = run_recent_summary_sync(today=date)
                failed = [step for step, ok in steps.items() if not ok]
                if failed:
                    self.stderr.write(f"อัปเดตข้อมูลไม่ครบ: {', '.join(failed)} (ใช้ข้อมูลเดิมต่อ)")
            except Exception as exc:  # ดึงข้อมูลไม่ได้ ก็ยังส่งรายงานจากข้อมูลล่าสุดที่มี
                self.stderr.write(f"อัปเดตข้อมูลจาก webstock ไม่สำเร็จ ({exc}) ใช้ข้อมูลเดิมต่อ")

        result = send_reports(frequency, today=date, force=force, output_dir=output)
        period = result.period
        self.stdout.write(f"{period.title} {period.label}")
        for path in result.files:
            self.stdout.write(f"  บันทึก {path}")
        if result.sent:
            self.stdout.write(self.style.SUCCESS(f"  ส่งแล้ว {len(result.sent)} คน"))
        if result.skipped:
            self.stdout.write(f"  ข้าม {len(result.skipped)} คน (ส่งช่วงนี้ไปแล้ว ใช้ --force เพื่อส่งซ้ำ)")
        if output is None and not (result.sent or result.skipped or result.failed):
            self.stdout.write("  ยังไม่มีผู้รับ: เพิ่มได้ที่ Admin > ผู้รับรายงานทางอีเมล")
        if result.failed:
            for email, error in result.failed:
                self.stderr.write(f"  ส่งไม่สำเร็จ {email}: {error}")
            raise CommandError(f"ส่งไม่สำเร็จ {len(result.failed)} คน")
