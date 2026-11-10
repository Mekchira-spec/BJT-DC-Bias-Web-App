# Design — BJT DC Bias Web App (ENG29 2121 · Lab 02)

สถานะ: **รออนุมัติ** · วันที่: 2026-11-10 · แนวทางที่เลือก: **B (thin Flask route + pure engineering module + Jinja + CSS + tests)**

## 1. Intent และเหตุผล
นักศึกษา (ปี 2 วิศวกรรมไฟฟ้า) ต้องส่งงาน Lab 02 ที่เป็น **Web Application จริง** ไม่ใช่ไฟล์ HTML ที่เปิดด้วย `file://` เป้าหมายคือให้เห็นเส้นทางข้อมูล Browser → Flask → Python → ผลลัพธ์ และสามารถอธิบาย/ตรวจสอบผลคำนวณด้วยตนเองได้ งานนี้จึงต้องแยก "สมการ" ออกจาก "การรับส่ง HTTP" ให้ชัด และต้องมีหลักฐานการทดสอบ

## 2. Goals
- เปิดผ่าน `http://127.0.0.1:5000/` ได้ และเห็นฟอร์มกรอกค่า
- รับ `VCC, R1, R2, RC, RE, β, VBE` แล้วให้ Python คำนวณ DC Operating Point จริง (ไม่มีผลลัพธ์ฝังใน HTML)
- แสดง `VB, VE, VC, VCE, IC` พร้อมหน่วย (เพิ่ม `IB, IE` และ `VTH, RTH` เพื่อการตรวจสอบ)
- ตรวจ input ผิดและแจ้งข้อความที่อ่านรู้เรื่องโดยหน้าเว็บไม่ล้ม (HTTP 200 + ข้อความ)
- จำแนก `ACTIVE / CUTOFF / SATURATION` และเตือนเมื่อสมมติฐาน Forward-Active ใช้ไม่ได้
- มี automated tests: ≥3 ด้านคณิตศาสตร์ + ≥1 ผ่าน Flask test client
- `README` ทำให้ clone แล้วติดตั้ง/รัน/ทดสอบได้จริง

## 3. Non-goals
AC small-signal, Bode plot, Transient, Signal generator, Overlay animation, DC load line, SPICE/ngspice, ตัวเลือก Bias แบบอื่น, FET, ระบบ login/ฐานข้อมูล

## 4. Anti-goals (ทำงานได้แต่ถือว่าล้มเหลว)
- ผลลัพธ์ hardcode หรือคำนวณฝั่ง JavaScript แทน Python
- หน้าเว็บพัง (500) เมื่อผู้ใช้กรอกค่าผิด
- รายงานตัวเลขใน Saturation/Cutoff ว่า "ใช้ได้" โดยไม่มีคำเตือน
- Commit `.venv/`, `__pycache__/`, `.env` หรือ credential
- เทสต์ที่ "ผ่าน" โดยไม่ได้รันจริง

## 5. Constraints
- Windows, Python 3.15.2, Flask 3.1.3 (ติดตั้งใน `.venv` เท่านั้น)
- เวลาคาบจำกัด (เป้าพัฒนา ≤ 75 นาที) → ต้องเรียบง่ายที่สุดที่ผ่านเกณฑ์
- commit/push ผ่าน **GitHub Desktop เท่านั้น** (git CLI ไม่อยู่ใน PATH ของเครื่อง)
- โฟลเดอร์โปรเจกต์: `C:\Users\B6822187\Documents\GitHub\BJT DC Bias Web App` (มี remote `Mekchira-spec/BJT-DC-Bias-Web-App` แล้ว)

## 6. Approaches
| | แนวทาง | Trade-off | ผล |
|---|---|---|---|
| A | ไฟล์เดียว `app.py` + `render_template_string` | เร็ว แต่ตกเกณฑ์ multi-file/backend และอธิบายสถาปัตยกรรมไม่ได้ | ตัดออก |
| **B** | Route บาง + โมดูลวิศวกรรมบริสุทธิ์ + Jinja + CSS + tests | ตรง A1–A7, แยกหน้าที่ชัด, เสี่ยงต่ำ | **เลือก** |
| C | เพิ่ม service layer + JSON API + JS fetch | สมจริงกว่า แต่เพิ่ม JS/error handling เสี่ยงไม่ทันคาบ | ตัดออก |

## 7. โครงไฟล์
```
app.py                     # Flask routes + form parsing เท่านั้น
dc_bias.py                 # สมการ + validation + region classification (ไม่ import Flask)
templates/index.html       # ฟอร์ม + ผลลัพธ์ (Jinja) — ไม่มีสมการฟิสิกส์
static/style.css           # การจัดหน้า
tests/test_dc_bias.py      # unit tests ของวิศวกรรม
tests/test_web.py          # Flask test client
requirements.txt           # Flask==3.1.3
.gitignore                 # .venv/, __pycache__/, *.pyc, .env, instance/
README.md                  # ติดตั้ง/รัน/ทดสอบ + ตัวอย่างผล
AGENTS.md                  # กติกาโค้ดสำหรับ AI
docs/design-note.md        # สรุปแบบจำลองและสมมติฐาน
docs/validation.md         # ตารางตรวจผลกับค่าคำนวณอิสระ
docs/reflection.md         # สิ่งที่เรียนรู้/ข้อจำกัด
docs/preflight-checklist.md# (มีแล้ว) หลักฐานก่อนเริ่มงาน
docs/superpowers/specs/    # เอกสาร design นี้
```

## 8. โมเดลวิศวกรรม
Forward-Active, β และ VBE คงที่:

```
VTH = VCC·R2/(R1+R2)        RTH = R1·R2/(R1+R2)
IB  = (VTH − VBE)/(RTH + (β+1)·RE)
IC  = β·IB                  IE = (β+1)·IB
VE  = IE·RE                 VB = VE + VBE
VC  = VCC − IC·RC           VCE = VC − VE
```
ค่าคงที่: `VCE_SAT = 0.30 V`

### กติกาการจำแนก Region (ตัดสินใจแล้ว)
| เงื่อนไข | สถานะ | ค่าที่รายงาน | ข้อความ |
|---|---|---|---|
| `VTH ≤ VBE` (ได้ IB ≤ 0) | **CUTOFF** | `IB=IC=IE=0`, `VE=0`, `VB=VTH`, `VC=VCC`, `VCE=VCC` | "Forward-Active ใช้ไม่ได้: VTH ≤ VBE (Transistor Cutoff)" — ไม่โชว์กระแสติดลบที่ไร้ความหมาย |
| `VCE < 0.30 V` | **SATURATION** | แสดงค่าที่สมการคำนวณได้ตามจริง | "ค่าเหล่านี้มาจากสมการ Forward-Active ซึ่งไม่ใช้ได้ใน Saturation — ใช้เพื่อการเรียนเท่านั้น" |
| อื่น ๆ | **ACTIVE** | แสดงค่าปกติ | "Forward-Active approximation ใช้ได้" |

> เหตุผล: รักษาความโปร่งใสของสมการ (ผู้เรียนเห็นว่าสมการให้อะไร) แต่ไม่ปล่อยให้ตัวเลขที่ผิดสมมติฐานถูกอ่านว่าใช้ได้ — ตรงกับเกณฑ์ A5

## 9. Validation
| อินพุต | กติกา | ผลเมื่อผิด |
|---|---|---|
| ทุกช่อง | ต้องมีค่า, เป็นตัวเลขได้ | error รายฟิลด์ "กรุณากรอกตัวเลข" |
| `VCC` | > 0 | error |
| `R1, R2, RC, RE` | > 0 (หลังแปลงหน่วยเป็น Ω) | error |
| `β` | > 0 | error |
| `VBE` | `0 ≤ VBE < VCC` | error |
| หน่วยตัวต้านทาน | `kΩ` (ค่าเริ่มต้น) หรือ `Ω` | แปลงเป็น Ω ก่อนคำนวณเสมอ |

ข้อผิดพลาดทั้งหมดต้อง render หน้าเดิมพร้อมข้อความ (HTTP 200) ไม่ throw ออกไปเป็น 500

## 10. HTTP / Data flow
| Route | Method | ทำงาน |
|---|---|---|
| `/` | GET | แสดงฟอร์ม (prefill ค่าตัวอย่างของ Lab) |
| `/calculate` | POST | parse form → `dc_bias.calculate(...)` → render `index.html` พร้อมผลหรือ error |

`app.py` มีหน้าที่แค่ parse/แปลง/เรียก/ส่งต่อ — ไม่มีสมการ

## 11. UI (ข้อความ ไม่ใช่ pixel spec)
- หัวเรื่อง + คำอธิบายสั้นว่าคำนวณฝั่ง Server
- ฟอร์ม 7 ช่อง + ตัวเลือกหน่วย `kΩ/Ω` + ปุ่ม **Calculate DC Bias**
- กล่องผลลัพธ์: ตาราง `VTH, RTH, IB, IC, IE, VB, VE, VC, VCE` พร้อมหน่วย (V, µA, mA, kΩ)
- ป้ายสถานะสี: เขียว = ACTIVE, ส้ม = SATURATION, แดง = CUTOFF + คำอธิบาย
- กล่อง error รวมด้านบนฟอร์ม เมื่อ input ผิด
- ใช้ CSS ไฟล์เดียว รองรับจอเล็ก (ไม่ต้องมี JS)

## 12. Tests
`tests/test_dc_bias.py`
1. ชุดค่าอ้างอิงของ Lab ตรงกับ oracle (VTH 2.1639 V, IB 12.30 µA, IC 1.2299 mA, IE 1.2422 mA, VE 1.2422 V, VB 1.9422 V, VC 9.2943 V, VCE 8.0522 V) และ `region == ACTIVE`
2. แปลงหน่วย: ให้ค่าเป็น Ω ตรง ๆ กับให้เป็น kΩ + unit flag → ผลเท่ากัน
3. Cutoff: `VTH ≤ VBE` → `region == CUTOFF`, `IC == 0`, `VC == VCC`
4. Saturation: เลือก RC สูง/RE ต่ำให้ `VCE < 0.3` → `region == SATURATION`
5. Validation: `R1=0`, `β=0`, `VCC=-1`, ค่า non-numeric → raise `ValidationError` พร้อมข้อความ

`tests/test_web.py`
1. `GET /` → 200 และมี `name="VCC"`
2. `POST /calculate` ค่าตัวอย่าง → 200, มี `8.052` และ `ACTIVE`
3. `POST /calculate` ค่าผิด → 200, มีข้อความ error และไม่มี traceback
4. `POST /calculate` ขาดฟิลด์ → 200 + error

## 13. การตัดสินใจที่เป็นของผู้สร้าง (builder calls)
- ใช้ `dataclass BiasResult` เป็นผลลัพธ์ (ไม่ใช่ dict) เพื่อให้เทสต์ตรวจทีละฟิลด์
- แสดง `VTH, RTH` ด้วย เพราะช่วยให้นักศึกษาverify สมการขั้นกลางได้
- หน่วย: ตัวเลือกหน่วยรวม `kΩ/Ω` (ไม่แยกต่อช่อง) — ฟอร์มง่ายและยังบังคับการแปลงหน่วยจริง
- Prefill ค่าตัวอย่างของ Lab ในฟอร์ม (ค่า input ไม่ใช่ผลลัพธ์ จึงไม่ขัด A2)
- `VCE_SAT = 0.30 V` เป็นค่าคงที่ที่ประกาศชัดในโค้ดและ README
- ไม่ใช้ JavaScript เลยในเฟสนี้

## 14. สิ่งที่เหลือให้ผู้สร้างตัดสินตอนลงมือ
- การจัดวาง CSS ละเอียด (ไม่กระทบเกณฑ์)
- จำนวนตำแหน่งทศนิยม (กำหนดขั้นต่ำ: V 3 ตำแหน่ง, mA 3 ตำแหน่ง, µA 2 ตำแหน่ง)
- ข้อความไทย/อังกฤษใน UI (เลือกไทยเป็นหลัก)

## 15. การแมปกับเกณฑ์ตรวจรับ
| เกณฑ์ | องค์ประกอบที่รองรับ |
|---|---|
| A1 GET / = 200 + ฟอร์ม | `GET /` + `templates/index.html` |
| A2 POST คำนวณจริง | `POST /calculate` → `dc_bias.calculate` |
| A3 ผลตรงการคำนวณอิสระ | oracle ใน `test_dc_bias.py` + `docs/validation.md` |
| A4 Validation | `ValidationError` + error box |
| A5 นอก Active Region | region classification + warning box |
| A6 Tests | 5 unit + 4 client tests |
| A7 Reproducibility | `README.md` + `requirements.txt` + `.gitignore` |
