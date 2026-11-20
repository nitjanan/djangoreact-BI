"""ลิงก์เข้าสู่ระบบอัตโนมัติในอีเมลรายงาน (magic link)

- ผูกกับ user ที่ใช้อีเมลเดียวกับผู้รับ (ต้องมีคนเดียว และไม่ใช่ superuser)
- ใช้ได้ครั้งเดียว: ใน token มีลายเซ็นของ last_login พอ login แล้ว last_login เปลี่ยน token ใช้ไม่ได้
- เปลี่ยนรหัสผ่าน/ปิดบัญชี = token ใช้ไม่ได้ทันที (ลายเซ็นมีรหัสผ่านที่ hash แล้วและ is_active)
- มีวันหมดอายุในตัว (รายสัปดาห์ 7 วัน รายเดือน 31 วัน)
- ใส่เฉพาะในเนื้ออีเมล ไม่ใส่ใน PDF (PDF มักถูกบันทึก/ส่งต่อ)

หน้าเว็บ /auto-login เป็นคนส่ง token มา POST (ไม่ login ตอน GET) เพื่อไม่ให้ระบบสแกนลิงก์
ของอีเมล (เช่น Outlook Safe Links) เปิดลิงก์ก่อนแล้วใช้ token หมด
"""

from datetime import datetime, timedelta
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.utils.crypto import constant_time_compare, salted_hmac

from .period import WEEKLY

SALT = "dbapp.reports.login-link"
VALID_FOR = {WEEKLY: timedelta(days=7)}
DEFAULT_VALID_FOR = timedelta(days=31)


def valid_for(frequency):
    return VALID_FOR.get(frequency, DEFAULT_VALID_FOR)


def _state(user):
    last_login = user.last_login.replace(microsecond=0, tzinfo=None) if user.last_login else ""
    value = f"{user.pk}|{user.password}|{last_login}|{user.is_active}"
    return salted_hmac(SALT, value).hexdigest()[:24]


def user_for_email(email):
    """user ที่ผูกกับอีเมลนี้ (ต้องมีคนเดียว) · superuser ไม่ได้ลิงก์อัตโนมัติ ให้ login เอง"""
    users = list(get_user_model().objects.filter(email__iexact=email.strip(), is_active=True)[:2])
    if len(users) != 1 or users[0].is_superuser:
        return None
    return users[0]


def make_token(user, expires_at):
    payload = {"u": user.pk, "s": _state(user), "e": int(expires_at.timestamp())}
    return signing.dumps(payload, salt=SALT, compress=True)


def check_token(token, now=None):
    """คืน user ถ้า token ถูกต้อง ยังไม่หมดอายุ และยังไม่เคยใช้ ไม่งั้นคืน None"""
    try:
        payload = signing.loads(token, salt=SALT)
    except signing.BadSignature:
        return None
    now = now or datetime.now()
    if not isinstance(payload, dict) or payload.get("e", 0) < now.timestamp():
        return None
    user = get_user_model().objects.filter(pk=payload.get("u"), is_active=True).first()
    if user is None or user.is_superuser:
        return None
    if not constant_time_compare(payload.get("s", ""), _state(user)):
        return None
    return user


def safe_next(value):
    """รับเฉพาะ path ภายในเว็บ (กัน open redirect ไปเว็บอื่น)"""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    return value


def login_url(token, dashboard_url):
    """แปลงลิงก์ dashboard เป็นลิงก์ที่ login ให้ก่อนแล้วไปหน้าเดิม"""
    parts = urlsplit(dashboard_url)
    target = parts.path + (f"?{parts.query}" if parts.query else "")
    query = urlencode({"token": token, "next": safe_next(target)})
    return f"{settings.FRONTEND_URL}/auto-login?{query}"
