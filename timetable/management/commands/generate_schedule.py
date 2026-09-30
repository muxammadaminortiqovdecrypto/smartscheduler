from django.core.management.base import BaseCommand
from django.db import transaction

from timetable.models import CoursePlan, Room, SystemSettings, TimetableSlot, Teacher
from timetable.scheduler import Lesson, TeacherInfo, diagnose, solve, DAYS

DAY_NAMES = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}


def build_problem():
    """DB dan solver uchun ma'lumotlarni tayyorlaydi."""
    ss = SystemSettings.objects.first()
    hps = ss.hours_per_stavka if ss else 20
    teachers = {
        t.id: TeacherInfo(cap=int(t.stavka * hps), daily_max=max(1, t.max_daily_hours),
                          rest=max(1, t.rest_hours_required))
        for t in Teacher.objects.all()
    }
    lessons, n = [], 0
    for cp in CoursePlan.objects.select_related('subject', 'teacher'):
        for kind, hours in (('lecture', cp.lecture_hours_per_week), ('seminar', cp.seminar_hours_per_week)):
            for _ in range(hours):
                lessons.append(Lesson(n, cp.id, cp.subject_id, cp.teacher_id, cp.group_name, kind))
                n += 1
    rooms = [(r.id, r.capacity) for r in Room.objects.all()]
    return lessons, teachers, rooms


class Command(BaseCommand):
    help = "Jadvalni avtomatik generatsiya qilish (constraint solver + local search)"

    def add_arguments(self, parser):
        parser.add_argument('--seed', type=int, default=1)
        parser.add_argument('--restarts', type=int, default=5)
        parser.add_argument('--iterations', type=int, default=20000)
        parser.add_argument('--dry-run', action='store_true', help="Bazaga yozmasdan natijani ko'rsatish")

    def handle(self, *args, **o):
        lessons, teachers, rooms = build_problem()
        if not lessons:
            return self.stdout.write(self.style.WARNING("O'quv rejasi topilmadi. Avval CoursePlan qo'shing."))
        if not rooms:
            return self.stdout.write(self.style.ERROR("Auditoriya topilmadi. Avval Room qo'shing."))

        names = {t.id: t.full_name for t in Teacher.objects.all()}
        for kind, who, need, limit in diagnose(lessons, teachers, len(rooms)):
            label = names.get(who, who) or 'xonalar'
            self.stdout.write(self.style.WARNING(
                f"⚠️  Sig'im yetarli emas [{kind}] {label}: {need} soat kerak, mumkin: {limit}"))

        self.stdout.write(f"🧮 {len(lessons)} ta dars joylashtirilmoqda...")
        s = solve(lessons, teachers, rooms, seed=o['seed'], restarts=o['restarts'], iterations=o['iterations'])
        missing = s.unplaced()

        if not o['dry_run']:
            with transaction.atomic():
                TimetableSlot.objects.all().delete()
                TimetableSlot.objects.bulk_create([
                    TimetableSlot(group_name=s.lessons[i].group, subject_id=s.lessons[i].subject,
                                  teacher_id=s.lessons[i].teacher, room_id=room,
                                  lesson_type=s.lessons[i].kind, day_of_week=d, pair_number=p)
                    for i, (d, p, room) in s.assign.items()
                ])
        self.stdout.write(f"✅ Joylashtirildi: {len(s.assign)}/{len(lessons)}   Jarima balli: {s.total_cost():.1f}")
        for l in missing:
            self.stdout.write(self.style.WARNING(
                f"   ❌ joylashmadi: {l.group} / fan#{l.subject} ({l.kind}) - {names.get(l.teacher)}"))
        if not missing:
            self.stdout.write(self.style.SUCCESS("Jadval muvaffaqiyatli generatsiya qilindi!"))
