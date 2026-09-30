@echo off
echo Smart Timetable ishga tushmoqda (parallel rejim)...
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
start "Jadval Generatsiyasi" cmd /k "python manage.py generate_schedule && pause"

timeout /t 2 /nobreak >nul

echo 3. Web server ishga tushmoqda (port 8000)...
start "Django Web Server" cmd /k "waitress-serve --port=8000 smartscheduler.wsgi:application && pause"

timeout /t 2 /nobreak >nul

echo 4. Telegram bot ishga tushmoqda...
start "Telegram Bot" cmd /k "python bot/main.py && pause"

echo.
echo Barcha jarayonlar alohida oynalarda ishga tushdi!
echo Web: http://localhost:8000
echo Bot: @darsmakerbot
echo.
echo Serverlarni to'xtatish uchun oynalarni yoping.
pause
