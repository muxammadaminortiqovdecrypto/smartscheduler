from django.core.management.base import BaseCommand
from django.db import transaction
from timetable.models import CoursePlan, TimetableSlot, Room, SystemSettings
import random


class Command(BaseCommand):
    help = 'Generate timetable schedule automatically'

    def handle(self, *args, **options):
        self.stdout.write('Jadval generatsiyasi boshlanmoqda...')
        
        # Tizim sozlamalarini olish
        system_settings = SystemSettings.objects.first()
        if system_settings:
            hours_per_stavka = system_settings.hours_per_stavka
            self.stdout.write(f'1 stavka = {hours_per_stavka} soat/hafta')
        else:
            hours_per_stavka = 20  # Default qiymat
            self.stdout.write('Tizim sozlamalari topilmadi. Default: 1 stavka = 20 soat/hafta')
        
        # Eski jadvalni tozalash
        TimetableSlot.objects.all().delete()
        self.stdout.write('Eski jadval ma\'lumotlari tozalandi.')
        
        # Barcha o\'quv rejalarni olish
        course_plans = CoursePlan.objects.select_related('subject', 'teacher').all()
        
        if not course_plans.exists():
            self.stdout.write(self.style.WARNING('O\'quv rejasi topilmadi. Avval CoursePlan qo\'shing.'))
            return
        
        # Barcha xonalarni olish
        rooms = list(Room.objects.all())
        if not rooms:
            self.stdout.write(self.style.ERROR('Auditoriya topilmadi. Avval Room qo\'shing.'))
            return
        
        # Har bir o\'quv rejasi uchun jadval yaratish
        with transaction.atomic():
            for course_plan in course_plans:
                self.stdout.write(f'{course_plan} uchun jadval yaratilmoqda...')
                
                # Ma'ruzalarni avval joylashtirish
                self._generate_lessons(
                    course_plan, 
                    rooms, 
                    lesson_type='lecture',
                    hours=course_plan.lecture_hours_per_week,
                    hours_per_stavka=hours_per_stavka
                )
                
                # Seminarlarni keyin joylashtirish (ma'ruzadan keyin)
                self._generate_lessons(
                    course_plan,
                    rooms,
                    lesson_type='seminar',
                    hours=course_plan.seminar_hours_per_week,
                    after_lecture=True,
                    hours_per_stavka=hours_per_stavka
                )
        
        self.stdout.write(self.style.SUCCESS('Jadval muvaffaqiyatli generatsiya qilindi!'))
    
    def _generate_lessons(self, course_plan, rooms, lesson_type, hours, after_lecture=False, hours_per_stavka=20):
        """Berilgan dars turi uchun jadval slotlarini generatsiya qilish"""
        teacher = course_plan.teacher
        group_name = course_plan.group_name
        subject = course_plan.subject
        
        # O'qituvchining allaqachon band bo'lgan vaqtlarini olish
        teacher_slots = TimetableSlot.objects.filter(teacher=teacher).values_list(
            'day_of_week', 'pair_number'
        )
        teacher_busy_slots = set(teacher_slots)
        
        # O'qituvchining joriy haftalik soatlarini hisoblash
        current_weekly_hours = TimetableSlot.objects.filter(teacher=teacher).count()
        max_weekly_hours = int(teacher.stavka * hours_per_stavka)  # Tizim sozlamalaridan olinadi
        
        # Guruhning allaqachon band bo'lgan vaqtlarini olish
        group_slots = TimetableSlot.objects.filter(group_name=group_name).values_list(
            'day_of_week', 'pair_number'
        )
        group_busy_slots = set(group_slots)
        
        # O'qituvchining har kundagi darslar sonini hisoblash
        teacher_daily_lessons = {}
        for day, pair in teacher_busy_slots:
            teacher_daily_lessons[day] = teacher_daily_lessons.get(day, 0) + 1
        
        # Barcha mumkin bo'lgan slotlarni yaratish (kun va para kombinatsiyalari)
        all_slots = []
        for day in range(1, 7):  # 1-6 kun
            for pair in range(1, 6):  # 1-5 para
                all_slots.append((day, pair))
        
        # Slotlarni aralashtirish (tasodifiy tartib)
        random.shuffle(all_slots)
        
        # Har bir soat uchun slot topish
        lessons_created = 0
        
        for day, pair in all_slots:
            if lessons_created >= hours:
                break
            
            # Stavka cheklovi
            if current_weekly_hours + lessons_created >= max_weekly_hours:
                break
            
            slot_key = (day, pair)
            
            # Tekshirishlar:
            # 1. O'qituvchi band emasligi
            if slot_key in teacher_busy_slots:
                continue
            
            # 2. Guruh band emasligi
            if slot_key in group_busy_slots:
                continue
            
            # 3. Kunlik darslar soni cheklovi (maksimal 3 para)
            daily_lessons = teacher_daily_lessons.get(day, 0)
            if daily_lessons >= 3:
                continue
            
            # 4. O'qituvchining tanaffus qoidasiga rioya qilish
            if not self._check_rest_hours(teacher, day, pair, lesson_type):
                continue
            
            # 5. Seminar bo'lsa, ma'ruzadan keyin bo'lishi kerak
            if after_lecture:
                if not self._check_seminar_after_lecture(teacher, subject, group_name, day, pair):
                    continue
            
            # Mos xona topish
            room = self._find_available_room(rooms, day, pair)
            if not room:
                continue
            
            # Slot yaratish
            TimetableSlot.objects.create(
                group_name=group_name,
                subject=subject,
                teacher=teacher,
                room=room,
                lesson_type=lesson_type,
                day_of_week=day,
                pair_number=pair
            )
            
            # Band slotlarni yangilash
            teacher_busy_slots.add(slot_key)
            group_busy_slots.add(slot_key)
            teacher_daily_lessons[day] = daily_lessons + 1
            
            lessons_created += 1
            self.stdout.write(f'  {lesson_type}: {self._get_day_name(day)} - {pair}-para')
        
        if lessons_created < hours:
            self.stdout.write(
                self.style.WARNING(
                    f'{course_plan.subject.name} ({lesson_type}) uchun faqat {lessons_created}/{hours} soat joylashtirildi. '
                    f'O\'qituvchi stavkasi: {teacher.stavka} (maksimal {max_weekly_hours} soat/hafta)'
                )
            )
    
    def _check_rest_hours(self, teacher, day, pair, lesson_type):
        """O'qituvchining tanaffus qoidasini tekshirish"""
        rest_required = teacher.rest_hours_required
        
        # O'qituvchining shu kundagi barcha slotlarini olish
        teacher_slots = TimetableSlot.objects.filter(
            teacher=teacher,
            day_of_week=day
        ).order_by('pair_number')
        
        if not teacher_slots.exists():
            return True
        
        # Agar rest_required = 1 bo'lsa, har 3 paradan keyin 1 para tanaffus
        # Ya'ni ketma-ket 3 para dars bo'lishi mumkin, 4-chi para bo'sh bo'lishi kerak
        
        # Shu kundagi barcha band paralarni olish
        busy_pairs = [slot.pair_number for slot in teacher_slots]
        
        # Hozirgi paradan oldingi ketma-ket darslarni sanash
        consecutive_before = 0
        for p in range(pair - 1, 0, -1):
            if p in busy_pairs:
                consecutive_before += 1
            else:
                break
        
        # Agar ketma-ket darslar 3 ta bo'lsa, hozirgi para bo'sh bo'lishi kerak (tanaffus)
        if consecutive_before >= 3:
            return False
        
        return True
    
    def _check_seminar_after_lecture(self, teacher, subject, group_name, day, pair):
        """Seminar ma'ruzadan keyin bo'lishini tekshirish"""
        # Shu fan va guruh uchun ma'ruzalarni olish
        lectures = TimetableSlot.objects.filter(
            subject=subject,
            group_name=group_name,
            lesson_type='lecture'
        ).order_by('day_of_week', 'pair_number')
        
        if not lectures.exists():
            # Ma'ruza hali joylashtirilmagan, seminar ham joylashtirilmaydi
            return False
        
        # Seminar ma'ruzadan keyin bo'lishi kerak
        # Ya'ni kamida bitta ma'ruza seminardan oldin bo'lishi shart
        for lecture in lectures:
            # Agar ma'ruza seminardan oldin bo'lsa (oldingi kun yoki o'sha kuni erta) - OK
            if lecture.day_of_week < day or (lecture.day_of_week == day and lecture.pair_number < pair):
                return True
        
        # Hech qanday ma'ruza seminardan oldin emas
        return False
    
    def _find_available_room(self, rooms, day, pair):
        """Berilgan vaqt uchun bo'sh xona topish"""
        for room in rooms:
            if not TimetableSlot.objects.filter(room=room, day_of_week=day, pair_number=pair).exists():
                return room
        return None
    
    def _get_day_name(self, day):
        days = {
            1: 'Dushanba',
            2: 'Seshanba',
            3: 'Chorshanba',
            4: 'Payshanba',
            5: 'Juma',
            6: 'Shanba',
        }
        return days.get(day, str(day))
