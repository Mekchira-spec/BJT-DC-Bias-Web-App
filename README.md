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

## ติดตั้งและรัน (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิดเบราว์เซอร์ที่ **http://127.0.0.1:5000/**

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
