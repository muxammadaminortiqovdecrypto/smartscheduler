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

from timetable.models import Teacher, Subject, Room, CoursePlan

print("📊 Ma'lumotlar yuklanmoqda...")

# Fanlar (6 ta)
subjects_data = [
    {"name": "Oliy Matematika", "code": "MATH101"},
    {"name": "Fizika", "code": "PHYS101"},
    {"name": "Ingliz Tili", "code": "ENG101"},
    {"name": "Dasturlash Asoslari", "code": "PROG101"},
    {"name": "Ma'lumotlar Bazasi", "code": "DB101"},
    {"name": "Algoritmlar va Ma'lumotlar Tuzilmasi", "code": "ALGO101"},
]

print("\n📚 Fanlar qo'shilmoqda...")
for subj in subjects_data:
    Subject.objects.get_or_create(
        code=subj["code"],
        defaults={"name": subj["name"]}
    )
    print(f"  ✅ {subj['name']} ({subj['code']})")

# Auditoriyalar (5 ta)
rooms_data = [
    {"name": "301-xona", "capacity": 40},
    {"name": "302-xona", "capacity": 35},
    {"name": "303-xona", "capacity": 30},
    {"name": "204-xona (Lab)", "capacity": 25},
    {"name": "205-xona (Lab)", "capacity": 25},
]

print("\n🚪 Auditoriyalar qo'shilmoqda...")
for room in rooms_data:
    Room.objects.get_or_create(
        name=room["name"],
        defaults={"capacity": room["capacity"]}
    )
    print(f"  ✅ {room['name']} ({room['capacity']} o'rin)")

# O'qituvchilar (12 ta) - har xil stavkalar bilan
teachers_data = [
    # 1.0 stavka (20 soat/hafta) - 4 ta
    {"full_name": "Karimov Aziz", "degree": "professor", "phone": "998901234567", "stavka": 1.0},
    {"full_name": "Rahimova Nilufar", "degree": "dotsent", "phone": "998902345678", "stavka": 1.0},
    {"full_name": "Toshmatov Bobur", "degree": "katta_oqituvchi", "phone": "998903456789", "stavka": 1.0},
    {"full_name": "Qodirova Malika", "degree": "dotsent", "phone": "998904567890", "stavka": 1.0},
    
    # 0.75 stavka (15 soat/hafta) - 4 ta
    {"full_name": "Saidov Jamshid", "degree": "professor", "phone": "998905678901", "stavka": 0.75},
    {"full_name": "Hakimova Zarnigor", "degree": "katta_oqituvchi", "phone": "998906789012", "stavka": 0.75},
    {"full_name": "Nazarov Dilshod", "degree": "assistent", "phone": "998907890123", "stavka": 0.75},
    {"full_name": "Yuldasheva Kamola", "degree": "katta_oqituvchi", "phone": "998908901234", "stavka": 0.75},
    
    # 0.5 stavka (10 soat/hafta) - 4 ta
    {"full_name": "Akbarov Sardor", "degree": "assistent", "phone": "998909012345", "stavka": 0.5},
    {"full_name": "Murodova Shohista", "degree": "assistent", "phone": "998910123456", "stavka": 0.5},
    {"full_name": "Zokirov Behzod", "degree": "katta_oqituvchi", "phone": "998911234567", "stavka": 0.5},
    {"full_name": "Gafurova Nargiza", "degree": "assistent", "phone": "998912345678", "stavka": 0.5},
]

print("\n👨‍🏫 O'qituvchilar qo'shilmoqda...")
teachers = {}
for teacher in teachers_data:
    obj, created = Teacher.objects.get_or_create(
        phone_number=teacher["phone"],
        defaults={
            "full_name": teacher["full_name"],
            "degree": teacher["degree"],
            "stavka": teacher["stavka"],
            "max_daily_hours": 4,
            "rest_hours_required": 1,
        }
    )
    teachers[teacher["full_name"]] = obj
    print(f"  ✅ {teacher['full_name']} - {teacher['stavka']} stavka ({int(teacher['stavka'] * 20)} soat/hafta)")

# Guruhlar (3 ta)
groups = ["KI-210", "KI-211", "KI-212"]

# O'quv rejalari - har bir guruh uchun 6 ta fan
print("\n📝 O'quv rejalari qo'shilmoqda...")

subjects = Subject.objects.all()

for group in groups:
    print(f"\n  Guruh: {group}")
    
    # Har bir guruh uchun 6 ta fan
    for i, subject in enumerate(subjects):
        # O'qituvchilarni taqsimlash (stavkaga qarab)
        # Har bir o'qituvchi o'z stavkasiga mos soatda ishlashi kerak
        teacher_list = list(teachers.values())
        teacher = teacher_list[i % len(teacher_list)]
        
        # Stavkaga qarab soatlar
        # 1.0 stavka = 20 soat/hafta -> 2 fan + har birida 2 ma'ruza + 2 seminar = 8 soat
        # 0.75 stavka = 15 soat/hafta -> 1.5 fan -> 1 fan to'liq + 1 fan yarim
        # 0.5 stavka = 10 soat/hafta -> 1 fan -> 2 ma'ruza + 2 seminar = 4 soat
        
        if teacher.stavka >= 1.0:
            lecture_hours = 2
            seminar_hours = 2
        elif teacher.stavka >= 0.75:
            lecture_hours = 2
            seminar_hours = 1
        else:  # 0.5 stavka
            lecture_hours = 1
            seminar_hours = 1
        
        CoursePlan.objects.get_or_create(
            subject=subject,
            teacher=teacher,
            group_name=group,
            defaults={
                "lecture_hours_per_week": lecture_hours,
                "seminar_hours_per_week": seminar_hours,
            }
        )
        print(f"    ✅ {subject.name} - {teacher.full_name} ({teacher.stavka} stavka) - Ma'ruza: {lecture_hours}, Seminar: {seminar_hours}")

print("\n✅ Barcha ma'lumotlar muvaffaqiyatli yuklandi!")
print("\n📊 Xulosa:")
print(f"  📚 Fanlar: {len(subjects_data)} ta")
print(f"  👨‍🏫 O'qituvchilar: {len(teachers_data)} ta")
print(f"  🚪 Auditoriyalar: {len(rooms_data)} ta")
print(f"  👥 Guruhlar: {len(groups)} ta")
print(f"  📝 O'quv rejalari: {len(groups) * len(subjects_data)} ta")
print("\nEndi 'python manage.py generate_schedule' buyrug'ini bajaring.")
