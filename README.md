# STG Dashboard

Dashboard รถ/เครื่องจักร (ค่าซ่อม น้ำมัน ชั่วโมงทำงาน MTBF/MTTR) เขียนใหม่จากโปรเจกต์ `djangodashboard`
(Django + Bootstrap 5) เป็น **Django REST Framework + React (TypeScript)**

```
backend/    Python 3.9.5 + Django 4.2.29 + DRF 3.14  (ใช้ฐานข้อมูล djangodashboarddb ตัวเดิม)
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

ต้องมี Python 3.9.5, [uv](https://docs.astral.sh/uv/) และ MariaDB/MySQL (XAMPP) ที่มีฐาน `djangodashboarddb`

เวอร์ชันของ Python และแพ็กเกจล็อกให้ตรงกับ `djangostock` / `djangoweight`
(Django 4.2.29, DRF 3.14.0, django-filter 2.4.0, django-import-export 2.6.1, mysqlclient 2.0.3,
whitenoise 5.3.0, gunicorn 20.1.0 ฯลฯ) — ดู `backend/pyproject.toml`
ถ้าจะใช้ pip แทน uv: `py -3.9 -m venv .venv` แล้ว `.venv\Scripts\pip install -r requirements.txt`
(อัปเดต `requirements.txt` ทุกครั้งที่แก้ dependency ด้วยคำสั่งในบรรทัดแรกของไฟล์)

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

### รายงานสรุปทางอีเมล (PDF)

ส่งรายงานรายสัปดาห์ (จันทร์–อาทิตย์ที่แล้ว) และรายเดือน (เดือนที่แล้ว) เป็นไฟล์ PDF ไฟล์เดียวทุกแผนก:
ภาพรวม, ตัวเลขหลักเทียบช่วงก่อน/ปีก่อน, การแจ้งซ่อม, ใบค้าง, รถที่ต้องจับตา, ต้นทุนซ่อมต่อชั่วโมงสูงสุด

1. ตั้งค่าอีเมลใน `.env` (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`)
2. เพิ่มผู้รับที่ Admin > **ผู้รับรายงานทางอีเมล** (เลือกรายสัปดาห์/รายเดือน และบริษัท ไม่เลือก = ทุกบริษัท)
   ในหน้ารายชื่อมีคำสั่ง "ส่งรายงาน…ตอนนี้" ไว้ส่งทดสอบให้คนที่เลือก
3. ดูหน้าตารายงานโดยไม่ส่งอีเมล:

   ```bash
   uv run python manage.py send_fleet_reports weekly --output reports/
   ```

4. ตั้งให้ส่งอัตโนมัติด้วย Windows Task Scheduler (สร้าง 2 งาน, Start in = โฟลเดอร์ `backend`):

   | งาน | Trigger | Program | Arguments |
   |---|---|---|---|
   | รายสัปดาห์ | Weekly, Monday 07:00 | `uv` | `run python manage.py send_fleet_reports weekly --sync` |
   | รายเดือน | Monthly, day 1, 07:00 | `uv` | `run python manage.py send_fleet_reports monthly --sync` |

   `--sync` ดึงข้อมูลล่าสุดจาก webstock ก่อน (ดึงไม่ได้ก็ยังส่งจากข้อมูลเดิม)
   รันซ้ำในช่วงเดียวกันจะไม่ส่งซ้ำ (ใช้ `--force` เพื่อส่งซ้ำ)

### อัปเดตข้อมูลอัตโนมัติทุกวัน

`GET /api/update_summary_from_api/` ดึงข้อมูลหลัก (รถ ชนิด แผนก ประเภทซ่อม) แล้วดึงข้อมูลสรุป
ย้อนหลัง 3 เดือน (ใบแจ้งซ่อมดึงตั้งแต่ต้นปีก่อนเสมอ) ตอบ `update summary from api success`

1. ตั้ง `SYNC_TOKEN` ใน `backend/.env` เป็นข้อความสุ่มยาว ๆ แล้ว restart Django
   (ไม่ตั้ง = ปิดใช้งาน) ส่งรหัสใน header `X-Sync-Token` เท่านั้น ไม่รับใน URL
2. Windows Task Scheduler: Daily 06:00 (ก่อนรายงาน 07:00), Program `curl.exe`,
   Arguments `-fsS -H "X-Sync-Token: <SYNC_TOKEN>" http://127.0.0.1:8001/api/update_summary_from_api/`

ตอบ 403 = รหัสไม่ถูก · 503 = ยังไม่ได้ตั้งค่า webstock · 502 = ดึงไม่ได้เลยสักขั้น
(ขั้นที่ดึงไม่ได้บางขั้นจะข้ามไปและเก็บข้อมูลเดิมไว้)

ค่าซ่อม/น้ำมัน/ชั่วโมงทำงานเก็บเป็นรายเดือน รายงานรายสัปดาห์จึงแสดงเป็นยอดสะสมของเดือน
ส่วนการแจ้งซ่อม/ปิดงานนับตามวันที่จริง · ฟอนต์ IBM Plex Sans Thai (OFL) อยู่ใน `dbapp/reports/fonts`

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
| GET | `/api/update_summary_from_api/` (header `X-Sync-Token`) | งานอัปเดตอัตโนมัติทุกวัน |

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
dbapp/reports/          รายงาน PDF ทางอีเมล (period, data, pdf, send)
dbapp/management/       คำสั่ง send_fleet_reports
dbapp/api/              serializers, views, urls ของ DRF
dbapp/tests/            pytest (ใช้ SQLite ในหน่วยความจำ)
```
