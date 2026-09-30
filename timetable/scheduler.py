"""
Jadval solveri (DB'dan mustaqil, test qilish oson).

HARD (majburiy) cheklovlar:
  1. O'qituvchi / guruh / xona bir vaqtda faqat bitta darsda
  2. O'qituvchining haftalik soati <= stavka * hours_per_stavka
  3. O'qituvchining kunlik soati <= max_daily_hours
  4. Ketma-ket 3 paradan ortiq dars yo'q; 3 para ketma-ket bo'lsa keyin
     kamida rest_hours_required para tanaffus
  5. Har bir fan+guruh uchun birinchi seminar birinchi ma'ruzadan KEYIN

SOFT (sifat) cheklovlari - jarima ballari bilan minimallashtiriladi:
  guruh va o'qituvchi "oynalari", kunlik yuklanish balansi, bir kunda bitta
  turdagi darsning takrorlanishi, shanba / 5-para, ma'ruza ertalab, ...
"""
import random
from collections import defaultdict
from dataclasses import dataclass

DAYS = range(1, 7)
PAIRS = range(1, 6)
MAX_RUN = 3


@dataclass(frozen=True)
class Lesson:
    id: int
    plan: int
    subject: int
    teacher: int
    group: str
    kind: str  # 'lecture' | 'seminar'


@dataclass(frozen=True)
class TeacherInfo:
    cap: int          # haftalik maksimal soat
    daily_max: int
    rest: int = 1


class Solver:
    def __init__(self, lessons, teachers, rooms, seed=0):
        self.lessons = {l.id: l for l in lessons}
        self.teachers = teachers          # {teacher_id: TeacherInfo}
        self.rooms = sorted(rooms, key=lambda r: r[1])  # [(room_id, capacity)]
        self.rng = random.Random(seed)
        self.assign = {}                  # lesson_id -> (day, pair, room)
        self.tb = defaultdict(lambda: defaultdict(set))   # teacher -> day -> pairs
        self.gb = defaultdict(lambda: defaultdict(set))   # group -> day -> pairs
        self.rb = defaultdict(set)                         # (day, pair) -> rooms
        self.tcount = defaultdict(int)
        self.by_plan = defaultdict(list)
        self.by_group = defaultdict(list)
        for l in lessons:
            self.by_plan[l.plan].append(l)
            self.by_group[l.group].append(l)

    # ---------------- state primitives ----------------
    def place(self, l, d, p, room):
        self.assign[l.id] = (d, p, room)
        self.tb[l.teacher][d].add(p)
        self.gb[l.group][d].add(p)
        self.rb[(d, p)].add(room)
        self.tcount[l.teacher] += 1

    def unplace(self, l):
        d, p, room = self.assign.pop(l.id)
        self.tb[l.teacher][d].discard(p)
        self.gb[l.group][d].discard(p)
        self.rb[(d, p)].discard(room)
        self.tcount[l.teacher] -= 1

    def free_room(self, l, d, p):
        used = self.rb[(d, p)]
        free = [r for r in self.rooms if r[0] not in used]
        if not free:
            return None
        return (free[-1] if l.kind == 'lecture' else free[0])[0]

    # ---------------- hard constraints ----------------
    def _runs_ok(self, teacher, pairs):
        info = self.teachers[teacher]
        ps = sorted(pairs)
        runs, start = [], ps[0]
        for a, b in zip(ps, ps[1:] + [None]):
            if b is None or b != a + 1:
                runs.append((start, a))
                start = b
        for i, (s, e) in enumerate(runs):
            n = e - s + 1
            if n > MAX_RUN:
                return False
            if n == MAX_RUN and i + 1 < len(runs) and runs[i + 1][0] - e - 1 < info.rest:
                return False
            if i and runs[i - 1][1] - runs[i - 1][0] + 1 == MAX_RUN and s - runs[i - 1][1] - 1 < info.rest:
                return False
        return True

    def _order_ok(self, l, d, p):
        """Birinchi ma'ruza < birinchi seminar (l joriy holatda joylashtirilmagan)."""
        pos = (d, p)
        others = [self.assign[x.id][:2] for x in self.by_plan[l.plan]
                  if x.id != l.id and x.id in self.assign]
        lec = [self.assign[x.id][:2] for x in self.by_plan[l.plan]
               if x.id != l.id and x.kind == 'lecture' and x.id in self.assign]
        sem = [self.assign[x.id][:2] for x in self.by_plan[l.plan]
               if x.id != l.id and x.kind == 'seminar' and x.id in self.assign]
        if l.kind == 'seminar':
            return bool(lec) and min(lec) < pos
        # ma'ruza: barcha seminarlardan oldin kamida bitta ma'ruza qolishi kerak
        first = min(lec + [pos])
        return not sem or first < min(sem)

    def hard_ok(self, l, d, p):
        t, g = l.teacher, l.group
        info = self.teachers[t]
        if p in self.tb[t][d] or p in self.gb[g][d]:
            return False
        if self.tcount[t] >= info.cap or len(self.tb[t][d]) >= info.daily_max:
            return False
        if not self._runs_ok(t, self.tb[t][d] | {p}):
            return False
        return self._order_ok(l, d, p)

    def candidates(self, l):
        out = []
        for d in DAYS:
            for p in PAIRS:
                if self.hard_ok(l, d, p):
                    room = self.free_room(l, d, p)
                    if room is not None:
                        out.append((d, p, room))
        return out

    # ---------------- soft cost ----------------
    def cost_group(self, g):
        c, counts = 0.0, []
        kinds = defaultdict(int)
        for d, ps in self.gb[g].items():
            n = len(ps)
            if not n:
                continue
            counts.append(n)
            c += 8 * ((max(ps) - min(ps) + 1) - n)      # oyna
            c += 20 * max(0, n - 4)                       # kuniga >4 para
            c += 3 if n == 1 else 0                       # yolg'iz para
            c += 2 if d == 6 else 0
            c += 1.5 * (5 in ps)
            c += 0.6 * n * n                              # balans
        for l in self.by_group[g]:
            if l.id in self.assign:
                d, p, _ = self.assign[l.id]
                if l.kind == 'lecture':
                    c += 0.5 * (p - 1)
                    kinds[(l.subject, d)] += 1
        c += 6 * sum(v - 1 for v in kinds.values() if v > 1)   # bir kunda 2 ma'ruza
        return c

    def cost_teacher(self, t):
        c = 0.0
        for d, ps in self.tb[t].items():
            n = len(ps)
            if not n:
                continue
            c += 4 * ((max(ps) - min(ps) + 1) - n)
            c += 10 * max(0, n - 3)
            c += 1.5                                      # ish kuni
            c += 2 if d == 6 else 0
        return c

    def total_cost(self):
        gs = {l.group for l in self.lessons.values()}
        return sum(self.cost_group(g) for g in gs) + sum(self.cost_teacher(t) for t in self.teachers)

    def _local(self, l):
        return self.cost_group(l.group) + self.cost_teacher(l.teacher)

    # ---------------- construction ----------------
    def _difficulty(self):
        demand = defaultdict(int)
        for l in self.lessons.values():
            demand[l.teacher] += 1
        def key(l):
            info = self.teachers[l.teacher]
            return (l.kind != 'lecture', -demand[l.teacher] / max(1, info.cap), self.rng.random())
        return sorted(self.lessons.values(), key=key)

    def _best_slot(self, l):
        best, best_c = None, None
        base = self._local(l)
        for d, p, room in self.candidates(l):
            self.place(l, d, p, room)
            delta = self._local(l) - base
            self.unplace(l)
            delta += self.rng.random() * 0.01
            if best_c is None or delta < best_c:
                best, best_c = (d, p, room), delta
        return best

    def construct(self):
        # ma'ruzalar avval, keyin seminarlar (tartib _difficulty ichida)
        pending = []
        for l in self._difficulty():
            slot = self._best_slot(l)
            if slot:
                self.place(l, *slot)
            else:
                pending.append(l)
        return pending

    def repair(self, pending, rounds=6):
        """Ejection chain: 1 ta bloklovchi darsni boshqa joyga ko'chirib joy ochish."""
        for _ in range(rounds):
            if not pending:
                break
            progress = False
            for l in list(pending):
                if self._eject_and_place(l):
                    pending.remove(l)
                    progress = True
            if not progress:
                break
        return pending

    def _eject_and_place(self, l):
        slots = [(d, p) for d in DAYS for p in PAIRS]
        self.rng.shuffle(slots)
        for d, p in slots:
            blockers = {x.id: x for x in self.lessons.values() if x.id in self.assign
                        and self.assign[x.id][:2] == (d, p)
                        and (x.teacher == l.teacher or x.group == l.group)}
            if len(blockers) > 2:
                continue
            saved = {b.id: self.assign[b.id] for b in blockers.values()}
            for b in blockers.values():
                self.unplace(b)
            if self.hard_ok(l, d, p) and (room := self.free_room(l, d, p)) is not None:
                self.place(l, d, p, room)
                moved, ok = [], True
                for b in blockers.values():
                    cands = [c for c in self.candidates(b) if (c[0], c[1]) != (d, p)]
                    if not cands:
                        ok = False
                        break
                    self.place(b, *self.rng.choice(cands))
                    moved.append(b)
                if ok:
                    return True
                for b in moved:
                    self.unplace(b)
                self.unplace(l)
            for bid, s in saved.items():
                self.place(self.lessons[bid], *s)
        return False

    # ---------------- improvement ----------------
    def improve(self, iterations=20000):
        ids = [i for i in self.assign]
        if not ids:
            return
        temp = 2.0
        for it in range(iterations):
            l = self.lessons[self.rng.choice(ids)]
            old = self.assign[l.id]
            before = self._local(l)
            self.unplace(l)
            d, p = self.rng.choice(list(DAYS)), self.rng.choice(list(PAIRS))
            room = self.free_room(l, d, p)
            if room is None or (d, p) == old[:2] or not self.hard_ok(l, d, p):
                self.place(l, *old)
                continue
            self.place(l, d, p, room)
            delta = self._local(l) - before
            t = temp * (1 - it / iterations) + 1e-6
            if delta > 0 and self.rng.random() >= pow(2.718281828, -delta / t):
                self.unplace(l)
                self.place(l, *old)

    def unplaced(self):
        return [l for l in self.lessons.values() if l.id not in self.assign]


def solve(lessons, teachers, rooms, seed=0, restarts=5, iterations=20000):
    """Bir nechta restartdan eng yaxshisini qaytaradi (kam joylashtirilmagan, kam jarima)."""
    best = None
    for r in range(restarts):
        s = Solver(lessons, teachers, rooms, seed=seed * 1000 + r)
        pending = s.repair(s.construct())
        s.improve(iterations)
        # improve qilingandan keyin qolgan darslarni yana urinib ko'ramiz
        pending = s.repair([l for l in s.unplaced()])
        score = (len(pending), s.total_cost())
        if best is None or score < best[0]:
            best = (score, s)
        if score[0] == 0 and score[1] < 1:
            break
    return best[1]


def diagnose(lessons, teachers, n_rooms):
    """Joylashtirish mumkin emasligining oldindan sabablari."""
    issues = []
    t_demand, g_demand = defaultdict(int), defaultdict(int)
    for l in lessons:
        t_demand[l.teacher] += 1
        g_demand[l.group] += 1
    for t, n in t_demand.items():
        info = teachers[t]
        limit = min(info.cap, info.daily_max * len(DAYS))
        if n > limit:
            issues.append(('teacher', t, n, limit))
    slots = len(DAYS) * len(PAIRS)
    for g, n in g_demand.items():
        if n > slots:
            issues.append(('group', g, n, slots))
    if len(lessons) > n_rooms * slots:
        issues.append(('rooms', None, len(lessons), n_rooms * slots))
    return issues
