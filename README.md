# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจร BJT Common-Emitter
แบบ **Voltage-Divider Bias** (NPN) — งาน Lab 02 รายวิชา ENG29 2121

ผลลัพธ์คำนวณด้วย **Python ฝั่ง Server** (ไม่ใช่ JavaScript และไม่ใช่ค่าที่ฝังใน HTML)

## โครงสร้าง

```
app.py                  # Flask routes + parse form (ไม่มีสมการ)
dc_bias.py              # สมการ + validation + จำแนก Active/Cutoff/Saturation
templates/index.html    # ฟอร์ม + ผลลัพธ์ (Jinja)
static/style.css        # การจัดหน้า
tests/test_dc_bias.py   # unit tests ของวิศวกรรม (10 tests)
tests/test_web.py       # Flask test client (6 tests)
requirements.txt        # Flask==3.1.3
docs/                   # design note, validation, reflection, plan, checklist
```

## เปิดแอปแบบดับเบิลคลิก (ง่ายที่สุด)

**ดับเบิลคลิก `start.bat`** — จบ ไม่ต้องพิมพ์คำสั่งใด ๆ

สิ่งที่เกิดขึ้น:
1. หน้าต่าง console เปิดขึ้นและแสดงที่อยู่ เช่น `http://127.0.0.1:5000/`
2. เบราว์เซอร์เด้งขึ้นเองพร้อมหน้าเว็บ
3. ถ้า port 5000 ถูกใช้อยู่ จะเลื่อนไป 5001, 5002, ... ให้อัตโนมัติ

> ปิดหน้าต่าง console = หยุดเว็บ (หน้าต่างนั้นคือตัวเซิร์ฟเวอร์)

ถ้าขึ้น `[ERROR] .venv\Scripts\python.exe not found.` แปลว่ายังไม่ได้ติดตั้ง
ให้ทำตามหัวข้อถัดไปก่อนหนึ่งครั้ง

## ติดตั้งครั้งแรก (Windows PowerShell)

```powershell
python -m venv .venv
python -m pip install -r requirements.txt
```

> บนเครื่องที่ PowerShell บล็อกสคริปต์ (`running scripts is disabled`) ไม่ต้องใช้
> `Activate.ps1` — เรียก `.venv\Scripts\python.exe` ตรง ๆ ได้เลย ซึ่งเป็นวิธีที่
> `start.bat` ใช้อยู่แล้ว

## รันแบบ manual (ทางเลือก)

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --port 5000
```

หรือใช้ launcher ตัวเดียวกับที่ `start.bat` เรียก:

```powershell
.\.venv\Scripts\python.exe run.py
```

เปิดเบราว์เซอร์ที่ **http://127.0.0.1:5000/** (หรือ port ที่ console แจ้ง)

> ต้องเปิดผ่าน Flask (localhost) เท่านั้น — การ double-click `templates/index.html`
> จะไม่มีการคำนวณเพราะไม่มี Python อยู่เบื้องหลัง

## ทดสอบ

```powershell
python -m unittest discover -s tests -v
```

## ชุดค่าตัวอย่าง (Lab reference)

| อินพุต | ค่า |
|---|---|
| VCC | 12 V |
| R1 / R2 | 100 kΩ / 22 kΩ |
| RC / RE | 2.2 kΩ / 1 kΩ |
| β | 100 |
| VBE | 0.70 V |

ผลที่คาดหวัง (Forward-Active):

| ปริมาณ | ค่า |
|---|---|
| VTH | 2.164 V |
| RTH | 18.03 kΩ |
| IB | 12.30 µA |
| IC | 1.230 mA |
| IE | 1.242 mA |
| VB | 1.942 V |
| VE | 1.242 V |
| VC | 9.294 V |
| VCE | 8.052 V |
| Region | ACTIVE |

## แบบจำลองและข้อจำกัด

- ใช้ Forward-Active approximation: β คงที่, VBE คงที่
- `VCE_SAT = 0.30 V` ใช้เป็นเกณฑ์ตัดสิน Saturation
- **CUTOFF** (VTH ≤ VBE): รายงาน `IB = IC = IE = 0`, `VB = VTH`, `VC = VCC`
  แทนการแสดงกระแสติดลบที่ไร้ความหมาย
- **SATURATION** (VCE < 0.30 V): แสดงค่าที่สมการให้มา **พร้อมคำเตือน** ว่าใช้ไม่ได้
- ไม่ใช่ SPICE/ngspice และไม่ครอบคลุม AC, Transient, Bode plot

## Git

Commit/push ทำผ่าน **GitHub Desktop** (git CLI ไม่ได้อยู่ใน PATH ของเครื่องนี้)
`.venv/`, `__pycache__/`, `.env` ถูกกันไว้ใน `.gitignore`
