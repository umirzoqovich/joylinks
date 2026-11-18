@echo off
title Joylinks Target CRM Server
cd /d "%~dp0"
echo ===================================================
echo   JOYLINKS TARGET CRM - O'QUV MARKAZ TIZIMI
echo ===================================================
echo.
echo Server ishga tushirilmoqda...
echo Manzil: http://127.0.0.1:8000
echo.
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8000"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)
if errorlevel 1 (
    echo.
    echo ===================================================
    echo   DIQQAT: Xatolik yuz berdi!
    echo   Kutubxonalarni o'rnatish uchun quyidagilarni bering:
    echo   pip install -r requirements.txt
    echo ===================================================
    pause
)
