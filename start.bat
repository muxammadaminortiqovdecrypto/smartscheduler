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

echo 3. Web server ishga tushmoqda (port 8000)...
start "Django Web Server" cmd /c "waitress-serve --port=8000 smartscheduler.wsgi:application && pause"
echo.

echo 4. Telegram bot ishga tushmoqda...
start "Telegram Bot" cmd /c "python bot/main.py && pause"
echo.

echo Barcha serverlar ishga tushdi!
echo Web: http://localhost:8000
echo Bot: @darsmakerbot
echo.
echo Serverlarni to'xtatish uchun oynalarni yoping.
pause

