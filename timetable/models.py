from django.db import models
from django.core.exceptions import ValidationError


class SystemSettings(models.Model):
    """Tizim sozlamalari - superadmin tomonidan boshqariladi"""
    hours_per_stavka = models.IntegerField(default=20, verbose_name="1 stavkada soatlar soni")
    allowed_groups = models.TextField(blank=True, help_text="Ruxsat etilgan guruhlar (vergul bilan ajratilgan)", verbose_name="Ruxsat etilgan guruhlar")
    
    class Meta:
        verbose_name = 'Tizim sozlamalari'
        verbose_name_plural = 'Tizim sozlamalari'
    
    def __str__(self):
        return f"1 stavka = {self.hours_per_stavka} soat"
    
    def save(self, *args, **kwargs):
        # Faqat bitta yozuv bo'lishi kerak
        if not self.pk and SystemSettings.objects.exists():
            raise ValidationError("Faqat bitta tizim sozlamalari yozuvi bo'lishi mumkin")
        super().save(*args, **kwargs)
    
    def get_allowed_groups(self):
        """Ruxsat etilgan guruhlarni ro'yxat sifatida qaytarish"""
        if not self.allowed_groups:
            return []
        return [g.strip() for g in self.allowed_groups.split(',') if g.strip()]
    
    def add_group(self, group_name):
        """Guruh qo'shish"""
        groups = self.get_allowed_groups()
        if group_name not in groups:
            groups.append(group_name)
            self.allowed_groups = ','.join(groups)
            self.save()
    
    def remove_group(self, group_name):
        """Guruh o'chirish"""
        groups = self.get_allowed_groups()
        if group_name in groups:
            groups.remove(group_name)
            self.allowed_groups = ','.join(groups)
            self.save()


class Teacher(models.Model):
    DEGREE_CHOICES = [
        ('professor', 'Professor'),
        ('dotsent', 'Dotsent'),
        ('katta_oqituvchi', 'Katta o\'qituvchi'),
        ('assistent', 'Assistent'),
    ]

    full_name = models.CharField(max_length=200, verbose_name='To\'liq ism')
    degree = models.CharField(max_length=20, choices=DEGREE_CHOICES, verbose_name='Daraja')
    phone_number = models.CharField(max_length=20, unique=True, verbose_name='Telefon raqam')
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True, verbose_name='Telegram ID')
    is_admin = models.BooleanField(default=False, verbose_name='Admin')
    is_superadmin = models.BooleanField(default=False, verbose_name='Superadmin')
    stavka = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, verbose_name='Stavka (1 stavka = 20 soat/hafta)')
    max_daily_hours = models.IntegerField(default=4, verbose_name='Kunlik maksimal soat')
    rest_hours_required = models.IntegerField(default=1, verbose_name='Tanaffus soatlari (har 3 paradan keyin 1 para)')

    class Meta:
        verbose_name = 'O\'qituvchi'
        verbose_name_plural = 'O\'qituvchilar'

    def __str__(self):
        return f"{self.full_name} ({self.get_degree_display()})"


class Subject(models.Model):
    name = models.CharField(max_length=200, verbose_name='Fan nomi')
    code = models.CharField(max_length=50, unique=True, verbose_name='Fan kodi')

    class Meta:
        verbose_name = 'Fan'
        verbose_name_plural = 'Fanlar'

    def __str__(self):
        return f"{self.name} ({self.code})"


class CoursePlan(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name='Fan')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name='O\'qituvchi')
    group_name = models.CharField(max_length=50, verbose_name='Guruh nomi')
    lecture_hours_per_week = models.IntegerField(default=2, verbose_name='Ma\'ruza soatlari (haftada)')
    seminar_hours_per_week = models.IntegerField(default=2, verbose_name='Seminar soatlari (haftada)')

    class Meta:
        verbose_name = 'O\'quv rejasi'
        verbose_name_plural = 'O\'quv rejalari'
        unique_together = ['subject', 'teacher', 'group_name']

    def __str__(self):
        return f"{self.subject.name} - {self.group_name} - {self.teacher.full_name}"


class Room(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Auditoriya nomi')
    capacity = models.IntegerField(verbose_name='Sig\'im')

    class Meta:
        verbose_name = 'Auditoriya'
        verbose_name_plural = 'Auditoriyalar'

    def __str__(self):
        return f"{self.name} ({self.capacity} o\'rin)"


class TimetableSlot(models.Model):
    LESSON_TYPE_CHOICES = [
        ('lecture', 'Ma\'ruza'),
        ('seminar', 'Seminar'),
    ]

    DAY_OF_WEEK_CHOICES = [
        (1, 'Dushanba'),
        (2, 'Seshanba'),
        (3, 'Chorshanba'),
        (4, 'Payshanba'),
        (5, 'Juma'),
        (6, 'Shanba'),
    ]

    group_name = models.CharField(max_length=50, verbose_name='Guruh nomi')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name='Fan')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name='O\'qituvchi')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name='Auditoriya')
    lesson_type = models.CharField(max_length=10, choices=LESSON_TYPE_CHOICES, verbose_name='Dars turi')
    day_of_week = models.IntegerField(choices=DAY_OF_WEEK_CHOICES, verbose_name='Hafta kuni')
    pair_number = models.IntegerField(verbose_name='Para raqami (1-5)')

    class Meta:
        verbose_name = 'Jadval sloti'
        verbose_name_plural = 'Jadval slotlari'
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'day_of_week', 'pair_number'],
                name='unique_teacher_time_slot',
                violation_error_message='O\'qituvchi bir vaqtda ikkita darsda bo\'la olmaydi'
            ),
            models.UniqueConstraint(
                fields=['group_name', 'day_of_week', 'pair_number'],
                name='unique_group_time_slot',
                violation_error_message='Guruh bir vaqtda ikkita darsda bo\'la olmaydi'
            ),
            models.UniqueConstraint(
                fields=['room', 'day_of_week', 'pair_number'],
                name='unique_room_time_slot',
                violation_error_message='Auditoriya bir vaqtda ikkita darsda bo\'la olmaydi'
            ),
        ]

    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.pair_number}-para: {self.subject.name} ({self.get_lesson_type_display()}) - {self.group_name}"
