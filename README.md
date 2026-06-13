# SS Incom Landing Page

Landing page ของ S&S Incom ที่ deploy เป็น FastAPI application เดียวบน Railway โดย FastAPI ทำหน้าที่ serve frontend static files และ backend API สำหรับ contact form

## Architecture Overview

ระบบแบ่งเป็น 3 ส่วนหลัก:

1. **Frontend**
   - อยู่ใน `frontend/`
   - แยกไฟล์เป็น `index.html`, `styles.css`, และ `app.js`
   - เรียก backend API ผ่าน path เดียวกันกับเว็บ เช่น `/api/pdgroups` และ `/api/contact`
   - Contact form โหลดรายการ product group จาก database แทนการ hardcode

2. **Backend**
   - ใช้ Python FastAPI
   - Entry point คือ `backend.main:app`
   - เชื่อม PostgreSQL ด้วย `asyncpg`
   - ใช้ environment variables จาก Railway หรือ local `.env`
   - Serve frontend ผ่าน `StaticFiles` ที่ path `/`

3. **External Services**
   - PostgreSQL database สำหรับ `quotation.pdgroup` และ `quotation.contact_customer`
   - SMTP provider สำหรับส่ง email หลังบันทึก contact request สำเร็จ
   - Railway สำหรับ runtime, deploy, และ variables

## Components

### Frontend

- `frontend/index.html`  
  โครงสร้างหน้า landing page และ contact form

- `frontend/styles.css`  
  styling ของหน้าเว็บ

- `frontend/app.js`  
  จัดการ interaction ฝั่ง browser:
  - toggle ภาษา
  - tab สินค้า
  - โหลด product groups จาก `GET /api/pdgroups`
  - submit contact form ไปที่ `POST /api/contact`

### Backend API

- `GET /api/health`  
  ใช้ตรวจสอบว่า FastAPI app ทำงานอยู่

- `GET /api/pdgroups`  
  อ่านข้อมูลจาก `quotation.pdgroup` และคืนค่า `pdgroup_id`, `pdgroup_name` สำหรับ dropdown ใน contact form

- `POST /api/contact`  
  รับข้อมูล contact form, validate `pdgroup_id`, insert ลง `quotation.contact_customer`, แล้วส่ง email notification ไปยัง recipients ที่กำหนดไว้

### Database

Backend ใช้ schema/table ต่อไปนี้:

- `quotation.pdgroup`
  - เก็บรายการ product group
  - ใช้ field `pdgroup_id` และ `pdgroup_name` สำหรับ dropdown

- `quotation.contact_customer`
  - เก็บข้อมูลที่ลูกค้ากรอกจาก contact form
  - field `pdgroup_id` อ้างอิงกับ `quotation.pdgroup`

### Email

หลังจาก insert contact request ลง database สำเร็จ backend จะส่ง email ผ่าน SMTP ไปยัง recipients ที่กำหนดใน `CONTACT_MAIL_RECIPIENTS`

ถ้า email ส่งไม่สำเร็จหลังจาก insert DB แล้ว backend จะ log error และยังตอบ frontend ว่าส่งฟอร์มสำเร็จ เพื่อไม่ให้ข้อมูล contact request สูญหาย

## Environment Variables

ตั้งค่าบน Railway Variables หรือ local `.env` ตาม template ใน `.env.example`

```env
DATABASE_URL=postgresql://user:password@host:5432/database_name

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=mailbox@example.com
SMTP_PASSWORD=change-me
SMTP_FROM=mailbox@example.com
SMTP_USE_TLS=true
CONTACT_MAIL_RECIPIENTS=contact@ssincom.com,mailtossincom@gmail.com
```

หมายเหตุ:

- `DATABASE_URL` จำเป็นสำหรับการ start backend
- `SMTP_HOST` คือ host จาก mail provider เช่น `smtp.gmail.com`
- ถ้าใช้ port `587` ให้ตั้ง `SMTP_USE_TLS=true`
- ถ้าใช้ port `465` ให้ตั้ง `SMTP_USE_TLS=false`
- `.env` ใช้เฉพาะ local development และไม่ควรถูก commit

## Railway Deployment

Start command:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

โปรเจกต์มี `Procfile` และ `nixpacks.toml` สำหรับให้ Railway run ด้วย command เดียวกัน

Railway ต้องตั้ง variables อย่างน้อย:

```env
DATABASE_URL=postgresql://...
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=mailbox@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=mailbox@example.com
SMTP_USE_TLS=true
CONTACT_MAIL_RECIPIENTS=contact@ssincom.com,mailtossincom@gmail.com
```

## Local Development

ติดตั้ง dependencies:

```bash
pip install -r requirements.txt
```

สร้างไฟล์ `.env` จาก `.env.example` แล้วใส่ค่าจริงสำหรับ local

รันแอป:

```bash
uvicorn backend.main:app --reload
```

จากนั้นเปิด:

```text
http://127.0.0.1:8000/
```

## Verification

ตรวจ syntax Python backend:

```powershell
python -m py_compile .\backend\__init__.py .\backend\config.py .\backend\database.py .\backend\emailer.py .\backend\main.py .\backend\schemas.py
```

ตรวจ syntax frontend JS:

```powershell
node --check .\frontend\app.js
```

ทดสอบ import FastAPI app:

```powershell
python -c "import backend.main; print(backend.main.app.title)"
```

หลัง deploy บน Railway ให้ตรวจ:

- เปิด `/api/health`
- เปิด `/api/pdgroups`
- submit contact form จากหน้าเว็บ
- ตรวจ row ใหม่ใน `quotation.contact_customer`
- ตรวจ email ที่ `contact@ssincom.com` และ `mailtossincom@gmail.com`

