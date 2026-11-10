# One-Click Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ให้ผู้ใช้ดับเบิลคลิก `start.bat` ครั้งเดียวแล้วเว็บ BJT DC Bias เปิดขึ้นเองในเบราว์เซอร์ โดยไม่ต้องพิมพ์คำสั่ง ไม่ต้อง `cd` ไม่ต้อง Activate venv และไม่เจอ `Address already in use`

**Architecture:** `start.bat` เป็น wrapper บาง ๆ ที่ย้าย current directory ไปยังโฟลเดอร์ของตัวเอง (`%~dp0`) แล้วเรียก `.venv\Scripts\python.exe run.py` ส่วน `run.py` ทำสามอย่าง: หา port ว่างถัดไป เปิดเบราว์เซอร์หลังเซิร์ฟเวอร์พร้อม แล้วเรียก `app.run()` — ไม่มีสมการฟิสิกส์และไม่แตะ `app.py`/`dc_bias.py`

**Tech Stack:** Windows batch, Python 3.15.2, Flask 3.1.3 (เดิม), `unittest` (เดิม), `socket`/`webbrowser`/`threading` จาก stdlib

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md` (ส่วน "วิธีรัน" ถูกขยายด้วยแผนนี้ — ไม่เปลี่ยนสถาปัตยกรรมเดิม)

## Global Constraints

- Python **3.15.2**, Flask **3.1.3**, ใช้ `.venv` เดิมเท่านั้น — ห้ามสร้าง venv ใหม่
- ใช้ `unittest` เท่านั้น; รันด้วย `python -m unittest discover -s tests -v`
- **ห้ามมี JavaScript**; ห้ามแตะ `dc_bias.py`, `app.py`, `templates/index.html`, `static/style.css`
- สมการ/ค่าคงที่ทางฟิสิกส์ต้องไม่ออกไปอยู่ใน `run.py` หรือ `start.bat`
- ข้อความ UI ภาษาไทย / ข้อความใน batch file เป็น ASCII เท่านั้น (กัน mojibake เพราะ cmd อ่าน .bat ตาม codepage)
- **Commit ผ่าน GitHub Desktop เท่านั้น** — git CLI ไม่อยู่ใน PATH
- ห้าม commit `.venv/`, `__pycache__/`, `.env`

## Review Focus

1. **`.venv` หายหรือย้ายเครื่อง** → ต้องขึ้นข้อความบอกวิธีแก้และ `pause` ไว้ ไม่ใช่หน้าต่างแวบแล้วหาย
2. **port 5000 ถูกใช้อยู่** (เช่นรันค้างจากรอบก่อน) → ต้องเลื่อนไป port ถัดไปเอง ไม่ error
3. **ดับเบิลคลิกจาก shortcut / จากโฟลเดอร์อื่น** → current directory ไม่ใช่โฟลเดอร์โปรเจกต์ ต้องยังหา `run.py` เจอ
4. **path มีช่องว่าง** (`BJT DC Bias Web App`) → ทุก path ใน batch ต้องอยู่ในเครื่องหมายคำพูด
5. **Flask ไม่ได้ติดตั้งใน `.venv`** → ต้องขึ้นข้อความติดตั้งและค้างหน้าต่างไว้ ไม่ใช่ traceback แล้วปิด

---

### Task 1: `run.py` — เลือก port + เปิดเบราว์เซอร์ + รัน Flask

**Files:**
- Create: `run.py`
- Create: `tests/test_launcher.py`

**Interfaces:**
- Produces:
  - `pick_port(host: str = "127.0.0.1", preferred: int = 5000, attempts: int = 20) -> int` — คืน port ว่างตัวแรกที่ ≥ `preferred`; raise `RuntimeError` ถ้าไม่ว่างเลยในช่วง `attempts` ตัว
  - `open_browser_later(url: str, delay: float = 1.5) -> threading.Timer` — เปิด `url` ด้วย `webbrowser.open` หลัง `delay` วินาที (timer เป็น daemon)
  - `main() -> int` — คืน `0` เมื่อสำเร็จ, `1` เมื่อ setup ผิด
  - module-level: `HOST`, `DEFAULT_PORT = 5000`, `MAX_ATTEMPTS = 20`, `BROWSER_DELAY_SECONDS = 1.5`

- [ ] **Step 1: เขียน failing test**

```python
# tests/test_launcher.py
"""Tests for the one-click launcher (no server is started)."""

import socket
import threading
import unittest
from unittest import mock

import run


class TestPickPort(unittest.TestCase):
    def test_returns_preferred_when_free(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free = probe.getsockname()[1]
        self.assertEqual(run.pick_port(preferred=free, attempts=1), free)

    def test_skips_busy_port(self):
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            taken = busy.getsockname()[1]
            chosen = run.pick_port(preferred=taken, attempts=5)
            self.assertNotEqual(chosen, taken)
            self.assertGreater(chosen, taken)

    def test_raises_when_no_port_available(self):
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            taken = busy.getsockname()[1]
            with self.assertRaises(RuntimeError):
                run.pick_port(preferred=taken, attempts=1)


class TestOpenBrowser(unittest.TestCase):
    def test_opens_url_after_delay(self):
        with mock.patch.object(run.webbrowser, "open") as fake_open:
            timer = run.open_browser_later("http://127.0.0.1:5000/", delay=0.0)
            timer.join(2.0)
            fake_open.assert_called_once_with("http://127.0.0.1:5000/")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: รันให้เห็นว่า FAIL**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest tests.test_launcher 2>&1"`
Expected: FAIL — `ModuleNotFoundError: No module named 'run'`

- [ ] **Step 3: สร้าง `run.py`**

จุดที่ต้องระวัง: **ห้ามใส่ `SO_REUSEADDR` ในตัว probe** — บน Windows มันยอมให้ bind ทับ port ที่ถูกใช้อยู่ ทำให้การตรวจ "port ว่าง" ผิดผล

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest tests.test_launcher 2>&1"`
Expected: PASS 4 tests

- [ ] **Step 5: รัน suite เดิมทั้งชุด ต้องไม่พัง**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests 2>&1"`
Expected: PASS 20 tests (16 เดิม + 4 ใหม่)

- [ ] **Step 6: Commit checkpoint (GitHub Desktop)**
ไฟล์: `run.py`, `tests/test_launcher.py`
Summary: `feat: add launcher that picks a free port and opens the browser`

---

### Task 2: `start.bat` + เอกสาร + ทดสอบดับเบิลคลิกจริง

**Files:**
- Create: `start.bat`
- Modify: `README.md` (เพิ่มหัวข้อ "เปิดแอปแบบดับเบิลคลิก")

**Interfaces:**
- Consumes: `run.py` จาก Task 1 (ไม่ต้องรู้ signature ภายใน เรียกเป็นไฟล์)

- [ ] **Step 1: สร้าง `start.bat`**

```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
title BJT DC Bias - close this window to stop the web server
if not exist ".venv\Scripts\python.exe" goto :no_venv
".venv\Scripts\python.exe" run.py
echo.
echo Server stopped. Press any key to close.
pause >nul
exit /b 0

:no_venv
echo [ERROR] .venv\Scripts\python.exe not found.
echo Fix: run these two commands in this folder, then double-click start.bat again:
echo    python -m venv .venv
echo    .venv\Scripts\python.exe -m pip install -r requirements.txt
pause
exit /b 1
```

- [ ] **Step 2: เพิ่มหัวข้อใน `README.md`**

ใต้หัวข้อ "ติดตั้งและรัน (Windows PowerShell)" ให้เพิ่ม: วิธีดับเบิลคลิก `start.bat`, สิ่งที่ต้องเห็น (`Running on http://127.0.0.1:<port>`), ข้อความว่า port อาจเป็น 5001+ ถ้า 5000 ไม่ว่าง, และ "ปิดหน้าต่าง = หยุดเว็บ"

- [ ] **Step 3: ทดสอบว่าดับเบิลคลิกแล้วเปิดจริง (ต้องเห็นผล)**

Run: `Start-Process start.bat` แล้วตรวจว่า port ที่ `run.py` รายงานตอบ HTTP 200 — ต้องได้ `200` และเนื้อหามี `name="VCC"`
Expected: เปิดเบราว์เซอร์เอง + เซิร์ฟเวอร์ตอบ 200

- [ ] **Step 4: ทดสอบเคส port ไม่ว่าง (Review Focus 2)**

จอง port 5000 ไว้ก่อนด้วย socket แล้วรัน `start.bat` → ต้องเห็นว่ามันเลื่อนไป 5001 และยังตอบ 200
Expected: ไม่มี `Address already in use`

- [ ] **Step 5: ทดสอบเคส `.venv` หาย (Review Focus 1, 4, 5)**

รัน `start.bat` ในโฟลเดอร์ที่ไม่มี `.venv` (คัดลอก bat ไปโฟลเดอร์ชั่วคราวใน `%TEMP%`) → ต้องขึ้น `[ERROR] .venv\Scripts\python.exe not found.` และค้างรอปุ่ม
Expected: หน้าต่างไม่ปิดเอง

- [ ] **Step 6: ตรวจความสะอาดก่อน commit**

Run (git ของ GitHub Desktop แบบ read-only):
`& "$env:LOCALAPPDATA\GitHubDesktop\app-3.6.10\resources\app\git\cmd\git.exe" status --short`
Expected: มีแต่ `start.bat`, `run.py`, `tests/test_launcher.py`, `README.md`, `docs/` — ไม่มี `.venv/`, `__pycache__/`

- [ ] **Step 7: Commit checkpoint (GitHub Desktop) + Push**
Summary: `feat: add one-click start.bat launcher`
