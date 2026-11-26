"""ให้คำสั่ง manage.py พิมพ์ภาษาไทยได้เมื่อรันจาก Windows Task Scheduler"""

import sys

from django.core.management.base import BaseCommand


class Utf8OutputCommand(BaseCommand):
    """คอนโซล/Task Scheduler ของ Windows ใช้ codepage เดิม (cp1252/cp874) พิมพ์ภาษาไทยไม่ได้
    -> UnicodeEncodeError ทั้งที่งานทำเสร็จแล้ว จึงให้พิมพ์เป็น UTF-8 เสมอ (รวมไฟล์ log ที่ >> ไว้)
    """

    def execute(self, *args, **options):
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)  # ตอน test เป็น StringIO ไม่มีเมธอดนี้
            if reconfigure:
                reconfigure(encoding="utf-8", errors="replace")
        return super().execute(*args, **options)
