"""เรียก API ของระบบ webstock (JWT) — ย้ายมาจาก views.py เดิม"""

import logging

import requests

from dbapp.models import BaseAPI

logger = logging.getLogger(__name__)

TIMEOUT = 10


def get_base_api():
    # query เมื่อเรียกใช้งานจริง (ไม่ cache ตอน import)
    return BaseAPI.objects.get(apiname="webstock")


def get_base_url():
    # ตัด / ท้าย URL ที่กรอกใน Admin ทิ้ง ไม่งั้นต่อ path แล้วได้ "//jwt/create/" (404)
    return get_base_api().url.rstrip("/")


def get_jwt_token(base_url=None):
    api = get_base_api()
    res = requests.post(
        f"{(base_url or api.url).rstrip('/')}/jwt/create/",
        json={"username": api.username, "password": api.password},
        timeout=TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()
    return data["access"], data["refresh"]


def refresh_token(refresh, base_url=None):
    res = requests.post(
        f"{(base_url or get_base_url()).rstrip('/')}/jwt/refresh/",
        json={"refresh": refresh},
        timeout=TIMEOUT,
    )
    res.raise_for_status()
    return res.json()["access"]


def get_api_data(api_url, base_url=None):
    """GET ข้อมูลที่ต้องใช้ JWT รองรับ pagination แบบ DRF (results/next)

    base_url: ขอ token จากเซิร์ฟเวอร์เดียวกับ api_url (None = ใช้ BaseAPI)
    คืนค่า [] เมื่อเกิด error (เหมือนเดิม) เพื่อไม่ให้ลบข้อมูลเก่าทิ้ง
    """
    try:
        access, refresh = get_jwt_token(base_url)
        headers = {"Authorization": f"Bearer {access}"}

        all_results = []
        next_url = api_url

        while next_url:
            res = requests.get(next_url, headers=headers, timeout=TIMEOUT)

            if res.status_code == 401:  # token หมดอายุ
                headers = {"Authorization": f"Bearer {refresh_token(refresh, base_url)}"}
                res = requests.get(next_url, headers=headers, timeout=TIMEOUT)

            res.raise_for_status()
            data = res.json()

            if isinstance(data, dict) and "results" in data:
                all_results.extend(data["results"])
                next_url = data["next"]
            else:
                return data

        return all_results

    except Exception:
        logger.exception("webstock API error: %s", api_url)
        return []
