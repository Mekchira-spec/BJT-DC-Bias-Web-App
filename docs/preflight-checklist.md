# Pre-flight Checklist — Lab 02 (ก่อนเริ่มทำงานจริง)

ตรวจเมื่อ: **2026-11-10 17:39 (อังคาร)** · เครื่อง: Windows (win32) · โฟลเดอร์: `C:\Users\B6822187\Documents\GitHub\BJT DC Bias Web App`

> เกณฑ์: ทุกข้อต้องมี **หลักฐานจากการรันคำสั่งจริง** ไม่ใช่การคาดเดา
> ผลรวม: **PASS (5/5)** — พร้อมเริ่ม Brainstorming

| # | รายการ (ตามเอกสาร Lab 2.4) | ผล | หลักฐาน |
|---|---|---|---|
| 1 | Git | ✅ | `git version 2.56.0.windows.4` (git ที่มากับ GitHub Desktop 3.6.10) · `user.name=Mekchira-spec` · `user.email=chirameksaisawat208@gmail.com` |
| 2 | GitHub: Repo เปิดได้ | ✅ | `git ls-remote origin` ตอบ `5a4d20b… refs/heads/main` · upstream = `origin/main` · `## main...origin/main` (ตรงกัน ไม่มี commit ค้าง) |
| 3 | OpenCode Desktop: ส่งข้อความได้ | ✅ | `opencode v2.2.6` · session นี้ตอบสนองปกติ |
| 4 | Superpowers: โหลด brainstorming ได้ | ✅ | `opencode plugin list` → `superpowers 22f0b46` · `/api/plugin` → `status: active` · skill catalog มี `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development` (15 skills) |
| 5 | Python | ✅ | `python --version` → **Python 3.15.2** · `pip 26.2.2` · `python -c "import venv"` → ok · PyPI เข้าถึงได้ (dry-run เห็น Flask 3.1.3) |

## สถานะ Repository
- Remote: `https://github.com/Mekchira-spec/BJT-DC-Bias-Web-App.git`
- Branch: `main` · commits: 1 (`5a4d20b Initial commit`) · tracked: `.gitattributes` เท่านั้น
- ยังไม่มี `.gitignore` → ต้องเพิ่มก่อน commit แรกของงานจริง (กัน `.venv/`, `__pycache__/`, `.env`)

## กติกาการ Commit (ตามที่กำหนด): ใช้ GitHub Desktop เท่านั้น
1. GitHub Desktop → **File ▸ Add Local Repository** → `C:\Users\B6822187\Documents\GitHub\BJT DC Bias Web App` (ถ้ายังไม่เคยเพิ่ม)
2. แท็บ **Changes** → ตรวจรายการไฟล์และ diff ให้ครบ (ต้องไม่มี `.venv/`, `.env`, API key)
3. พิมพ์ Summary (และ Description ถ้าจำเป็น) → **Commit to main**
4. กด **Push origin** → ตรวจว่าแถบบนขึ้น "No local changes" และซิงก์กับ `origin/main`
5. ห้ามใช้ `git commit` จาก terminal ในงานนี้ (git CLI ไม่ได้อยู่ใน PATH ของเครื่องนี้)

## ข้อควรระวังที่พบระหว่างตรวจ
- **PATH ของ Python**: แก้ user PATH ให้ `Python315` มาก่อน `WindowsApps` แล้ว (backup: `%USERPROFILE%\.config\opencode\user-path-backup-2026-11-10.txt`) — terminal/แอปที่เปิดค้างก่อนแก้ต้องเปิดใหม่หนึ่งครั้ง
- **git CLI**: ไม่อยู่ใน PATH; ใช้ git bundle ของ GitHub Desktop ได้เฉพาะแบบ read-only เพื่อตรวจสถานะ/diff ก่อน commit
- **Repo Lab 1** (`Documents\GitHub\DC-circuit-calculator`, branch `user1`) ยังมีไฟล์ค้างไม่ commit: `M electrical.py`, `M test_electrical_branch.py` — ไม่เกี่ยวข้องกับ Lab 2 และไม่ถูกแตะต้อง

## เกณฑ์ตรวจรับที่จะใช้ปิดงาน (A1–A7)
A1 GET / = 200 + เห็นฟอร์ม · A2 POST คำนวณจริงด้วย Python · A3 ผลตรงกับการคำนวณอิสระ · A4 Validation · A5 Warning นอก Active Region · A6 ≥3 unit tests + ≥1 Flask test client · A7 clone repo แล้วรันตาม README ได้
