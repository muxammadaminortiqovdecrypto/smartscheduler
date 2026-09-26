@echo off
echo Smart Timetable ishga tushmoqda...
echo.

echo 1. Migratsiyalarni qo'llash...
python manage.py migrate
if %errorlevel% neq 0 (
    echo Xatolik: Migratsiyalar muvaffaqiyatsiz tugadi!
    pause
    exit /b 1
)
echo Migratsiyalar muvaffaqiyatli tugadi!
echo.

echo 2. Jadval generatsiyasi boshlanmoqda...
python manage.py generate_schedule
if %errorlevel% neq 0 (
    echo Xatolik: Jadval generatsiyasi muvaffaqiyatsiz tugadi!
    pause
    exit /b 1
)
echo Jadval generatsiyasi muvaffaqiyatli tugadi!
echo.

echo 3. Telegram bot ishga tushmoqda...
python bot/main.py
