from django.test import TestCase
from django.test.utils import override_settings
from timetable.models import Teacher, Subject, Room, TimetableSlot, CoursePlan


class TimetableQueryOptimizationTest(TestCase):
    """Database query optimization tests"""

    def setUp(self):
        """Test ma'lumotlarini yaratish"""
        # Fan
        self.subject = Subject.objects.create(name="Matematika", code="MATH101")
        
        # O'qituvchi
        self.teacher = Teacher.objects.create(
            full_name="Test O'qituvchi",
            degree="professor",
            phone_number="998901234567",
            telegram_id=123456789
        )
        
        # Xona
        self.room = Room.objects.create(name="301-xona", capacity=30)
        
        # Jadval slotlari
        self.slot1 = TimetableSlot.objects.create(
            group_name="KI-210",
            subject=self.subject,
            teacher=self.teacher,
            room=self.room,
            lesson_type="lecture",
            day_of_week=1,
            pair_number=1
        )
        
        self.slot2 = TimetableSlot.objects.create(
            group_name="KI-210",
            subject=self.subject,
            teacher=self.teacher,
            room=self.room,
            lesson_type="seminar",
            day_of_week=1,
            pair_number=2
        )

    def test_select_related_reduces_queries(self):
        """select_related so'rovlar sonini kamaytirishi kerak"""
        # select_related bilan - 1 ta so'rov
        with self.assertNumQueries(1):
            slots = list(TimetableSlot.objects.filter(
                group_name="KI-210"
            ).select_related('subject', 'teacher', 'room'))
            
            # Related fieldlarga murojaat qilish
            for slot in slots:
                _ = slot.subject.name
                _ = slot.teacher.full_name
                _ = slot.room.name

    def test_without_select_related_more_queries(self):
        """select_relatedsiz ko'proq so'rov bo'ladi"""
        # select_relatedsiz - har bir slot uchun 3 ta qo'shimcha so'rov
        # 2 slot bor: 1 asosiy + 2 * 3 = 7 so'rov
        with self.assertNumQueries(7):
            slots = list(TimetableSlot.objects.filter(group_name="KI-210"))
            
            for slot in slots:
                _ = slot.subject.name
                _ = slot.teacher.full_name
                _ = slot.room.name

    def test_telegram_id_index_exists(self):
        """telegram_id uchun indeks/unique constraint mavjudligini tekshirish"""
        from django.db import connection

        table_name = Teacher._meta.db_table
        constraints = connection.introspection.get_constraints(connection.cursor(), table_name)
        telegram_field = Teacher._meta.get_field('telegram_id').column

        self.assertTrue(
            any(
                telegram_field in info.get('columns', [])
                for info in constraints.values()
            )
        )

    def test_unique_constraints_enforced(self):
        """Unique constraintlar ishlashini tekshirish"""
        # Teacher constraint
        with self.assertRaises(Exception):
            TimetableSlot.objects.create(
                group_name="KI-211",
                subject=self.subject,
                teacher=self.teacher,
                room=self.room,
                lesson_type="lecture",
                day_of_week=1,
                pair_number=1  # slot1 bilan bir xil vaqt
            )
        
        # Group constraint
        with self.assertRaises(Exception):
            TimetableSlot.objects.create(
                group_name="KI-210",  # slot1 bilan bir xil guruh
                subject=self.subject,
                teacher=self.teacher,  # Boshqa o'qituvchi kerak
                room=Room.objects.create(name="302-xona", capacity=25),
                lesson_type="lecture",
                day_of_week=1,
                pair_number=1  # slot1 bilan bir xil vaqt
            )
