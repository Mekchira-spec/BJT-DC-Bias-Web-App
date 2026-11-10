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
