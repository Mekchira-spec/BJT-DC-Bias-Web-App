# Design Note — แบบจำลอง DC Bias

## วงจร
NPN Common-Emitter, Voltage-Divider Bias
- `R1` ต่อระหว่าง VCC–Base, `R2` ต่อระหว่าง Base–Ground (ตัวแบ่งแรงดัน)
- `RC` ต่อ VCC–Collector, `RE` ต่อ Emitter–Ground

## สมมติฐาน
1. Forward-Active: ฐาน-อิมิตเตอร์ไบแอสตรง, คอลเลกเตอร์-เบสไบแอสกลับ
2. `β` คงที่ (ไม่ขึ้นกับ IC และอุณหภูมิ)
3. `VBE` คงที่ตามค่าที่ผู้ใช้กรอก (ปกติ 0.70 V)
4. ตัวต้านทานเป็นอุดมคติ ไม่มีความคลาดเคลื่อน

## สมการ
```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1)·RE)
IC  = β · IB
IE  = (β + 1)·IB
VE  = IE · RE
VB  = VE + VBE
VC  = VCC − IC · RC
VCE = VC − VE
```

## การจำแนก Operating Region
| เงื่อนไข | Region | การรายงาน |
|---|---|---|
| `VTH ≤ VBE` | CUTOFF | `IB=IC=IE=0`, `VE=0`, `VB=VTH`, `VC=VCC`, `VCE=VCC` + คำเตือน |
| `VCE < 0.30 V` | SATURATION | ค่าจากสมการตามจริง + คำเตือนว่าแบบจำลองใช้ไม่ได้ |
| อื่น ๆ | ACTIVE | ค่าปกติ ไม่มีคำเตือน |

**เหตุผลของ CUTOFF:** ถ้าใช้สมการ Forward-Active ตรง ๆ กับกรณี `VTH ≤ VBE`
จะได้ `IB` ติดลบ ซึ่งไม่มีความหมายทางกายภาพ จึงรายงานสถานะ Cutoff แทน
และระบุชัดว่าเป็นผลจากสมมติฐาน ไม่ใช่ผลจำลองที่แม่นยำ

## เหตุผลที่แยก `dc_bias.py`
- ทดสอบได้โดยไม่ต้องมี Flask (รันเร็ว, แยกความรับผิดชอบ)
- อธิบายได้ว่า Frontend (template) / Backend (Flask) / Engineering logic ต่างกันอย่างไร
- แก้สมการแล้วไม่ต้องแตะ HTML — และแก้หน้าตาแล้วไม่เสี่ยงทำให้คณิตศาสตร์พัง
