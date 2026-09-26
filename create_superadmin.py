import os
import sys
from pathlib import Path

# Project root ni qo'shish
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Django sozlamalarini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartscheduler.settings')

import django
django.setup()

from timetable.models import Teacher

# Superadmin yaratish
print("Superadmin yaratish...")
print("Telegram ID: 1685342390")

# Telefon raqamni so'rash
phone = input("Telefon raqamingizni kiriting (masalan: 998901234567): ")
name = input("Ismingizni kiriting: ")

try:
    teacher = Teacher.objects.create(
        full_name=name,
        degree="professor",
        phone_number=phone,
        telegram_id=1685342390,
        is_superadmin=True,
        max_daily_hours=4,
        rest_hours_required=1
    )
    print(f"\n✅ Superadmin muvaffaqiyatli yaratildi!")
    print(f"👤 Ism: {teacher.full_name}")
    print(f"📱 Telegram ID: {teacher.telegram_id}")
    print(f"🎓 Daraja: {teacher.get_degree_display()}")
    print(f"\nEndi botda /start buyrug'ini bosing va admin paneldan foydalaning!")
except Exception as e:
    print(f"\n❌ Xatolik: {e}")
    if "unique constraint" in str(e).lower():
        print("Ehtimol bu telefon raqam yoki Telegram ID allaqachon ro'yxatdan o'tgan.")
        print("Agar allaqachon yaratilgan bo'lsa, quyidagini bajaring:")
        print("python manage.py shell")
        print(">>> from timetable.models import Teacher")
        print(">>> teacher = Teacher.objects.get(telegram_id=1685342390)")
        print(">>> teacher.is_superadmin = True")
        print(">>> teacher.save()")
