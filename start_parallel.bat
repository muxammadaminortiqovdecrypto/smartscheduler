@echo off
echo Smart Timetable ishga tushmoqda (parallel rejim)...
echo.

echo Jadval generatsiyasi boshlanmoqda...
start "Jadval Generatsiyasi" cmd /k "python manage.py generate_schedule"

timeout /t 2 /nobreak >nul

echo Telegram bot ishga tushmoqda...
start "Telegram Bot" cmd /k "python bot/main.py"

echo Ikkala jarayon ham alohida oynalarda ishga tushdi.
