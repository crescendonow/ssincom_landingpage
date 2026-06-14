# Add Sand Sales Dashboard (`dashboard_sand.html`)

## Context

ต้องการ dashboard สรุปยอดขายทรายแบบ drill-down (รายปี → ราย 6 เดือน → รายเดือน → รายใบกำกับ)
โดยดึงข้อมูลจากระบบ billing แยกต่างหาก (`ssincombill-production.up.railway.app`)
ซึ่งมี API สาธารณะ (ไม่มี auth guard) แต่ต่าง origin → ต้องมี proxy ใน landing page backend เพื่อแก้ CORS

โครงสร้างอ้างอิงจากไฟล์ Excel ตัวอย่าง:
`C:\DATA\SSINCOM\Natirat_Acc\สรุปรายละเอียดซื้อ-ขายทราย\2568\สรุปรายละเอียดซื้อ-ขายทรายปี 2025.xlsx`

---

## Source APIs (billing app)

**Base URL:** `https://ssincombill-production.up.railway.app` (ตั้งค่าผ่าน `BILL_BASE_URL`)

### `GET /api/saletax/summary`
Query params: `granularity=year|month`, `year=YYYY`, `month=YYYY-MM`

Response array:
```json
[{ "period": "2025", "count": 120, "before_vat": 500000.00, "vat": 35000.00, "grand": 535000.00 }]
```

### `GET /api/saletax/list`
Query params: `month=YYYY-MM`, `year=YYYY`, `start=YYYY-MM-DD`, `end=YYYY-MM-DD`

Response array:
```json
[{
  "idx": 1, "invoice_number": "INV-001", "invoice_date": "2025-01-15",
  "company": "บริษัท ก จำกัด", "personid": "C001", "cf_taxid": "1234567890123",
  "branch_text": "สำนักงานใหญ่", "sum_qty": 12.500,
  "before_vat": 25000.00, "vat": 1750.00, "grand": 26750.00,
  "driver_name": "นาย ก ข", "items": [{"cf_itemid": "S01", "cf_itemname": "ทรายหยาบ"}]
}]
```

---

## Files to Change

### 1. `requirements.txt`
เพิ่ม `httpx==0.28.1` สำหรับ async HTTP client ใน proxy

### 2. `backend/config.py`
เพิ่ม field ใน `Settings` dataclass:
```python
bill_base_url: str
```
เพิ่มใน `get_settings()`:
```python
bill_base_url=os.getenv("BILL_BASE_URL", "https://ssincombill-production.up.railway.app"),
```

### 3. `backend/main.py`
เพิ่ม `import httpx` และ `from urllib.parse import urlencode`

เพิ่ม 2 proxy routes (วางก่อน `app.mount("/frontend", ...)`):

```python
@app.get("/api/dashboard/saletax_summary")
async def proxy_saletax_summary(request: Request) -> JSONResponse:
    params = dict(request.query_params)
    url = f"{settings.bill_base_url}/api/saletax/summary"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
    return JSONResponse(content=r.json(), status_code=r.status_code)

@app.get("/api/dashboard/saletax_list")
async def proxy_saletax_list(request: Request) -> JSONResponse:
    params = dict(request.query_params)
    url = f"{settings.bill_base_url}/api/saletax/list"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
    return JSONResponse(content=r.json(), status_code=r.status_code)
```

ต้อง import เพิ่ม: `from fastapi import Request`, `from fastapi.responses import JSONResponse`

### 4. `.env.example`
เพิ่มบรรทัด:
```
BILL_BASE_URL=https://ssincombill-production.up.railway.app
```

### 5. `frontend/dashboard_sand.html` (ไฟล์ใหม่)

Standalone HTML — ใช้ Tailwind CSS CDN + Google Fonts (Kanit) ให้สอดคล้องกับ landing page

#### โครงสร้าง UI
```
[หัว: โลโก้ + ชื่อ "รายงานยอดขายทราย"]

[ส่วนกรอง: ปีที่ต้องการดู (dropdown ทุกปี/2024/2025)]

[ตารางสรุปรายปี]
  ▼ ปี 2568 (2025)  |  120 ใบ  |  2,500.000 ตัน  |  500,000.00  |  35,000.00  |  535,000.00
      ▼ ม.ค. - มิ.ย. (H1)  |  60 ใบ  |  1,200.000 ตัน  |  240,000.00  |  ...
            ▼ มกราคม 2568  |  10 ใบ  |  ...
                  [ตารางใบกำกับ: วันที่ | เลขที่ | บริษัท | ตัน | มูลค่า | VAT | รวม]
            ► กุมภาพันธ์ 2568  | ...
            ...
      ► ก.ค. - ธ.ค. (H2)
  ► ปี 2567 (2024)
```

#### Column headers ตาราง
| ระดับ | Columns |
|-------|---------|
| ปี | ปี (พ.ศ.) \| จำนวนใบกำกับ \| จำนวนตัน \| มูลค่าก่อน VAT \| VAT (7%) \| รวมทั้งสิ้น |
| 6 เดือน | ครึ่งปี \| จำนวนใบกำกับ \| จำนวนตัน \| มูลค่าก่อน VAT \| VAT (7%) \| รวมทั้งสิ้น |
| เดือน | เดือน \| จำนวนใบกำกับ \| จำนวนตัน \| มูลค่าก่อน VAT \| VAT (7%) \| รวมทั้งสิ้น |
| ใบกำกับ | วันที่ \| เลขที่ \| รหัส \| ชื่อบริษัท \| Tax ID \| สถานที่ \| คนขับ \| รหัสสินค้า \| สินค้า \| ตัน \| มูลค่า \| VAT \| รวม |

#### Data flow (JavaScript)
1. **Load**: `GET /api/dashboard/saletax_summary?granularity=year` → แสดงทุกปี collapsed
2. **Click ปี**: `GET /api/dashboard/saletax_summary?granularity=month&year=YYYY` → จัดกลุ่ม H1 (month 1-6) / H2 (month 7-12) ใน JS
3. **Click H1/H2**: ขยายแสดงรายเดือนจากข้อมูลที่ดึงมาแล้ว (ไม่ต้อง API call ซ้ำ)
4. **Click เดือน**: `GET /api/dashboard/saletax_list?month=YYYY-MM` → แสดงตารางใบกำกับ

#### Style
- พื้นหลังขาว/เทาอ่อน, header row: `#2d2d2d` (charcoal), accent: `#c9a84c` (gold) — สอดคล้องกับ landing page
- Row indent ตาม level (pl-4, pl-8, pl-12)
- ▶/▼ triangle icon toggle แต่ละ row
- ตัวเลขจัดขวา, format `,` thousands separator, ทศนิยม 2 หลัก (ตัน: 3 หลัก)
- Responsive: horizontal scroll บน mobile

---

## Serving the File

`dashboard_sand.html` จะถูก serve โดย `StaticFiles` mount ที่ `/frontend` (มีอยู่แล้วใน `main.py`) →
เข้าถึงได้ที่ `/frontend/dashboard_sand.html`

ไม่ต้องเพิ่ม route ใหม่สำหรับ HTML file

---

## Railway Environment Variable

เพิ่มใน Railway Variables:
```
BILL_BASE_URL=https://ssincombill-production.up.railway.app
```

(ถ้าไม่ตั้ง จะใช้ default URL นั้นอยู่แล้ว แต่ควรตั้งอย่างชัดเจน)

---

## Verification

1. รัน local: `uvicorn backend.main:app --reload`
2. เปิด `http://127.0.0.1:8000/api/dashboard/saletax_summary?granularity=year` → ต้องได้ JSON array
3. เปิด `http://127.0.0.1:8000/api/dashboard/saletax_list?month=2025-01` → ต้องได้ JSON array
4. เปิด `http://127.0.0.1:8000/frontend/dashboard_sand.html` → ต้องเห็น dashboard โหลดข้อมูลปีอัตโนมัติ
5. ทดสอบ drill-down: คลิกปี → ครึ่งปี → เดือน → ใบกำกับ
6. Deploy Railway → ตรวจ `/frontend/dashboard_sand.html` บน production
