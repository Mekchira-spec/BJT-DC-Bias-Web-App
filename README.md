# BJT Amplifier Simulator — Lab 04 (ต่อยอดจาก Lab 03)

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจร BJT Common-Emitter (NPN) และจำลอง **Common-Emitter Amplifier ด้วย ngspice จริง** — รายวิชา ENG29 2121

- **Lab 03 (คงไว้ 100%):** เลือก Voltage Divider / Fixed Bias / Emitter Bias คำนวณด้วย Python ฝั่ง Server
- **Lab 04 (ใหม่):** รัน `DC .op`, `AC .ac`, `Transient .tran` ผ่าน ngspice 47 จากภายนอก Flask แล้วอ่านผลจาก `run.raw` จริง
- ผล Analytical กับผล SPICE แสดงแยกป้ายเสมอ ไม่นำมาปนกัน และไม่มีค่าสำเร็จ/กราฟตัวอย่างฝังใน HTML
- กราฟทั้งหมดสร้างเป็น SVG ฝั่ง Server จาก array ที่ parse ได้จาก ngspice — **ไม่มี JavaScript**

> ⚠️ ต้องเปิดผ่าน Flask (localhost) เท่านั้น — การ double-click `templates/index.html` จะไม่มีการคำนวณหรือเรียก ngspice

## ที่มาและ Commit

| รายการ | ค่า |
|---|---|
| GitHub repository | https://github.com/Mekchira-spec/BJT-DC-Bias-Web-App.git |
| Branch | `main` |
| Commit ของโค้ด Lab 04 | `b6cf3914084944935d8b7456f6c4db08c78a02d6` — `feat: integrate ngspice DC/AC/transient simulator (Lab 04)` |
| Commit หลักฐาน/เอกสารล่าสุด | `c16ceb6c4037050b97d64db6686f64ea0b8ddad1` — `fix: capture full 390x4342 phone UI evidence` |
| Commit ก่อนหน้า | `17b797d` |
| หลักฐานตรวจรับ B1–B8 | [`docs/validation.md`](docs/validation.md) |
| ภาพประกอบ | [`docs/captures/`](docs/captures/) — `B8_desktop.jpeg`, `B8_phone_390px.jpeg` (390×4342 px) |

> README นี้เป็นของ **Lab 04** แล้ว (Lab 03 ยังคงไว้เป็น regression) — โค้ด/เอกสาร/ภาพหลักฐานทั้งหมดถูก commit และ push ขึ้น `main` แล้ว ไม่มีสิ่งที่ค้างในเครื่อง

## Dependencies / สิ่งที่ต้องมี

| รายการ | เวอร์ชัน/ตำแหน่งที่ใช้จริง | หมายเหตุ |
|---|---|---|
| Python | 3.10+ (ใช้ type hint แบบ `str \| None`) | ไม่ต้องติดตั้งแพ็กเกจวิศวกรรมเพิ่ม |
| Flask | `Flask==3.1.3` | อยู่ใน [`requirements.txt`](requirements.txt) |
| ngspice | **ngspice 47 portable 64-bit** | **external binary** ไม่ได้ติดตั้งผ่าน `pip` |
| ตำแหน่ง ngspice | `%USERPROFILE%\ngspice-47\Spice64\bin\ngspice.exe` | โปรแกรมจะหาเองจาก `NGSPICE` → `PATH` → `tools/ngspice/bin/ngspice.exe` → path ข้างต้น |
| Git / GitHub Desktop | Git 2.56.1 (ติดตั้งแล้ว) หรือ GitHub Desktop | ใช้ push งานได้ทั้งสองแบบ |

- `ngspice.exe` ที่ใช้ตรวจมี SHA256 `59225971BD68CDD1199443649AA4615A9E6D684933F205AB49006A3942518F5A`
- winget ไม่มีแพ็กเกจ ngspice ในเครื่องนี้ จึงใช้ไฟล์ portable และตั้งค่าผ่านตัวแปร `NGSPICE`
- ถ้าไม่พบ ngspice โหมด SPICE จะแจ้ง error แทนการแสดงผลปลอม

## โครงสร้างโปรเจกต์

```text
app.py                    # Flask routes + อ่าน form + dispatch ไป analytical / SPICE
dc_bias.py                #Lab 03: สมการ 3 วงจร + validation + Active/Cutoff/Saturation
spice_engine.py           #Lab 04: สร้าง netlist, เรียก ngspice, parse raw, จัดการ error
charts.py                 #Lab 04: คำนวณพิกัด SVG จากข้อมูลจริง (server-side)
templates/index.html      #ฟอร์ม + ตัวเลือก analysis + ตารางผล + SVG macro
static/style.css          #layout desktop/mobile, badge, chart, error (ไม่มี JS)
static/images/            #รูปวงจรอ้างอิง
tests/test_dc_bias.py     #Lab 03 engineering unit tests
tests/test_spice_engine.py#Lab 04 adapter + real-ngspice integration tests
tests/test_web.py         #Flask client ทั้ง analytical และ SPICE
tests/test_launcher.py    #ทดสอบ launcher
docs/validation.md        #A1–A5 (Lab 03) + B1–B8 (Lab 04) พร้อมหลักฐาน
docs/captures/            #screenshot desktop/mobile จาก browser จริง
requirements.txt          #Flask==3.1.3
start.bat / run.py        #เปิดเว็บแบบดับเบิลคลิก / เลือกพอร์ตว่าง
README.md                 #เอกสารนี้
```

## ติดตั้งและรัน (Windows PowerShell)

### 1) สร้าง venv และติดตั้ง Flask

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2) ตั้งค่า ngspice (ถ้าไม่ได้อยู่ใน PATH)

```powershell
$env:NGSPICE = Join-Path $env:USERPROFILE 'ngspice-47\Spice64\bin\ngspice.exe'
& $env:NGSPICE -v
```

หรือวาง ngspice ไว้ที่ `%USERPROFILE%\ngspice-47\Spice64\bin\ngspice.exe` แล้วไม่ต้องตั้งตัวแปรก็ได้ (มี fallback)

### 3) เปิดเว็บ

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --port 5000
# หรือ
.\.venv\Scripts\python.exe run.py
# หรือดับเบิลคลิก start.bat
```

เปิด **http://127.0.0.1:5000/** → เลือก `Analytical (Python)` / `DC .op` / `AC .ac` / `Transient .tran` → กด Run

> ปิดหน้าต่าง console = หยุดเซิร์ฟเวอร์

## การใช้งาน

### Lab 03 — Analytical (Regression)

| โหมด | อินพุตที่ต้องกรอก | สมการ IB |
|---|---|---|
| **Voltage Divider** | VCC, R1, R2, RC, RE, β, VBE | `IB = (VTH − VBE) / (RTH + (β+1)·RE)` |
| **Fixed Bias** | VCC, RC, RB, β, VBE | `IB = (VCC − VBE) / RB` |
| **Emitter Bias** | VCC, RC, RB, RE, β, VBE | `IB = (VCC − VBE) / (RB + (β+1)·RE)` |

สมการร่วม: `IC = β·IB`, `IE = (β+1)·IB`, `VE = IE·RE` (Fixed ใช้ 0), `VB = VE + VBE`, `VC = VCC − IC·RC`, `VCE = VC − VE`

หน่วยภายใน: V, A, Ω — แปลงเป็น mA/µA/kΩ เฉพาะตอนแสดงผล

### Lab 04 — SPICE

| Analysis | netlist ที่สร้าง | ผลที่แสดง |
|---|---|---|
| `DC .op` | `.op` | `VB/VE/VC/VCE/IC/IE/IB` + log tail + badge engine |
| `AC .ac` | `.ac dec 20 1 10meg` | Bode magnitude/phase, gain สูงสุด, fL/fH (หรือระบุว่าไม่พบจุดตัด) |
| `Transient .tran` | `.tran 2u 3m 0 2u` | `Vin/Vout` ตามเวลา, Vpp, gain, เฟสโดยประมาณ |

Fixture เริ่มต้น: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ, Cin=Cout=10 µF, `.model QNPN NPN BF=100`, source 10 mV peak @ 1 kHz

### ชุดค่าอ้างอิง Lab 03 (ต้องยังตรงอยู่)

| โหมด | อินพุต | คาดหวัง |
|---|---|---|
| Voltage Divider | VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V | VCE ≈ **8.052 V**, IC ≈ **1.230 mA**, ACTIVE |
| Fixed Bias | VCC=12 V, RC=2.2 kΩ, RB=1 MΩ, β=100, VBE=0.70 V | VCE ≈ **9.514 V**, IC ≈ **1.130 mA**, ACTIVE |
| Emitter Bias | VCC=12 V, RC=2.2 kΩ, RB=1 MΩ, RE=1 kΩ, β=100, VBE=0.70 V | VCE ≈ **8.705 V**, IC ≈ **1.026 mA**, ACTIVE |

## การทดสอบ

```powershell
$env:NGSPICE = Join-Path $env:USERPROFILE 'ngspice-47\Spice64\bin\ngspice.exe'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ผลที่คาดหวัง: **Ran 71 tests ... OK** (รวม integration test ที่เรียก ngspice จริง)

ตรวจรับผ่าน browser ตามตาราง **B1–B8** ใน [`docs/validation.md`](docs/validation.md) — มีค่าที่อ่านจริง หน่วย หลักฐาน และสถานะ PASS/NOT RUN ระบุไว้แล้ว

## วิธีทำงานของโหมด SPICE (ย่อ)

1. `app.py` อ่านฟอร์ม → `spice_engine.py` ตรวจค่าแล้วสร้าง netlist ตาม analysis ที่เลือก
2. เรียก `ngspice -b -o run.log -r run.raw <netlist>` ด้วย `subprocess` แยก process
3. อ่าน `run.raw` ด้วย `spice_engine.parse_raw()` (frequency complex ถูกแปลงเป็น float)
4. `charts.py` คำนวณพิกัด SVG จาก array จริง → Jinja render เป็น `<svg>` (ไม่มี JS/CDN)
5. ถ้า netlist fail / ไม่มี binary / parse ไม่ได้ → แสดง error และ **ไม่มี results/chart**

## ข้อควรระวัง

- ผล DC ของ ngspice (`VCE ≈ 8.263 V`) ไม่เท่ากับ analytical (`8.052 V`) เพราะโมเดลและ coupling capacitor ต่างสมมติฐาน — หน้าเว็บแยกป้ายให้เสมอ
- หา `-3 dB` ไม่เจอในช่วง 1 Hz–10 MHz ระบบจะแสดง `not determined in sweep range` แทนการแต่งตัวเลข
- `.tran 0 3m 0 2u` ใช้ไม่ได้ใน ngspice 47 (`TSTEP is invalid`) จึงใช้ `.tran 2u 3m 0 2u`
- ห้าม commit `.venv/`, `__pycache__/`, `.env`, credential
- ห้ามเพิ่ม JavaScript หรือค่าตัวอย่างลง template

## บทบาท AI กับสิ่งที่นักศึกษาตรวจ

- AI เขียน/ปรับ `spice_engine.py`, `charts.py`, `app.py`, template, CSS และชุดเทสต์ Lab 04 ตาม requirement ที่ให้ไว้
- นักศึกษาตรวจค่าอิสระ Lab 03 (VCE/IC ทั้ง 3 โหมด), เปรียบเทียบ netlist กับ input ที่กรอก และยืนยันว่า SPICE ไม่ได้แทนที่ analytical
- นักศึกษาตรวจ B2–B6 จาก browser จริง: badge engine, 141 จุด AC, Vpp/gain/เฟส transient, และการเปลี่ยน RE/amplitude ต้องเปลี่ยนผล
- นักศึกษาตรวจ B7–B8: input ผิดต้องไม่มีกราฟปลอม, desktop/390 px ต้องไม่มี horizontal overflow
- ข้อจำกัดที่ตรงไปตรงมา: ไม่มี Playwright MCP / Impeccable skill ในเครื่องนี้ จึงใช้ in-app browser ของ OpenCode และปรับ CSS เอง — ไม่มีหลักฐานจากสองเครื่องมือนั้น

## Git

```powershell
$git = 'C:\Users\b6822187\AppData\Local\Programs\Git\cmd\git.exe'
& $git status --short
& $git add README.md docs
& $git commit -m "docs: add Lab 04 ngspice setup and B1-B8 validation evidence"
& $git push origin main
```

Commit/push ผ่าน GitHub Desktop ก็ได้เช่นกัน (.repo เปิดอยู่ใน GitHub Desktop แล้ว) — ตรวจ `git diff --staged` ก่อน commit ทุกครั้ง
