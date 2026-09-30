from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from timetable.management.commands.generate_schedule import build_problem, DAY_NAMES
from timetable.models import TimetableSlot
from timetable.scheduler import Solver, DAYS, PAIRS


class Command(BaseCommand):
    help = "Jadvalni tekshirish (majburiy qoidalar), sifatini baholash va tasdiqlangan optimallashtirish takliflari"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help="Topilgan yaxshilanishlarni qo'llash")
        parser.add_argument('--top', type=int, default=10)

    def handle(self, *args, **o):
        lessons, teachers, rooms = build_problem()
        slots = list(TimetableSlot.objects.select_related('subject', 'teacher', 'room'))
        if not slots:
            return self.stdout.write(self.style.WARNING("Jadval bo'sh. Avval generate_schedule ni ishga tushiring."))

        # DB slotlarini solver holatiga moslashtirish (plan + tur bo'yicha)
        pool = defaultdict(list)
        for l in lessons:
            pool[(l.group, l.subject, l.teacher, l.kind)].append(l)
        s = Solver(lessons, teachers, rooms)
        db_id, extra = {}, []
        for sl in slots:
            bucket = pool[(sl.group_name, sl.subject_id, sl.teacher_id, sl.lesson_type)]
            if bucket:
                l = bucket.pop()
                s.place(l, sl.day_of_week, sl.pair_number, sl.room_id)
                db_id[l.id] = sl.id
            else:
                extra.append(sl)

        # 1. MAJBURIY QOIDALAR
        self.stdout.write(self.style.MIGRATE_HEADING('=== 1. MAJBURIY QOIDALAR ==='))
        errors = 0
        for l in s.unplaced():
            errors += 1
            self.stdout.write(self.style.ERROR(f'❌ Rejadagi dars joylashmagan: {l.group}, fan#{l.subject}, {l.kind}'))
        for sl in extra:
            errors += 1
            self.stdout.write(self.style.ERROR(f'❌ Rejada yo\'q dars: {sl}'))
        by_teacher = defaultdict(int)
        for sl in slots:
            by_teacher[sl.teacher] += 1
        for t, n in by_teacher.items():
            if n > teachers[t.id].cap:
                errors += 1
                self.stdout.write(self.style.ERROR(f'❌ {t.full_name}: {n} soat > stavka limiti {teachers[t.id].cap}'))
        for l in s.lessons.values():
            if l.id not in s.assign:
                continue
            d, p, room = s.assign[l.id]
            s.unplace(l)
            ok = s.hard_ok(l, d, p)
            s.place(l, d, p, room)
            if not ok:
                errors += 1
                self.stdout.write(self.style.ERROR(
                    f'❌ Qoida buzilgan: {l.group} {DAY_NAMES[d]} {p}-para ({l.kind}) - kunlik limit/tanaffus/ma\'ruza tartibi'))
        self.stdout.write(self.style.SUCCESS('✅ Barcha majburiy qoidalar bajarilgan') if not errors else f'Jami xatolar: {errors}')

        # 2. SIFAT
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== 2. SIFAT KO\'RSATKICHLARI ==='))
        g_windows = defaultdict(int)
        for g, days in s.gb.items():
            for d, ps in days.items():
                if ps:
                    g_windows[g] += (max(ps) - min(ps) + 1) - len(ps)
        t_windows = defaultdict(int)
        for t, days in s.tb.items():
            for d, ps in days.items():
                if ps:
                    t_windows[t] += (max(ps) - min(ps) + 1) - len(ps)
        for g, w in sorted(g_windows.items()):
            if w:
                self.stdout.write(f'⚠️  {g}: {w} ta "oyna" (darslar orasida bo\'sh para)')
        for t, w in t_windows.items():
            if w:
                self.stdout.write(f'⚠️  {teachers_name(slots, t)}: {w} ta oyna')
        for g, days in sorted(s.gb.items()):
            for d, ps in days.items():
                if len(ps) > 4:
                    self.stdout.write(f'⚠️  {g}: {DAY_NAMES[d]} - {len(ps)} para (4 tadan ko\'p)')
        if not any(g_windows.values()) and not any(t_windows.values()):
            self.stdout.write('✅ Oynalar yo\'q')

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== 3. XONALAR BANDLIGI ==='))
        total = len(DAYS) * len(PAIRS)
        used = defaultdict(int)
        for sl in slots:
            used[sl.room.name] += 1
        for name, n in sorted(used.items(), key=lambda x: -x[1]):
            pct = 100 * n / total
            mark = '⚠️ ' if pct > 80 else ('💤' if pct < 20 else '✅')
            self.stdout.write(f'{mark} {name}: {n}/{total} ({pct:.0f}%)')

        # 4. TASDIQLANGAN TAKLIFLAR: har biri haqiqatan mumkin va jarimani kamaytiradi
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== 4. TASDIQLANGAN YAXSHILANISHLAR ==='))
        before_total = s.total_cost()
        applied = []
        for _ in range(200):
            best = None
            for lid in list(s.assign):
                l = s.lessons[lid]
                old = s.assign[lid]
                base = s._local(l)
                s.unplace(l)
                for d, p, room in s.candidates(l):
                    if (d, p) == old[:2]:
                        continue
                    s.place(l, d, p, room)
                    gain = base - s._local(l)
                    s.unplace(l)
                    if gain > 0.01 and (best is None or gain > best[0]):
                        best = (gain, l, old, (d, p, room))
                s.place(l, *old)
            if not best:
                break
            gain, l, old, new = best
            s.unplace(l)
            s.place(l, *new)
            applied.append((gain, l, old, new))
        if not applied:
            self.stdout.write('✅ Jadval lokal optimal - yaxshilash topilmadi')
        for i, (gain, l, old, new) in enumerate(applied[:o['top']], 1):
            self.stdout.write(f'{i}. {l.group} ({l.kind}): {DAY_NAMES[old[0]]} {old[1]}-para → '
                              f'{DAY_NAMES[new[0]]} {new[1]}-para   (+{gain:.1f} ball)')

        after_total = s.total_cost()
        score = max(0, 100 - after_total / max(1, len(slots)) * 4)
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== XULOSA ==='))
        self.stdout.write(f'Jarima: {before_total:.1f} → {after_total:.1f} (takliflardan keyin)')
        self.stdout.write(f'Sifat bahosi: {score:.0f}/100')

        if applied and o['apply']:
            with transaction.atomic():
                # unique constraint'lar sababli avval band slotlarni vaqtincha bo'shatamiz
                ids = {db_id[i]: s.assign[i] for i in s.assign if i in db_id}
                objs = {x.pk: x for x in TimetableSlot.objects.filter(pk__in=ids)}
                TimetableSlot.objects.filter(pk__in=ids).delete()
                TimetableSlot.objects.bulk_create([
                    TimetableSlot(group_name=objs[pk].group_name, subject_id=objs[pk].subject_id,
                                  teacher_id=objs[pk].teacher_id, room_id=r, lesson_type=objs[pk].lesson_type,
                                  day_of_week=d, pair_number=p)
                    for pk, (d, p, r) in ids.items()])
            self.stdout.write(self.style.SUCCESS('✅ Yaxshilanishlar qo\'llandi'))
        elif applied:
            self.stdout.write("💡 Qo'llash uchun: python manage.py analyze_schedule --apply")


def teachers_name(slots, tid):
    for sl in slots:
        if sl.teacher_id == tid:
            return sl.teacher.full_name
    return str(tid)
