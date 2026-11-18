# Fleet Dashboard

Dashboard รถ/เครื่องจักร (ค่าซ่อม น้ำมัน ชั่วโมงทำงาน MTBF/MTTR) เขียนใหม่จากโปรเจกต์ `djangodashboard`
(Django + Bootstrap 5) เป็น **Django REST Framework + React (TypeScript)**

```
backend/    Django 4.2 + DRF  (ใช้ฐานข้อมูล djangodashboarddb ตัวเดิม)
frontend/   React + TypeScript + Vite + Tailwind + shadcn/ui   (เฟส 2)
```

## Backend

ต้องมี [uv](https://docs.astral.sh/uv/) และ MariaDB/MySQL (XAMPP) ที่มีฐาน `djangodashboarddb`

```bash
cd backend
cp .env.example .env
uv sync
uv run python manage.py migrate      # ฐานเดิม: แค่สร้างตารางของ app ใหม่ (ถ้ามี)
uv run python manage.py runserver 8001
```

- Swagger: http://localhost:8001/api/docs/
- Admin:   http://localhost:8001/admin/

> ใช้พอร์ต 8001 เพราะ `MAINTENANCE_API_BASE` (webstock บนเครื่อง) ใช้ 8000 อยู่

ทดสอบและ lint:

```bash
uv run pytest
uv run ruff check . && uv run ruff format .
```

### ทำไม Django 4.2

MariaDB 10.4 ใน XAMPP ไม่รองรับ Django 5.x — อัปเกรดเป็น MariaDB 10.5+ / MySQL 8 แล้วค่อยขยับไป Django 5.2 LTS

## API

ทุก endpoint ต้อง login (session cookie) ยกเว้นกลุ่ม `auth/`
คำขอที่ไม่ใช่ GET ต้องส่ง header `X-CSRFToken` จาก cookie `fleet_csrftoken`

| Method | Path | ใช้แทนของเดิม |
|---|---|---|
| GET | `/api/auth/csrf/` | — (ตั้ง cookie CSRF) |
| POST | `/api/auth/login/` | `login/` |
| POST | `/api/auth/logout/` | `logout/` |
| POST | `/api/auth/password-reset/` | `reset_password/` |
| POST | `/api/auth/password-reset/confirm/` | `reset/<uid>/<token>` |
| GET | `/api/me/` | context processor `companyVisibleTab`, `userVisibleTab` |
| GET | `/api/dashboard/?company=ALL&year=2026&car_dep=1&car_type=&car_id=&branch_company_id=` | `home` + `setSessionCompany` + `getApiDataToDashbord` |
| GET | `/api/car-departments/`, `/api/car-types/`, `/api/cars/?car_dep=&car_type=` | ตัวเลือกใน filter |
| POST | `/api/sync/` | `updateValueAPI/` |
| POST | `/api/sync/summary/` | `update_summary_from_api/` |
| POST | `/api/sync/base/` | `update_base_from_api/` |

ตัวกรอง (บริษัท แผนก ฯลฯ) ส่งเป็น query param แทนการเก็บใน session
และ API ตรวจว่า user มีสิทธิ์เห็นบริษัทที่ขอ

## โครงสร้าง backend

```
config/                 settings (อ่านค่าจาก .env), urls
dbapp/models.py         คัดลอกจากโปรเจกต์เดิม (app label เดิม เพื่อใช้ migrations/ตารางเดิม)
dbapp/migrations/       คัดลอกจากโปรเจกต์เดิม 0001–0019
dbapp/services/
  external_api.py       เรียก webstock ด้วย JWT
  sync.py               ดึงข้อมูล webstock -> base_* / sum_*
  dashboard.py          คำนวณกราฟ ตารางรถ MTBF/MTTR
dbapp/api/              serializers, views, urls ของ DRF
dbapp/tests/            pytest (ใช้ SQLite ในหน่วยความจำ)
```
