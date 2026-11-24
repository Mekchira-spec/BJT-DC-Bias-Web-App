# Validation — ผลจากเว็บเทียบกับการคำนวณอิสระ

## 1. ชุดค่าอ้างอิงของ Lab
อินพุต: VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V

ค่าที่คำนวณอิสระ (ทดแทนสมการใน `docs/design-note.md` ด้วยมือ/เครื่องคิดเลข):

| ปริมาณ | ค่าอิสระ | ค่าที่เว็บแสดง | ตรงกัน |
|---|---|---|---|
| VTH | 2.163934 V | 2.164 V | ✅ |
| RTH | 18.032787 kΩ | 18.03 kΩ | ✅ |
| IB | 12.298581 µA | 12.30 µA | ✅ |
| IC | 1.229858 mA | 1.230 mA | ✅ |
| IE | 1.242157 mA | 1.242 mA | ✅ |
| VB | 1.942157 V | 1.942 V | ✅ |
| VE | 1.242157 V | 1.242 V | ✅ |
| VC | 9.294312 V | 9.294 V | ✅ |
| VCE | 8.052155 V | 8.052 V | ✅ |
| Region | ACTIVE (VCE ≫ 0.30 V) | ACTIVE | ✅ |

> ค่าอิสระคำนวณด้วยเลขทศนิยมความละเอียดสูง (`decimal`) จากสมการเดียวกับ
> `docs/design-note.md` แล้วจึงนำมาใช้เป็น oracle ใน `tests/test_dc_bias.py`
> (tolerance 6–12 ตำแหน่ง) — ไม่ได้คัดลอกผลจากตัวโปรแกรม

## 2. เคส CUTOFF
อินพุต: R2 = 1 kΩ (ค่าอื่นเดิม)

- VTH = 12 × 1 / 101 = **0.1188 V** → น้อยกว่า VBE = 0.70 V
- ผลที่ต้องได้: `CUTOFF`, `IC = 0`, `VC = VCC = 12 V`, `VCE = 12 V` + คำเตือน
- ตรวจแล้ว: ตรง (มีเทสต์ `test_cutoff_when_vth_below_vbe` และตรวจบน HTTP จริง)

## 3. เคส SATURATION
อินพุต: RC = 100 kΩ (ค่าอื่นเดิม)

- IC = 1.229858 mA → แรงดันตกคร่อม RC = 122.99 V > VCC
- VC = 12 − 122.99 = **−110.99 V**, VCE = −112.23 V → ต่ำกว่า 0.30 V มาก
- ผลที่ต้องได้: `SATURATION` + คำเตือนว่าค่าเหล่านี้มาจากสมการ Forward-Active
  ซึ่งใช้ไม่ได้ — ตรวจแล้ว: ตรง (`test_saturation_when_vce_below_threshold` + HTTP)

## 4. การตรวจสอบอินพุตผิด
| อินพุต | ผลที่ต้องได้ | ตรวจแล้ว |
|---|---|---|
| `R1 = 0` | ข้อความ "R1 ต้องมากกว่า 0" + HTTP 200 | ✅ |
| `β = 0` | ข้อความ "β ต้องมากกว่า 0" | ✅ |
| `VCC = -1` | ข้อความ "VCC ต้องมากกว่า 0" | ✅ |
| `VBE = 12` (= VCC) | ข้อความ "VBE ต้องอยู่ระหว่าง 0 ถึง VCC" | ✅ |
| ช่องว่าง/ฟิลด์หาย | "กรุณากรอกตัวเลข" ต่อฟิลด์ | ✅ |
| `1,000` | "กรุณากรอกตัวเลข" (ไม่ crash) | ✅ |
| `1e999` | "กรุณากรอกตัวเลข" (ไม่กลายเป็น inf) | ✅ |

## 5. วิธีทำซ้ำ
```powershell
python -m unittest discover -s tests -v
python -m flask --app app run --debug
```

---

# Lab 04 — BJT Amplifier Simulator (ngspice จริง)

## สภาพแวดล้อมที่ใช้ตรวจ

| รายการ | ค่าที่ใช้จริง |
|---|---|
| Simulator | **ngspice 47** portable 64-bit (รัน batch ด้วย `-b -o run.log -r run.raw`) |
| ตำแหน่ง | `%USERPROFILE%\ngspice-47\Spice64\bin\ngspice.exe` (ตั้งผ่านตัวแปร `NGSPICE`) |
| SHA256 ของ binary | `59225971BD68CDD1199443649AA4615A9E6D684933F205AB49006A3942518F5A` |
| ข้อความจาก log | `NGSPICE-47, build Aug 11 2026 13:49:23` |
| BJT model | `.model QNPN NPN BF=100` (โมเดลอย่างเดียวที่ใช้ใน netlist ทั้ง 3 analysis) |
| Fixture | VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ, Cin=Cout=10 µF, source 10 mV peak @ 1 kHz |
| เว็บ | Flask 3.1.3 บน `http://127.0.0.1:5000/` |
| เครื่องมือตรวจ | In-app browser ของ OpenCode Desktop (`tabs/snapshot/select/fill/evaluate/screenshot`) — **ไม่ใช่ Playwright MCP** (ไม่ได้ติดตั้ง/ไม่พร้อมในเครื่องนี้) |
| UI polish | ปรับ CSS ด้วยตนเอง — **Impeccable skill ไม่พร้อมใช้** จึงไม่มีก่อน/หลังจาก skill นี้ |

## ตาราง B1–B8 (ผลที่รันจริงจาก browser)

| Case | Method / Input | Expected / Reference | Observed (หน่วยชัดเจน) | Evidence | Status |
|---|---|---|---|---|---|
| **B1 Regression** | เลือก `Analytical` → Divider, Fixed, Emitter ตามชุดค่า Lab 3 | VCE = 8.052 / 9.514 / 8.705 V; IC = 1.230 / 1.130 / 1.026 mA | Divider **VCE 8.052 V, IC 1.230 mA**; Fixed **9.514 V, 1.130 mA**; Emitter **8.705 V, 1.026 mA** — ทั้ง 3 `ACTIVE`, badge บอก `Analytical (Python)` | snapshot ของ `section.results` ทั้ง 3 โหมด; ค่าตรงกับชุดค่าอ้างอิง Lab 03 ใน `README.md` และ `docs/validation.md` §1 | **PASS** |
| **B2 DC SPICE** | เลือก `DC .op (ngspice)` → Run ด้วย fixture | ผลต้องมาจาก ngspice `.op`, มี `VB/VE/VC/VCE/IC`, badge ระบุ engine/model | `VB 1.954 V · VE 1.176 V · VC 9.439 V · VCE 8.263 V · IC 1.164 mA · IE 1.176 mA · IB 11.64 µA`; badge `SPICE · ACTIVE · NGSPICE-47, build Aug 11 2026 13:49:23`; netlist มี `.op` | `details.evidence` แสดง netlist + log tail (`No. of Data Rows : 1`); ค่า DC ของ SPICE ต่างจาก analytical 8.052 V ตามสมมติฐานโมเดล — ไม่ได้อ้างว่าตรงกัน | **PASS** |
| **B3 Change RE** | เปลี่ยน `RE` จาก 1 → **2 kΩ** แล้วรัน DC ซ้ำ | Operating point ต้องเปลี่ยน และ netlist ต้องสะท้อนค่าใหม่ | `IC 1.164 → 0.637 mA`, `VCE 8.263 → 9.312 V`, `VB 1.954 → 2.049 V`; netlist เปลี่ยนเป็น `RE e 0 2k` | ผลก่อน/หลังอ่านจากหน้าเว็บ + ข้อความ netlist ที่แนบในหน้า | **PASS** |
| **B4 AC** | เลือก `AC .ac (ngspice)` → Run, sweep 1 Hz–10 MHz | กราฟ Frequency (Hz) / Gain (dB) / Phase (deg) จากข้อมูลจริง; มีจุด -3 dB หรือระบุว่าไม่พบ | กราฟ 2 รูป, **141 จุด sweep** (1–1e+07 Hz); Gain สูงสุด **1.75 V/V (4.8 dB)**; phase **−180°…−81.4°**; แสดง `not determined in sweep range — ไม่พบจุดตัด -3 dB ภายในช่วงที่ sweep` | polyline ของ SVG มี 141 จุดต่อกราฟ (อ่านจาก DOM จริง); netlist มี `.ac dec 20 1 10meg`; `docs/captures/B4_AC_desktop.jpeg` | **PASS** |
| **B5 Transient** | เลือก `Transient .tran (ngspice)` → Run @ 10 mV peak, 1 kHz | เห็น Vin/Vout กับเวลา (ms, V), Vpp สมเหตุสมผล และกลับเฟส CE | `Vin 20.0 mV Vpp`, `Vout 0.035 V Vpp`, `Gain 1.75 V/V`, `เฟสโดยประมาณ −180°`, `Points 1508`; แกน `Time (ms)` / `Voltage (V)`; legend `Vin`, `Vout`; ข้อความ `สัญญาณขาออกกลับเฟสตามวงจร Common-Emitter` | polyline 240 จุดที่ downsample จาก 1508 จุดจริง; netlist มี `.tran 2u 3m 0 2u` และ `SIN(0 10m 1k …)` | **PASS** |
| **B6 Change Source** | เปลี่ยน amplitude 10 → **20 mV peak** แล้วรัน Transient ซ้ำ | Waveform/ค่าต้องเปลี่ยนตาม amplitude ไม่ใช่กราฟ hard-code | `Vin Vpp 20.0 → 40.0 mV`, `Vout Vpp 0.035 → 0.070 V` (gain คง 1.75 V/V); y-axis tick จาก `±17.5m` → `±34.9m`; netlist เปลี่ยนเป็น `SIN(0 20m 1k …)` | ผลก่อน/หลัง + ข้อความ netlist จาก DOM จริง | **PASS** |
| **B7 Invalid / Fail** | ตั้ง `RE = 0` แล้ว Run DC; ตรวจ error path ของ engine ด้วย unit test | ต้องแจ้ง error, ไม่แสดง results/chart, ไม่มี badge success | ข้อความที่เห็น: `กรุณากรอกข้อมูลให้ถูกต้องแล้วลองอีกครั้ง — analysis — re ต้องมากกว่า 0`; `section.results = false`, `figure.chart = false`, `badge = null` | snapshot ของ `.alert-error` จาก browser จริง; เคส engine หาย/timeout ครอบคลุมใน `tests/test_spice_engine.py` (`test_missing_binary_raises_spice_error`) **แต่ยัง NOT RUN ใน browser** | **PASS** (invalid input) / **NOT RUN** (engine หายใน browser) |
| **B8 UI** | เปิด/เปลี่ยนทั้ง 4 โหมด (`Analytical`, `DC`, `AC`, `Tran`) บน desktop และจำลอง viewport **390 px** ด้วย iframe ของหน้าเดียวกัน แล้วถ่ายภาพ 2 ขนาดจอ | กราฟ/หน่วย/ปุ่มอ่านได้, ไม่มีเนื้อหาสำคัญถูกตัด | **Desktop** (`innerWidth 1056`, `scrollWidth 1041`): 4/4 โหมดไม่มี horizontal overflow; AC มี 2 กราฟ พร้อมแกน `Frequency (Hz)`, `Gain (dB)`, `Phase (deg)`; Tran มี 1 กราฟแกน `Time (ms)`, `Voltage (V)`; ปุ่มกว้าง 178/208 px, font 16 px; badge engine ชัด **Phone 390 px** (`innerWidth 390`, `scrollWidth 375`): 4/4 โหมดไม่มี overflow; AC กราฟกว้าง 313 px, SVG 283 px, axis font 12 px, button font 16 px, ยังเห็น 2 กราฟ; Tran เห็น 1 กราฟ; ไม่มี `.alert-error` | `docs/captures/B8_desktop.jpeg` (desktop, AC), `docs/captures/B8_phone_390px.jpeg` (390 px, AC แบบเต็มหน้า 390×4000); ตรวจ `scrollWidth <= innerWidth` ทั้ง 4 โหมดจาก DOM จริง | **PASS** (ข้อยกเว้น: ใช้ iframe emulation ไม่ใช่เครื่องมือถือจริง) |

## จุดที่ต้องระวัง / ความคลาดเคลื่อน

1. **DC ของ SPICE ≠ DC ของ analytical** — `8.263 V` เทียบ `8.052 V` ต่างเพราะ `dc_bias.py` สมมติ β/VBE คงที่ ส่วน ngspice ใช้ `.model QNPN NPN BF=100` และ coupling capacitor เปิด circuit ใน DC หน้าเว็บแยกป้าย `Analytical (Python)` กับ `SPICE` ไว้เสมอ
2. **-3 dB ไม่มีในช่วง sweep** — ตามใบงานห้ามแต่งตัวเลข ระบบจึงแสดง `not determined in sweep range` แทน
3. **กราฟมาจาก raw file จริง** — `spice_engine.parse_raw()` อ่าน `run.raw` ที่ ngspice เขียน; `charts.py` คำนวณพิกัด SVG จาก array นั้นฝั่ง server ไม่มี JavaScript และไม่มีข้อมูลตัวอย่างฝังใน template
4. **เครื่องมือตรวจรับไม่ตรงตามใบงาน 100%** — ไม่มี Playwright MCP และ Impeccable skill ในสภาพแวดล้อมนี้ จึงใช้ in-app browser ของ OpenCode + ปรับ CSS ด้วยตนเอง และระบุตรงไปตรงมาว่าไม่มีหลักฐานจาก skill ดังกล่าว
5. **Screenshot ไม่ได้พิสูจน์ค่าทางวิศวกรรม** — ตัวเลขในตารางอ่านจาก DOM/netlist/log ที่ browser แสดงจริง มี screenshot เป็นหลักฐานประกอบเท่านั้น
6. **แผนภาพวงจรใน evidence ถูกอัปเดตให้ครบ** — `static/images/bjt-voltage-divider.svg` แสดง `+VCC, GND, Vin, Cin, R1, R2, Base, RC, Q1, Collector, Emitter, RE, Cout, Vout, RL` และต่อเชื่อมถูกต้องตาม Common-Emitter; ตรวจจาก `<text>` ใน SVG ที่ browser โหลดจริง แล้วถ่าย screenshot ใหม่แทนของเดิม (ยังเป็น UI เดิม ไม่ใช่ภาพ generating ภายนอก) ภาพ B8 ถูกถ่ายใหม่ทั้ง desktop และ phone 390 px หลังเปลี่ยนครบทั้ง 4 โหมด

## วิธีทำซ้ำ Lab 04

```powershell
# 1) ติดตั้ง ngspice 47 แบบ portable แล้วชี้ตัวแปร
$env:NGSPICE = Join-Path $env:USERPROFILE 'ngspice-47\Spice64\bin\ngspice.exe'

# 2) รันชุดเทสต์ (ใช้ ngspice จริงใน integration test)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# คาดหวัง: Ran 71 tests ... OK

# 3) เปิดเว็บ
.\.venv\Scripts\python.exe -m flask --app app run --port 5000
# เปิด http://127.0.0.1:5000/ → เลือก DC/AC/Transient → Run SPICE simulation
```
