from django.shortcuts import render, get_object_or_404
from django.http import Http404, HttpResponse
from .models import TimetableSlot, SystemSettings
import datetime
import csv
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


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
    
    # Export formatini tekshirish
    export_format = request.GET.get('format', None)
    if export_format == 'csv':
        return export_schedule_csv(group_name, slots)
    elif export_format == 'pdf':
        return export_schedule_pdf(group_name, slots, day_names)
    
    return render(request, 'group_schedule.html', context)


def export_schedule_csv(group_name, slots):
    """CSV export"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{group_name}_jadval.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Kun', 'Para', 'Fan', 'Dars turi', 'O\'qituvchi', 'Auditoriya'])
    
    day_names = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
    
    for slot in slots:
        day_name = day_names.get(slot.day_of_week, slot.day_of_week)
        lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
        writer.writerow([
            day_name,
            f"{slot.pair_number}-para",
            slot.subject.name,
            lesson_type_uz,
            slot.teacher.full_name,
            slot.room.name
        ])
    
    return response


def export_schedule_pdf(group_name, slots, day_names):
    """PDF export"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{group_name}_jadval.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center
    
    elements.append(Paragraph(f"{group_name} Guruh Jadvali", title_style))
    elements.append(Spacer(1, 20))
    
    # Jadval ma'lumotlari
    data = [['Kun', 'Para', 'Fan', 'Dars turi', 'O\'qituvchi', 'Auditoriya']]
    
    for slot in slots:
        day_name = day_names.get(slot.day_of_week, str(slot.day_of_week))
        lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
        data.append([
            day_name,
            str(slot.pair_number),
            slot.subject.name,
            lesson_type_uz,
            slot.teacher.full_name,
            slot.room.name
        ])
    
    # Jadval yaratish
    table = Table(data, colWidths=[60, 40, 100, 60, 100, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    return response
