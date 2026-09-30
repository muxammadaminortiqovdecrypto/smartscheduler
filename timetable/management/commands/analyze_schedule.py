from django.core.management.base import BaseCommand
from timetable.models import Teacher, TimetableSlot, CoursePlan, Room
from collections import defaultdict


class Command(BaseCommand):
    help = 'Analyze schedule and provide optimization suggestions for superadmin'

    def handle(self, *args, **options):
        self.stdout.write('📊 Jadval tahlili va optimizatsiya maslahatlari...\n')
        
        # 1. O'qituvchilarning kunlik darslarini tahlil qilish
        self.stdout.write('=== 1. O\'QITUVCHILARNING KUNLIK DARSLARI ===')
        teacher_daily_stats = defaultdict(lambda: defaultdict(int))
        
        for slot in TimetableSlot.objects.select_related('teacher'):
            teacher_daily_stats[slot.teacher][slot.day_of_week] += 1
        
        for teacher, days in teacher_daily_stats.items():
            for day, count in days.items():
                day_names = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
                if count > 3:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️ {teacher.full_name}: {day_names[day]} - {count} para (maksimal 3 tavsiya etiladi)"
                        )
                    )
                elif count < 2 and count > 0:
                    self.stdout.write(
                        f"✅ {teacher.full_name}: {day_names[day]} - {count} para (yaxshi)"
                    )
        
        # 2. Xonalarning bandlik darajasini tahlil qilish
        self.stdout.write('\n=== 2. XONALARNING BANDLIGI ===')
        room_usage = defaultdict(lambda: defaultdict(int))
        
        for slot in TimetableSlot.objects.select_related('room'):
            room_usage[slot.room][slot.day_of_week] += 1
        
        for room, days in room_usage.items():
            total_usage = sum(days.values())
            capacity = room.capacity
            usage_percent = (total_usage / (capacity * 5)) * 100  # 5 para per day, 6 days
            
            if usage_percent > 80:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️ {room.name}: {total_usage}/{capacity*5} ({usage_percent:.1f}% band) - ko'p ishlatilmoqda"
                    )
                )
            elif usage_percent < 30:
                self.stdout.write(
                    f"✅ {room.name}: {total_usage}/{capacity*5} ({usage_percent:.1f}% band) - bo'sh ko'p"
                )
        
        # 3. Guruhlarning darslarini tahlil qilish
        self.stdout.write('\n=== 3. GURUHLARNING DARLARI ===')
        group_stats = defaultdict(lambda: defaultdict(int))
        
        for slot in TimetableSlot.objects.all():
            group_stats[slot.group_name][slot.day_of_week] += 1
        
        for group, days in group_stats.items():
            for day, count in days.items():
                day_names = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
                if count > 4:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️ {group}: {day_names[day]} - {count} para (juda ko'p)"
                        )
                    )
                elif count == 0:
                    self.stdout.write(
                        f"ℹ️ {group}: {day_names[day]} - {count} para (dars yo'q)"
                    )
        
        # 4. Optimizatsiya maslahatlari
        self.stdout.write('\n=== 4. OPTIMIZATSIYA MASLAHATLARI ===')
        
        # 4.1 O'qituvchilarni boshqa kunga ko'chirish maslahati
        suggestions = []
        
        for teacher, days in teacher_daily_stats.items():
            overloaded_days = [day for day, count in days.items() if count > 3]
            underloaded_days = [day for day, count in days.items() if count < 2 and count > 0]
            
            if overloaded_days and underloaded_days:
                day_names = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
                for over_day in overloaded_days:
                    for under_day in underloaded_days:
                        benefit = (days[over_day] - 3) * 10  # Har bir ortiqcha para uchun 10 ball
                        suggestions.append({
                            'type': 'teacher_move',
                            'teacher': teacher.full_name,
                            'from_day': day_names[over_day],
                            'to_day': day_names[under_day],
                            'benefit': benefit,
                            'description': f"{teacher.full_name}ni {day_names[over_day]}dan {day_names[under_day]}ga ko'chirish ({days[over_day]} → {days[under_day] + 1})"
                        })
        
        # 4.2 Guruhlarni boshqa kunga ko'chirish maslahati
        for group, days in group_stats.items():
            overloaded_days = [day for day, count in days.items() if count > 4]
            underloaded_days = [day for day, count in days.items() if count < 2 and count > 0]
            
            if overloaded_days and underloaded_days:
                day_names = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
                for over_day in overloaded_days:
                    for under_day in underloaded_days:
                        benefit = (days[over_day] - 4) * 15  # Har bir ortiqcha para uchun 15 ball
                        suggestions.append({
                            'type': 'group_move',
                            'group': group,
                            'from_day': day_names[over_day],
                            'to_day': day_names[under_day],
                            'benefit': benefit,
                            'description': f"{group} guruhini {day_names[over_day]}dan {day_names[under_day]}ga ko'chirish ({days[over_day]} → {days[under_day] + 1})"
                        })
        
        # Maslahatlarni foyda bo'yicha tartiblash
        suggestions.sort(key=lambda x: x['benefit'], reverse=True)
        
        if suggestions:
            self.stdout.write('\n🎯 TOP 10 MASLAHATLAR (foyda bo\'yicha):')
            for i, suggestion in enumerate(suggestions[:10], 1):
                self.stdout.write(
                    f"{i}. {suggestion['description']} (Foyda: {suggestion['benefit']} ball)"
                )
        else:
            self.stdout.write('✅ Jadval optimal holatda!')
        
        # 5. Xulosa
        self.stdout.write('\n=== 5. XULOSA ===')
        self.stdout.write('📋 Umumiy tavsiyalar:')
        self.stdout.write('1. O\'qituvchilar kuniga maksimal 3 para dars bo\'lishi kerak')
        self.stdout.write('2. Guruhlar kuniga maksimal 4-5 para dars bo\'lishi kerak')
        self.stdout.write('3. Juma tushdan keyin dars qo\'yish tavsiya etiladi')
        self.stdout.write('4. Ma\'ruzalarni ertalab (1-3 para), seminarlarni tushdan keyin (4-5 para)')
        self.stdout.write('5. Xonalar sig\'imidan to\'li foydalanish kerak')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Tahlil tugadi!'))
