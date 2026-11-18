# Fleet Dashboard

Dashboard รถ/เครื่องจักร (ค่าซ่อม น้ำมัน ชั่วโมงทำงาน MTBF/MTTR) เขียนใหม่จากโปรเจกต์ `djangodashboard`
(Django + Bootstrap 5) เป็น **Django REST Framework + React (TypeScript)**

```
backend/    Django 4.2 + DRF  (ใช้ฐานข้อมูล djangodashboarddb ตัวเดิม)
frontend/   React 19 + TypeScript + Vite + Tailwind v4 + shadcn/ui
```

## เริ่มใช้งาน (dev)

เปิด MySQL ใน XAMPP ก่อน แล้วรัน 2 terminal:

```bash
cd backend && uv run python manage.py runserver 8001
```

```bash
cd frontend && npm install && npm run dev
```

เปิด http://localhost:5173 — Vite ส่ง `/api`, `/admin`, `/static` ต่อไปที่ Django (8001)
จึงอยู่ origin เดียวกัน ใช้ session cookie ได้โดยไม่ต้องตั้ง CORS

## Frontend

| เรื่อง | ใช้ |
|---|---|
| UI | Tailwind v4 + shadcn/ui (Radix), ฟอนต์ Geist + Noto Sans Thai |
| ข้อมูลจาก API | TanStack Query + openapi-fetch (type สร้างจาก schema ของ DRF) |
| Routing | React Router — ตัวกรอง dashboard เก็บใน URL (`?company=&car_dep=&car_type=&car_id=`) |
| ฟอร์ม | React Hook Form + Zod |
| กราฟ | react-apexcharts (ชุดสีเดิมที่ตรวจสำหรับคนตาบอดสีแล้ว) |
| Excel | SheetJS 0.20.3 จาก cdn.sheetjs.com (เวอร์ชันบน npm เก่าและมีช่องโหว่) |

API เปลี่ยนเมื่อไร ให้สร้าง type ใหม่:

```bash
cd frontend && npm run gen:api   # backend/schema.yml -> src/api/schema.d.ts
```

ตรวจโค้ด: `npm run typecheck`, `npm run lint`, `npm run build`

```
src/api/          client (CSRF อัตโนมัติ), hooks ของ TanStack Query, schema.d.ts (generated)
src/layout/       RequireAuth, AppLayout (sidebar), CompanySwitcher
src/pages/auth/   login, ลืมรหัสผ่าน, ตั้งรหัสผ่านใหม่ (/reset-password/:uid/:token)
src/pages/dashboard/  KPI, ตารางรถ, ความถี่การเสีย (MTBF/MTTR), กราฟ 9 ตัว
src/lib/          ตัวกรองใน URL, format ตัวเลข, export Excel
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
