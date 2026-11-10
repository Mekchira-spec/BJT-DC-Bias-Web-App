# Add Zoom Support + Circuit Diagram

> Small change — user approved the approach verbally. Plan written here for the record; implementation follows in this same session.

**Goal:** หน้าเว็บ BJT DC Bias ซูม/ขยายได้บนเบราว์เซอร์และมือถือ และมีรูปวงจร BJT Voltage-Divider Bias แสดงเหนือฟอร์มกรอกค่า

**Architecture:** เพิ่ม `user-scalable=yes` ใน viewport meta; แทรก `` static/images/bjt-voltage-divider.svg` (ไม่มีสมการ ไม่มีตัวเลข มีแต่ label ตัวอุปกรณ์) ไว้เหนือ `<form>`; ปรับ CSS ให้ตัวหนังสือและตารางขยายอ่านง่ายเมื่อซูม

**Tech Stack:** SVG, HTML (Jinja), CSS — ไม่มี JavaScript ตาม AGENTS.md

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md` + AGENTS.md (ห้ามฝังสมการใน template)

## Global Constraints

- ใช้ `unittest` เท่านั้น; รัน `python -m unittest discover -s tests -v`
- ห้ามมี JavaScript
- ห้าม hardcode ผลลัพธ์ใน template
- สมการ/ค่าคงที่ต้องอยู่ใน `dc_bias.py` เท่านั้น — SVG มี label ตัวอุปกรณ์เท่านั้น (R1, R2, RC, RE, VCC, Q1, GND) ไม่มีตัวเลขหรือสูตร
- UI ภาษาไทย; identifier เป็นภาษาอังกฤษ

## Review Focus

1. **หน้าเว็บซูมไม่ออกบนมือถือ** → viewport ต้องมี `user-scalable=yes`
2. **ไม่มีรูปวงจรประกอบ** → ต้องมี `` ชี้ไปที่ static images ของวงจร
3. **รูปวงจรต้องไม่มีสมการหรือค่าคงที่** → label ตัวอุปกรณ์เท่านั้น

---

### Task 1: เขียนเทสต์ล้มเหลวก่อน (TDD RED)

**Files:**
- Modify: `tests/test_web.py`

- [ ] **Step 1: เขียน failing test** — เพิ่ม 2 test ใน `TestWeb`:

```python
def test_viewport_allows_zoom(self):
    res = self.client.get("/")
    self.assertIn(b"user-scalable=yes", res.data)

def test_circuit_diagram_image_present(self):
    res = self.client.get("/")
    self.assertIn(b"bjt-voltage-divider.svg", res.data)
```

- [ ] **Step 2: รันให้เห็นว่า FAIL**

Run: `python -m unittest tests.test_web -v`
Expected: FAIL — `AssertionError: "user-scalable=yes"` not found และ `bjt-voltage-divider.svg` not found

---

### Task 2: สร้าง SVG วงจร + แก้ template + แก้ CSS (TDD GREEN)

**Files:**
- Create: `static/images/bjt-voltage-divider.svg`
- Modify: `templates/index.html`
- Modify: `static/style.css`

- [ ] **Step 1: สร้างไฟล์ SVG วงจร**

วาดวงจร NPN Voltage-Divider Bias แบบส케ตช์:
- VCC ด้านบน → R1 → ฐาน Q1 → R2 → GND
- VCC → RC → คอลเลกเตอร์ Q1
- อิมิตเตอร์ Q1 → RE → GND
- มี label ตัวอุปกรณ์เท่านั้น (R1, R2, RC, RE, VCC, Q1, GND) **ห้ามมีตัวเลขหรือสมการ**

- [ ] **Step 2: แก้ `templates/index.html`**

- เปลี่ยนบรรทัด 5 จาก `<meta name="viewport" content="width=device-width, initial-scale=1">`
  เป็น `<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=yes">`
- แทรก `<img src="..." alt="วงจร BJT Voltage-Divider Bias" class="circuit">` เหนือ `<form>` (หลัง `{% if errors %}` block ก่อน `<form>`)

- [ ] **Step 3: แก้ `static/style.css`**

เพิ่ม CSS สำหรับ `.circuit`:
```css
.circuit {
  width: 100%;
  max-width: 520px;
  height: auto;
  display: block;
  margin: 0 auto 18px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
}
```
และปรับ `main` ให้ไม่ตัดข้อความเมื่อซูม (ลบ `overflow` ที่อาจซ่อน ถ้ามี; เพิ่ม `max-width: none` บน mobile หรือให้ `.results` และ `table` ขยายได้)

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `python -m unittest tests.test_web -v`
Expected: PASS 8 tests (6 เดิม + 2 ใหม่)

Run: `python -m unittest discover -s tests -v`
Expected: PASS 26 tests (24 เดิม + 2 ใหม่)

- [ ] **Step 5: Commit checkpoint (GitHub Desktop)**
Summary: `feat: add zoom support and BJT circuit diagram to web UI`

---

## หมายเหตุ

การเพิ่ม `user-scalable=yes` ไม่ทำให้หน้าเว็บเสียบนเดสก์ท็อป และ SVG แยกไฟล์ทำแก้รูปได้โดยไม่แตะ HTML หลังจากนี้
