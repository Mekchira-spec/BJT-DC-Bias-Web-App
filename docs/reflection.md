# Reflection — Lab 02

## สิ่งที่ได้เรียนรู้
1. **Frontend / Backend ต่างกันจริง**: ไฟล์ `.html` เป็นเพียง template ที่ Flask นำไป render
   การเปิดด้วย `file://` ไม่มีการคำนวณ เพราะไม่มี process Python รอรับ request
2. **Form → Python เดินทางอย่างไร**: `<form method="post">` ส่งข้อมูลใน HTTP body →
   `request.form` → parse → เรียก `calculate()` → template แสดงผล
3. **แยกสมการออกจาก HTTP คุ้มจริง**: แก้สูตรใน `dc_bias.py` แล้วไม่ต้องแตะ HTML
   และเทสต์คณิตศาสตร์รันได้โดยไม่ต้องสตาร์ทเซิร์ฟเวอร์
4. **แบบจำลองมีขอบเขต**: Forward-Active ให้ผลที่ใช้ไม่ได้ใน Cutoff/Saturation
   การมี Warning ที่ชัดเจนสำคัญพอ ๆ กับการคำนวณถูก

## ข้อจำกัด
- β และ VBE คงที่ ไม่คิดผลอุณหภูมิและ Early effect
- ไม่มีการจำลอง DC Load Line หรือ SPICE
- เกณฑ์ Saturation ใช้ `VCE < 0.30 V` เป็นค่าคงที่ (ของจริงขึ้นกับกระแสและอุปกรณ์)
- ยังไม่รองรับ Bias แบบอื่น (Fixed, Emitter) และยังไม่มี AC analysis

## สิ่งที่จะทำต่อ
- W3: เพิ่ม Bias template อื่น + เทสต์เปรียบเทียบ
- W4: DC Load Line และตรวจกับ ngspice
- W5–W6: AC small-signal, Bode plot, Transient
- ปรับ UI ให้แสดงแผนผังวงจรและไฮไลต์โหนดแรงดัน

## บทเรียนเชิงกระบวนการ
- การเขียนเทสต์ก่อนทำให้เห็นทันทีว่า oracle ที่คำนวณมือมีRounding error
  (ค่า IB ต่างกันที่ทศนิยมตำแหน่งที่ 7) — จับได้เพราะเทสต์ละเอียด ไม่ใช่เพราะอ่านโค้ด
- การ commit ผ่าน GitHub Desktop ทำให้เห็น diff ก่อน commit ทุกครั้ง
  ซึ่งช่วยกันไฟล์ที่ไม่ควรเข้า repo (`.venv/`) ได้ดี
