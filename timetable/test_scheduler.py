from collections import Counter
from django.test import SimpleTestCase
from timetable.scheduler import Lesson, TeacherInfo, Solver, solve, diagnose


def problem(groups=6, subjects=4):
    lessons, n = [], 0
    for g in range(groups):
        for s in range(subjects):
            for kind, h in (('lecture', 2), ('seminar', 1)):
                for _ in range(h):
                    lessons.append(Lesson(n, g * 10 + s, s, s % 4 + 1, f'G{g}', kind)); n += 1
    teachers = {t: TeacherInfo(cap=20, daily_max=4) for t in range(1, 5)}
    return lessons, teachers, [(1, 30), (2, 30), (3, 40), (4, 25)]


class SolverTests(SimpleTestCase):
    def setUp(self):
        self.L, self.T, self.R = problem()
        self.s = solve(self.L, self.T, self.R, seed=3, restarts=3, iterations=3000)

    def test_all_placed_no_clashes(self):
        self.assertEqual(self.s.unplaced(), [])
        for key in (lambda l, a: (l.teacher, a[0], a[1]), lambda l, a: (l.group, a[0], a[1]),
                    lambda l, a: (a[2], a[0], a[1])):
            c = Counter(key(self.s.lessons[i], a) for i, a in self.s.assign.items())
            self.assertTrue(all(v == 1 for v in c.values()))

    def test_lecture_before_seminar(self):
        for plan, ls in self.s.by_plan.items():
            lec = min(self.s.assign[l.id][:2] for l in ls if l.kind == 'lecture')
            sem = min(self.s.assign[l.id][:2] for l in ls if l.kind == 'seminar')
            self.assertLess(lec, sem)

    def test_limits_respected(self):
        for t, info in self.T.items():
            mine = [a for i, a in self.s.assign.items() if self.s.lessons[i].teacher == t]
            self.assertLessEqual(len(mine), info.cap)
            for d, n in Counter(a[0] for a in mine).items():
                self.assertLessEqual(n, info.daily_max)

    def test_deterministic_with_seed(self):
        a = solve(self.L, self.T, self.R, seed=5, restarts=1, iterations=500).assign
        b = solve(self.L, self.T, self.R, seed=5, restarts=1, iterations=500).assign
        self.assertEqual(a, b)

    def test_diagnose_flags_overload(self):
        t = {1: TeacherInfo(cap=2, daily_max=4)}
        L = [Lesson(i, 1, 1, 1, 'G', 'lecture') for i in range(5)]
        self.assertTrue(any(k == 'teacher' for k, *_ in diagnose(L, t, 3)))
