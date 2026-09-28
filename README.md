# Smart Timetable - Universitetlar uchun aqlli dars jadvali tizimi

Python, Django, PostgreSQL va Aiogram 3.x yordamida ishlaydigan universitet dars jadvali tizimi.

## Xususiyatlar

- **Avtomatik jadval generatsiyasi**: Django management command orqali jadvalni avtomatik yaratish
- **Cheklovlar asosida ishlash**: Ma'ruza har doim seminar oldin bo'ladi, o'qituvchilar tanaffus oladi
- **Telegram bot integratsiyasi**: O'qituvchilar o'z dars jadvalini Telegram orqali ko'rishlari mumkin
- **Avtorizatsiya**: Telefon raqam orqali avtorizatsiya
- **To'qnashuvsizlik**: O'qituvchi, guruh va xona bir vaqtda ikkita darsda bo'la olmaydi

## Texnologiyalar

- Python 3.11+
- Django 5.0
- PostgreSQL
- Aiogram 3.x (Telegram Bot)
- psycopg2 (PostgreSQL adapter)

## O'rnatish

### 1. Repositoryni klonlash

```bash
git clone <repository-url>
cd smartscheduler
```

### 2. Virtual muhit yaratish

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Dependencylarni o'rnatish

```bash
pip install -r requirements.txt
```

### 4. Muhit o'zgaruvchilarini sozlash

`.env.example` faylini `.env` deb nusxalang va quyidagilarni to'ldiring:

```env
SECRET_KEY=django-insecure-change-this-in-production
DEBUG=True
# PostgreSQL uchun (production)
DATABASE_URL=postgresql://postgres:password@localhost:5432/smartscheduler
# Yoki alohida o'zgaruvchilar sifatida:
# DB_NAME=smartscheduler
# DB_USER=postgres
# DB_PASSWORD=postgres
# DB_HOST=localhost
# DB_PORT=5432
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

**Eslatma:** Agar `DATABASE_URL` sozlanmagan bo'lsa, tizim avtomatik SQLite ishlatadi (development uchun).

### 5. Ma'lumotlar bazasi sozlamalari

**Development (lokal):**
- SQLite avtomatik ishlatiladi (`DATABASE_URL` sozlanmagan bo'lsa)
- Hech qanday qo'shimcha sozlash talab etilmaydi

**Production (PostgreSQL):**
```bash
# PostgreSQL o'rnatish (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib

# Ma'lumotlar bazasini yaratish
sudo -u postgres psql
CREATE DATABASE smartscheduler;
CREATE USER smartscheduler WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE smartscheduler TO smartscheduler;
\q
```

### 6. Ma'lumotlar bazasini ko'chirish (SQLite ↔ PostgreSQL)

**SQLite dan PostgreSQL ga:**
```bash
# SQLite ma'lumotlarini eksport qilish
python manage.py dumpdata > backup.json

# .env faylida DATABASE_URL sozlang
# Migratsiyalarni qo'llash
python manage.py migrate

# Ma'lumotlarni import qilish
python manage.py loaddata backup.json
```

**PostgreSQL dan SQLite ga:**
```bash
# PostgreSQL ma'lumotlarini eksport qilish
python manage.py dumpdata > backup.json

# .env faylida DATABASE_URL o'chirib tashlang
# Migratsiyalarni qo'llash
python manage.py migrate

# Ma'lumotlarni import qilish
python manage.py loaddata backup.json
```

### 7. Migratsiyalarni qo'llash

```bash
python manage.py makemigrations
python manage.py migrate
```

### 8. Superuser yaratish

```bash
python manage.py createsuperuser
```

### 9. Ma'lumotlarni qo'shish

Django admin paneliga kirib (`http://localhost:8000/admin`):
- O'qituvchilar (Teacher) qo'shing
- Fanlar (Subject) qo'shing
- Auditoriyalar (Room) qo'shing
- O'quv rejalari (CoursePlan) qo'shing

## Foydalanish

### Jadval generatsiyasi

```bash
python manage.py generate_schedule
```

Bu komanda:
- Eski jadvalni tozalaydi
- Ma'ruzalarni avval joylashtiradi
- Seminarlarni ma'ruzadan keyin joylashtiradi
- O'qituvchilarning tanaffus qoidasiga amal qiladi
- To'qnashuvlarni oldini oladi

### Telegram botni ishga tushirish

```bash
python bot/main.py
```

Bot buyruqlari:
- `/start` - Avtorizatsiyadan o'tish
- `/myday` - Bugungi dars jadvalini ko'rish
- "📅 Bugungi dars jadvalim" - Bugungi dars jadvalini ko'rish
- "📊 Haftalik jadval" - Haftalik dars jadvalini ko'rish

## Loyiha tuzilishi

```
smartscheduler/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Botni ishga tushirish
│   ├── handlers.py          # Bot handlerlari
│   └── keyboards.py         # Klaviaturalar
├── smartscheduler/
│   ├── __init__.py
│   ├── settings.py          # Django sozlamalari
│   ├── urls.py              # URL konfiguratsiyasi
│   ├── wsgi.py
│   └── asgi.py
├── timetable/
│   ├── __init__.py
│   ├── models.py            # Django modellari
│   ├── admin.py             # Admin panel sozlamalari
│   ├── apps.py
│   └── management/
│       └── commands/
│           └── generate_schedule.py  # Jadval generatsiya komandasi
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## Django Modellari

### Teacher (O'qituvchi)
- `full_name` - To'liq ism
- `degree` - Daraja (Professor, Dotsent, Katta o'qituvchi, Assistent)
- `phone_number` - Telefon raqam (Unique)
- `telegram_id` - Telegram ID (Unique)
- `max_daily_hours` - Kunlik maksimal soat
- `rest_hours_required` - Tanaffus soatlari

### Subject (Fan)
- `name` - Fan nomi
- `code` - Fan kodi (Unique)

### CoursePlan (O'quv rejasi)
- `subject` - Fan (FK)
- `teacher` - O'qituvchi (FK)
- `group_name` - Guruh nomi
- `lecture_hours_per_week` - Ma'ruza soatlari (haftada)
- `seminar_hours_per_week` - Seminar soatlari (haftada)

### Room (Auditoriya)
- `name` - Auditoriya nomi (Unique)
- `capacity` - Sig'im

### TimetableSlot (Jadval sloti)
- `group_name` - Guruh nomi
- `subject` - Fan (FK)
- `teacher` - O'qituvchi (FK)
- `room` - Auditoriya (FK)
- `lesson_type` - Dars turi (lecture/seminar)
- `day_of_week` - Hafta kuni (1-6)
- `pair_number` - Para raqami (1-5)

## Cheklovlar (Constraints)

1. **O'qituvchi cheklovi**: O'qituvchi bir vaqtda (day_of_week + pair_number) ikkita darsda bo'la olmaydi
2. **Guruh cheklovi**: Guruh bir vaqtda ikkita darsda bo'la olmaydi
3. **Xona cheklovi**: Auditoriya bir vaqtda ikkita darsda bo'la olmaydi
4. **Ma'ruza qoidasi**: Har bir fanning ma'ruza mashg'uloti seminar mashg'ulotidan oldin bo'lishi shart
5. **Tanaffus qoidasi**: O'qituvchining `rest_hours_required` parametriga amal qilinadi

## Telegram Bot Xabari Namunasi

```
📅 Bugungi dars jadvalingiz (Dushanba):

🔹 1-para: Oliy Matematika (Ma'ruza)
   👥 Guruh: KI-210
   🚪 Auditoriya: 302-xona

🔹 3-para: Oliy Matematika (Seminar)
   👥 Guruh: KI-210
   🚪 Auditoriya: 204-xona
```

## Rivojlanish

```bash
# Django serverni ishga tushirish
python manage.py runserver

# Telegram botni ishga tushirish
python bot/main.py

# Jadvalni qayta generatsiya qilish
python manage.py generate_schedule
```

## Litsenziya

MIT License
