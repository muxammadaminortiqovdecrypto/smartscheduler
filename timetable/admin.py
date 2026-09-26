from django.contrib import admin
from .models import Teacher, Subject, CoursePlan, Room, TimetableSlot, SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['hours_per_stavka']
    
    def has_add_permission(self, request):
        # Faqat superadmin qo'sha oladi
        if request.user.is_superuser:
            return True
        return False
    
    def has_change_permission(self, request, obj=None):
        # Faqat superadmin o'zgartira oladi
        if request.user.is_superuser:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        # O'chirishga ruxsat yo'q
        return False


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'degree', 'phone_number', 'stavka', 'max_daily_hours', 'rest_hours_required']
    search_fields = ['full_name', 'phone_number']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']


@admin.register(CoursePlan)
class CoursePlanAdmin(admin.ModelAdmin):
    list_display = ['subject', 'teacher', 'group_name', 'lecture_hours_per_week', 'seminar_hours_per_week']
    list_filter = ['group_name', 'subject']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'capacity']


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ['group_name', 'subject', 'teacher', 'room', 'lesson_type', 'day_of_week', 'pair_number']
    list_filter = ['day_of_week', 'lesson_type', 'group_name']
