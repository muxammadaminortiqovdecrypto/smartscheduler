from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .models import TimetableSlot, SystemSettings
import datetime


def schedule_view(request):
    """Bosh sahifa - guruh tanlash"""
    # Barcha guruhlarni olish
    groups = TimetableSlot.objects.values_list('group_name', flat=True).distinct()
    
    # Tizim sozlamalaridan ruxsat etilgan guruhlarni olish
    settings_obj = SystemSettings.objects.first()
    allowed_groups = []
    if settings_obj:
        allowed_groups = settings_obj.get_allowed_groups()
    
    # Faqat ruxsat etilgan guruhlarni ko'rsatish
    if allowed_groups:
        groups = [g for g in groups if g in allowed_groups]
    
    context = {
        'groups': sorted(groups),
    }
    return render(request, 'index.html', context)


def group_schedule_view(request, group_name):
    """Guruh jadvali"""
    # Guruh mavjudligini tekshirish
    if not TimetableSlot.objects.filter(group_name=group_name).exists():
        raise Http404(f"'{group_name}' guruh topilmadi.")
    
    # Tizim sozlamalaridan ruxsat etilgan guruhlarni olish
    settings_obj = SystemSettings.objects.first()
    allowed_groups = []
    if settings_obj:
        allowed_groups = settings_obj.get_allowed_groups()
    
    # Ruxsat tekshirish
    if allowed_groups and group_name not in allowed_groups:
        raise Http404(f"'{group_name}' guruhiga ruxsat yo'q.")
    
    # Bugungi kunni aniqlash
    today = datetime.date.today()
    day_of_week = today.isoweekday()  # 1-Dushanba ... 7-Yakshanba
    
    # Hafta kunlari
    day_names = {
        1: 'Dushanba',
        2: 'Seshanba',
        3: 'Chorshanba',
        4: 'Payshanba',
        5: 'Juma',
        6: 'Shanba',
    }
    
    # Barcha darslarni olish
    slots = TimetableSlot.objects.filter(group_name=group_name).order_by('day_of_week', 'pair_number')
    
    # Kunlarga bo'lish
    schedule_by_day = {}
    for day in range(1, 7):
        schedule_by_day[day] = []
    
    for slot in slots:
        schedule_by_day[slot.day_of_week].append(slot)
    
    context = {
        'group_name': group_name,
        'schedule_by_day': schedule_by_day,
        'day_names': day_names,
        'today': day_of_week,
    }
    
    return render(request, 'group_schedule.html', context)
