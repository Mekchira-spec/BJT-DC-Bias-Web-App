# BJT DC Bias Web App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้าง Flask Web App หลายไฟล์ที่รับค่า VCC, R1, R2, RC, RE, β, VBE แล้วให้ Python คำนวณ DC Operating Point ของวงจร BJT Common-Emitter Voltage-Divider Bias พร้อม validation, region warning และ automated tests ภายในคาบ Lab 02

**Architecture:** Flask route ทำหน้าที่เพียง parse form → เรียก `dc_bias.calculate()` → render Jinja template ส่วนสมการ/validation/region classification อยู่ใน `dc_bias.py` ที่ไม่รู้จัก HTTP เลย ทำให้ทดสอบแยกได้และอธิบาย Frontend/Backend ได้ชัด

**Tech Stack:** Python 3.15.2, Flask 3.1.3, Jinja2, `unittest` (ไม่ใช้ pytest), HTML/CSS (ไม่มี JavaScript)

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`

## Global Constraints

- Python **3.15.2**, Flask **3.1.3** (pin ใน `requirements.txt`), ติดตั้งใน `.venv` เท่านั้น
- ใช้ `unittest` เท่านั้น; รันด้วย `python -m unittest discover -s tests -v`
- **ห้ามมี JavaScript** ในเฟสนี้
- ค่าคงที่ `VCE_SAT = 0.30` (V) ประกาศใน `dc_bias.py`
- ค่าอ้างอิง (oracle) จากชุดทดสอบของ Lab: VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, β=100, VBE=0.70
  → VTH=2.163934426 V, RTH=18032.7868852 Ω, IB=12.2985814626 µA, IC=1.2298581463 mA,
  IE=1.2421567277 mA, VE=1.2421567277 V, VB=1.9421567277 V, VC=9.2943120782 V, VCE=8.0521553505 V
- หน่วย SI ภายในโมดูล: V, A, Ω (template ค่อยแปลงเป็น mA/µA/kΩ เพื่อแสดงผล)
- **Commit ผ่าน GitHub Desktop เท่านั้น** — git CLI ไม่อยู่ใน PATH ของเครื่องนี้ ทุก task จบด้วย commit checkpoint ที่มนุษย์กดเอง
- ห้าม commit `.venv/`, `__pycache__/`, `.env`
- UI ภาษาไทย, ชื่อ identifier/ฟังก์ชันเป็นภาษาอังกฤษ

## Review Focus

อินพุต/เงื่อนไขที่ spec ไม่ได้เขียนไว้แต่มีโอกาสทำให้โปรแกรมพังหรือให้ผลผิด (แต่ละข้อมี test ใน task ที่รับผิดชอบ):

1. **ค่าตัวต้านทานเป็น kΩ ที่มีทศนิยม** (เช่น `2.2`) → ต้องกลายเป็น 2200.0 Ω ไม่ใช่ 2.2 Ω
2. **ช่องว่าง/ฟิลด์หายไปจาก form** → ต้องได้ error รายฟิลด์ ไม่ใช่ `KeyError`/HTTP 500
3. **ค่าที่ทำให้สมการไร้ความหมาย** (`RE=0`, `β=-1`, `VCC=-1`, `R1+R2` เป็นลบ) → ต้องถูกปฏิเสธก่อนคำนวณ
4. **ตัวเลขที่ผู้ใช้พิมพ์จริงแต่ Python ไม่รับ** (`"1,000"`, `"1e999"`, `"--5"`) → ต้องแจ้ง error ไม่ใช่ crash หรือได้ `inf`
5. **`VCE` ติดลบมาก** (RC ใหญ่จัด) → ต้องเป็น `SATURATION` ไม่ใช่ `ACTIVE`

---

### Task 1: Engineering core — `dc_bias.py` (สมการ + dataclass + unit conversion)

**Files:**
- Create: `dc_bias.py`
- Create: `tests/test_dc_bias.py`
- Create: `requirements.txt`
- Create: `.gitignore`

**Interfaces:**
- Produces:
  - `class ValidationError(ValueError)` — มี `errors: dict[str, str]` (ชื่อฟิลด์ → ข้อความ)
  - `@dataclass(frozen=True) class BiasResult` — ฟิลด์ `vth, rth, ib, ic, ie, vb, ve, vc, vce: float`, `region: str`, `warnings: list[str]`
  - `to_ohms(value: float, unit: str) -> float` — `unit` รับ `"kohm"` หรือ `"ohm"`
  - `calculate(vcc, r1, r2, rc, re, beta, vbe) -> BiasResult` — รับค่า **SI ทั้งหมด (V, Ω)**
  - `VCE_SAT: float = 0.30`

- [ ] **Step 1: เขียน failing test สำหรับค่าอ้างอิง + การแปลงหน่วย**

```python
# tests/test_dc_bias.py
import unittest
from dc_bias import calculate, to_ohms

class TestReferenceOperatingPoint(unittest.TestCase):
    def test_lab_reference_values(self):
        r = calculate(vcc=12.0, r1=100_000.0, r2=22_000.0,
                      rc=2_200.0, re=1_000.0, beta=100.0, vbe=0.70)
        self.assertAlmostEqual(r.vth, 2.1639344, places=6)
        self.assertAlmostEqual(r.rth, 18032.786885, places=5)
        self.assertAlmostEqual(r.ib, 12.298549e-6, places=12)
        self.assertAlmostEqual(r.ic, 1.2298549e-3, places=12)
        self.assertAlmostEqual(r.ie, 1.24215345e-3, places=12)
        self.assertAlmostEqual(r.ve, 1.24215345, places=6)
        self.assertAlmostEqual(r.vb, 1.94215345, places=6)
        self.assertAlmostEqual(r.vc, 9.2943192, places=6)
        self.assertAlmostEqual(r.vce, 8.0521657, places=6)
        self.assertEqual(r.region, "ACTIVE")

class TestUnitConversion(unittest.TestCase):
    def test_kohm_with_decimal(self):
        self.assertAlmostEqual(to_ohms(2.2, "kohm"), 2200.0)

    def test_ohm_passthrough(self):
        self.assertAlmostEqual(to_ohms(2200.0, "ohm"), 2200.0)
```

- [ ] **Step 2: รันให้เห็นว่า FAIL**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: สร้าง `dc_bias.py` (สมการ + dataclass + to_ohms)**

Signature ตาม Interfaces ด้านบน; `calculate` ยังไม่ต้องทำ validation/region ครบ (ให้ Task 2) แต่ให้คืน `region="ACTIVE"` และ `warnings=[]` ไว้ก่อน

- [ ] **Step 4: สร้าง `requirements.txt` และ `.gitignore`**

```
# requirements.txt
Flask==3.1.3
```
```
# .gitignore
.venv/
__pycache__/
*.py[cod]
.env
instance/
.pytest_cache/
```

- [ ] **Step 5: รัน test ให้ผ่าน**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: PASS 3 tests

- [ ] **Step 6: Commit checkpoint (มนุษย์กดใน GitHub Desktop)**
ไฟล์: `dc_bias.py`, `tests/test_dc_bias.py`, `requirements.txt`, `.gitignore`
Summary ที่แนะนำ: `feat: add DC bias engineering core with reference test`

---

### Task 2: Validation + Region classification (CUTOFF / SATURATION)

**Files:**
- Modify: `dc_bias.py`
- Modify: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `calculate`, `to_ohms`, `ValidationError`, `BiasResult` จาก Task 1
- Produces: `calculate()` raise `ValidationError` เมื่ออินพุตผิด; `region` ∈ `{"ACTIVE","CUTOFF","SATURATION"}` พร้อม `warnings` ที่มีข้อความภาษาไทย

- [ ] **Step 1: เขียน failing tests สำหรับ validation และ region**

```python
# เพิ่มใน tests/test_dc_bias.py
from dc_bias import ValidationError

class TestValidation(unittest.TestCase):
    def test_rejects_zero_resistor(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate(12.0, 0.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertIn("r1", ctx.exception.errors)

    def test_rejects_nonpositive_beta(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 0.0, 0.70)
        self.assertIn("beta", ctx.exception.errors)

    def test_rejects_negative_vcc(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate(-1.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertIn("vcc", ctx.exception.errors)

    def test_rejects_vbe_at_or_above_vcc(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 12.0)
        self.assertIn("vbe", ctx.exception.errors)

class TestRegions(unittest.TestCase):
    def test_cutoff_when_vth_below_vbe(self):
        # R2 เล็กมาก -> VTH ต่ำกว่า VBE
        r = calculate(12.0, 100_000.0, 1_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(r.region, "CUTOFF")
        self.assertEqual(r.ic, 0.0)
        self.assertEqual(r.vc, 12.0)
        self.assertTrue(r.warnings)

    def test_saturation_when_vce_below_threshold(self):
        # RC ใหญ่จัด -> VCE ติดลบ
        r = calculate(12.0, 100_000.0, 22_000.0, 100_000.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(r.region, "SATURATION")
        self.assertLess(r.vce, 0.30)
        self.assertTrue(r.warnings)

    def test_active_has_no_warnings(self):
        r = calculate(12.0, 100_000.0, 22_000.0, 2_200.0, 1_000.0, 100.0, 0.70)
        self.assertEqual(r.warnings, [])
```

- [ ] **Step 2: รันให้เห็นว่า FAIL**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: FAIL — `ImportError: cannot import name 'ValidationError'`

- [ ] **Step 3: เพิ่ม validation และ region logic ใน `dc_bias.py`**

กติกา (คัดลอกจาก spec §8–9):
- `vcc <= 0`, `r1 <= 0`, `r2 <= 0`, `rc <= 0`, `re <= 0`, `beta <= 0`, `vbe < 0`, `vbe >= vcc` → เก็บลง `errors` แล้ว raise `ValidationError(errors)`
- `VTH <= VBE` → `CUTOFF`: `ib=ic=ie=0.0, ve=0.0, vb=vth, vc=vcc, vce=vcc` + warning ภาษาไทย
- `VCE < VCE_SAT` → `SATURATION`: รายงานค่าจากสมการตามจริง + warning ว่า Forward-Active ใช้ไม่ได้
- อื่น ๆ → `ACTIVE`, `warnings=[]`

- [ ] **Step 4: รัน test ให้ผ่านทั้งหมด**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: PASS 10 tests

- [ ] **Step 5: Commit checkpoint (GitHub Desktop)**
Summary ที่แนะนำ: `feat: validate inputs and classify operating region`

---

### Task 3: Flask app + template + CSS (GET / และ POST /calculate)

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `tests/test_web.py`

**Interfaces:**
- Consumes: `calculate(...) -> BiasResult`, `ValidationError.errors`, `to_ohms`
- Produces: `app` (Flask instance) ที่ import ได้จาก `app.py`; route `GET /`, `POST /calculate`

- [ ] **Step 1: เขียน failing tests ของ HTTP**

```python
# tests/test_web.py
import unittest
from app import app

class TestWeb(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_index_shows_form(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'name="VCC"', res.data)

    def test_post_calculate_returns_results(self):
        res = self.client.post("/calculate", data={
            "VCC": "12", "R1": "100", "R2": "22", "RC": "2.2",
            "RE": "1", "beta": "100", "VBE": "0.70", "unit": "kohm",
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"8.052", res.data)
        self.assertIn(b"ACTIVE", res.data)

    def test_post_invalid_shows_error_not_crash(self):
        res = self.client.post("/calculate", data={
            "VCC": "12", "R1": "0", "R2": "22", "RC": "2.2",
            "RE": "1", "beta": "100", "VBE": "0.70", "unit": "kohm",
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)

    def test_post_missing_field_shows_error(self):
        res = self.client.post("/calculate", data={"VCC": "12", "unit": "kohm"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)

    def test_post_thousands_separator_shows_error(self):
        res = self.client.post("/calculate", data={
            "VCC": "12", "R1": "1,000", "R2": "22", "RC": "2.2",
            "RE": "1", "beta": "100", "VBE": "0.70", "unit": "kohm",
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)

    def test_post_overflow_value_shows_error(self):
        res = self.client.post("/calculate", data={
            "VCC": "12", "R1": "1e999", "R2": "22", "RC": "2.2",
            "RE": "1", "beta": "100", "VBE": "0.70", "unit": "kohm",
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("กรุณากรอก".encode(), res.data)
```

- [ ] **Step 2: รันให้เห็นว่า FAIL**

Run: `python -m unittest tests.test_web -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: สร้าง `app.py`**

- `parse_form(form) -> dict` : อ่านทั้ง 7 ค่า + `unit`, ถ้าขาด/ว่าง/แปลงเป็น float ไม่ได้/**ได้ค่า inf หรือ nan** (เช่น `1e999`) → สะสม error ข้อความ `"กรุณากรอกตัวเลข"`; แปลงตัวต้านทานด้วย `to_ohms`
- `GET /` → render `index.html` พร้อมค่า prefill (12, 100, 22, 2.2, 1, 100, 0.70, unit="kohm")
- `POST /calculate` → ถ้า parse error → render หน้าเดิม + `errors`; ถ้าผ่าน → `calculate()`; ถ้า `ValidationError` → ส่ง `errors` ไปแสดง; สำเร็จ → ส่ง `result`
- **ห้ามมีสมการใน `app.py`**

- [ ] **Step 4: สร้าง `templates/index.html` และ `static/style.css`**

องค์ประกอบขั้นต่ำ: ฟอร์ม 7 ช่อง + select หน่วย `kohm/ohm` + ปุ่ม `Calculate DC Bias`; ตารางผล `VTH, RTH, IB, IC, IE, VB, VE, VC, VCE` พร้อมหน่วย; ป้ายสถานะ `ACTIVE` (เขียว) / `SATURATION` (ส้ม) / `CUTOFF` (แดง); กล่อง error ด้านบนฟอร์ม; `<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">`

- [ ] **Step 5: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: PASS 16 tests (10 + 6)

- [ ] **Step 6: ตรวจด้วยมือ (หลักฐาน A1/A2)**

Run: `python -m flask --app app run --debug` แล้วเปิด `http://127.0.0.1:5000/` กด Calculate ด้วยค่าตัวอย่าง → ต้องเห็น VCE 8.052 V และป้าย ACTIVE

- [ ] **Step 7: Commit checkpoint (GitHub Desktop)**
Summary ที่แนะนำ: `feat: add Flask UI for DC bias calculation`

---

### Task 4: เอกสาร + การตรวจรับครบวงจร

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `docs/design-note.md`
- Create: `docs/validation.md`
- Create: `docs/reflection.md`

**Interfaces:**
- Consumes: ทุกอย่างจาก Task 1–3

- [ ] **Step 1: เขียน `README.md`**

ต้องมี: วิธีสร้าง venv/activate/ติดตั้ง/รัน/ทดสอบ (คำสั่งจริงสำหรับ Windows PowerShell), ชุดค่าตัวอย่าง, ตารางผลที่คาดหวัง, ข้อจำกัด (Forward-Active, VCE_SAT=0.30), และหมายเหตุว่า commit ทำผ่าน GitHub Desktop

- [ ] **Step 2: เขียน `AGENTS.md`**

กติกา: สมการต้องอยู่ใน `dc_bias.py` เท่านั้น, ห้าม hardcode ผลลัพธ์ใน template, ห้ามใช้ JS, test ใหม่ต้องรันจริงก่อนอ้างว่าผ่าน, หน่วย SI ภายในโมดูล

- [ ] **Step 3: เขียน `docs/design-note.md`, `docs/validation.md`, `docs/reflection.md`**

- design-note: สมการ + สมมติฐาน + เหตุผลที่แยกโมดูล
- validation: ตารางเทียบค่าที่เว็บแสดงกับค่าคำนวณมือ (oracle) + เคส CUTOFF/SATURATION
- reflection: สิ่งที่เรียนรู้, ข้อจำกัดของแบบจำลอง, สิ่งที่จะทำต่อ (W3+)

- [ ] **Step 4: ตรวจรับครบวงจร (ต้องรันจริงทุกข้อ)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v      # ต้อง PASS ทั้งหมด
python -m flask --app app run --debug        # เปิด http://127.0.0.1:5000/
```
Expected: tests PASS ทุกตัว; หน้าเว็บคำนวณค่าตัวอย่างได้; กรอก `R1=0` แล้วเห็น error; ใส่ `RC=100` (kΩ) แล้วเห็น SATURATION

- [ ] **Step 5: ตรวจความสะอาดก่อน commit**

Run: `git status --short` (ใช้ git ของ GitHub Desktop แบบ read-only)
Expected: ไม่มี `.venv/`, `__pycache__/`, `.env` อยู่ในรายการ

- [ ] **Step 6: Commit checkpoint (GitHub Desktop) + Push**
Summary ที่แนะนำ: `docs: add README, validation note and reflection`
