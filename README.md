# BJT DC Bias Web App — Lab 03

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจร BJT Common-Emitter แบบ **Voltage-Divider Bias** (NPN) — งาน Lab 02 รายวิชา ENG29 2121

**ต่อยอดใน Lab 03:** เพิ่มการเลือกวงจรไบอัสได้สามแบบ — Voltage Divider (เดิม), Fixed Bias และ Emitter Bias แบบแหล่งจ่ายเดียว — คำนวณด้วย Python ฝั่ง Server และเปรียบเทียบผลบนหน้าเว็บกับค่าที่คำนวณไว้ล่วงหน้า

ผลลัพธ์คำนวณด้วย **Python ฝั่ง Server** (ไม่ใช่ JavaScript และไม่ใช่ค่าที่ฝังใน HTML)

## โครงสร้างโปรเจกต์

```text
app.py                  # Flask routes + parse form + เลือกฟังก์ชันตามโหมด (ไม่มีสมการ)
dc_bias.py              # สมการทั้งสามวงจร + validation + จำแนก Active/Cutoff/Saturation
templates/index.html    # ฟอร์ม + ตัวเลือกโหมด + ผลลัพธ์ (Jinja)
static/style.css        # การจัดหน้า (ไม่มี JavaScript)
static/images/bjt-voltage-divider.svg  # รูปวงจรอ้างอิง
tests/test_dc_bias.py   # unit tests ของวิศวกรรม (15 tests)
tests/test_web.py       # Flask test client (รวมทดสอบโหมดใหม่)
tests/test_launcher.py  # ทดสอบตัวเปิดแอปแบบครั้งเดียว
requirements.txt        # Flask==3.1.3
start.bat               # ดับเบิลคลิกเปิดเว็บได้ทันที (Windows)
run.py                  # ตัว launcher ที่เลือกพอร์ตว่างและเปิดเบราว์เซอร์
README.md               # เอกสารนี้ (วิธีรัน, คำอธิบาย, เกณฑ์ส่งงาน)
docs/                   # design note, validation, reflection, plan
```

## ติดตั้งและรัน (Windows PowerShell)

### วิธีที่ 1 — ดับเบิลคลิก `start.bat` (ง่ายที่สุด)

ดับเบิลคลิกไฟล์ `start.bat` ในโฟลเดอร์โปรเจกต์ → รอให้หน้าต่างสีดำแสดง `Running on http://127.0.0.1:5000` → เบราว์เซอร์จะเปิดเอง

> ปิดหน้าต่างสีดำ = หยุดเว็บ (หน้าต่างนั้นคือตัวเซิร์ฟเวอร์)

ถ้าขึ้น `[ERROR] .venv\Scripts\python.exe not found.` ให้ทำตามขั้นตอนถัดไปก่อนหนึ่งครั้ง

### วิธีที่ 2 — รันผ่าน PowerShell (ครั้งแรก)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

จากนั้นเปิดเว็บ:

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --port 5000
```

หรือใช้ launcher ตัวเดียวกับ `start.bat`:

```powershell
.\.venv\Scripts\python.exe run.py
```

เปิดเบราว์เซอร์ที่ **http://127.0.0.1:5000/** (หรือพอร์ตที่หน้าต่าง console แจ้ง)

> ⚠️ ต้องเปิดผ่าน Flask (localhost) เท่านั้น — การ double-click `templates/index.html` จะไม่มีการคำนวณเพราะไม่มี Python อยู่เบื้องหลัง

## โหมดวงจรที่รองรับ

เลือกได้จากฟอร์มบนหน้าเว็บ:

| โหมด | อินพุตที่ต้องกรอก | สมการ IB |
|---|---|---|
| **Voltage Divider** (เดิม) | VCC, R1, R2, RC, RE, β, VBE | `IB = (VTH − VBE) / (RTH + (β+1)·RE)` |
| **Fixed Bias** (ใหม่) | VCC, RC, RB, β, VBE | `IB = (VCC − VBE) / RB` |
| **Emitter Bias** (ใหม่) | VCC, RC, RB, RE, β, VBE | `IB = (VCC − VBE) / (RB + (β+1)·RE)` |

สมการร่วมทุกโหมด:
- `IC = β · IB`, `IE = (β+1)·IB`
- `VE = IE · RE` (Fixed Bias ใช้ `VE = 0`)
- `VB = VE + VBE`, `VC = VCC − IC · RC`, `VCE = VC − VE`

หน่วยภายในโมดูล: V, A, Ω — แปลงเป็น mA/µA/kΩ ที่ template เท่านั้น

## ชุดค่าอ้างอิง (สำหรับทดสอบ)

**Voltage Divider:** VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V
→ VCE ≈ 8.052 V, IC ≈ 1.230 mA, Region = ACTIVE

**Fixed Bias:** VCC=12 V, RC=2.2 kΩ, RB=1 MΩ, β=100, VBE=0.70 V
→ VCE ≈ 9.514 V, IC ≈ 1.130 mA, Region = ACTIVE

**Emitter Bias:** VCC=12 V, RC=2.2 kΩ, RB=1 MΩ, RE=1 kΩ, β=100, VBE=0.70 V
→ VCE ≈ 8.705 V, IC ≈ 1.026 mA, Region = ACTIVE

## การทดสอบ

### รัน unit tests (Python)

```powershell
python -m unittest discover -s tests -v
```

ผลลัพธ์ที่คาดหวัง: **38 tests ผ่านทั้งหมด** (15 engineering + 23 web/launcher)

### การทดสอบผ่านเบราว์เซอร์ (Lab 03 Acceptance A1–A5)

| ケース | โหมด | อินพุต | สิ่งที่ต้องตรวจ |
|---|---|---|---|
| **A1** | Voltage Divider | R1=100k, R2=22k, RE=1k | ผลต้องตรงกับ Lab 2 เดิม (VCE ≈ 8.052 V) |
| **A2** | Fixed Bias | RB=1 MΩ | คำนวณได้โดยไม่ต้องกรอก RE |
| **A3** | Emitter Bias | RB=1 MΩ, RE=1 kΩ | มีช่อง RE ใช้ค่าได้ |
| **A4** | Emitter Bias | เหมือน A3 แต่ RE=2 kΩ | ทำนายทิศทาง IC ก่อนรัน (เพิ่มหรือลด) |
| **A5** | Fixed Bias | RB=0 | มีข้อผิดพลาด เว็บไม่ล่ม ไม่แสดงผลเก่า |

ค่าอ้างอิงต้องคำนวณมือก่อน แล้วเปรียบเทียบกับผลบนหน้าเว็บ (tolerance: IC ±0.01 mA, VCE ±0.02 V)

## เกณฑ์ให้คะแนน (Lab 03)

| เกณฑ์ | คะแนน |
|---|---|
| โครงสร้างและ Python (แยกฟังก์ชันใหม่ เลือกตามโหมด ส่งผลเป็น dict) | 3 |
| วิศวกรรมและการคงผลเดิม (ทั้งสามโหมดคำนวณถูก Divider ไม่เสีย) | 3 |
| ตรวจฟอร์มและผลจาก Browser (ตาราง A1–A5 ตรวจอินพุตผิดได้ ทวนเอง ≥1 กรณี) | 3 |
| ส่งงานและทำซ้ำได้ (README มีวิธีรัน GitHub URL Commit SHA ระบุส่วนที่ AI ช่วย) | 1 |

## ข้อจำกัดและข้อห้าม

- **สมการฟิสิกส์ทั้งหมดต้องอยู่ใน `dc_bias.py` เท่านั้น** — `app.py` ห้ามมีสูตรคำนวณ
- **`dc_bias.py` ห้าม import Flask หรือรับรู้ HTTP/form/template**
- **`templates/index.html` ห้ามฝังสมการหรือค่าคงที่ทางฟิสิกส์** (นอกจาก label/หน่วย)
- **ห้ามใช้ JavaScript** ในเฟสนี้
- **ห้าม hardcode ผลลัพธ์ลง template**
- **ห้าม commit `.venv/`, `__pycache__/`, `.env`, credential**
- **ห้ามแก้ `VCE_SAT` โดยไม่ปรับเอกสารและเทสต์**

## การส่งงาน (Deliverables)

1. **ลิงก์ GitHub และ Commit SHA** ของงาน Lab 03
2. **ตาราง A1–A5** พร้อมอินพุต ค่าคาดหมาย ผลจริง หน่วย วิธีตรวจ และสถานะ แนบหลักฐานจากหน้าเว็บอย่างน้อยหนึ่งกรณี
3. **ค่าอ้างอิงอิสระ** อย่างน้อยหนึ่งกรณีของโหมดใหม่ (Fixed หรือ Emitter) พร้อมสมการและหน่วย
4. ระบุว่า AI สร้างโค้ดส่วนไหน นักศึกษาตรวจอะไร โค้ดเลือกฟังก์ชันกับแปลงหน่วยอยู่ที่ไหน

## Git

Commit/push ทำผ่าน **GitHub Desktop** (git CLI ไม่ได้อยู่ใน PATH ของเครื่องนี้)

ก่อน Commit ให้เปิด `git diff` และตรวจรายการไฟล์ที่ Stage แล้วด้วย `git diff --staged`  
ไม่ส่ง `.venv`, `.env`, credentials จากนั้น Commit และ Push

คำแนะนำข้อความ commit:
```
feat: add Fixed Bias and Emitter Bias modes for Lab 03
```
