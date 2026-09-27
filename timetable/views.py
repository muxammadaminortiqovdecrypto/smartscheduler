from django.shortcuts import render, get_object_or_404
from django.http import Http404, HttpResponse
from .models import TimetableSlot, SystemSettings
import datetime
import csv
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


DAY_NAMES = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}


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
    # Guruh nomini case-insensitive qilish
    group_name_lower = group_name.lower()
    
    # Barcha guruhlarni olish va case-insensitive qidirish
    all_groups = TimetableSlot.objects.values_list('group_name', flat=True).distinct()
    matching_group = None
    
    for g in all_groups:
        if g.lower() == group_name_lower:
            matching_group = g
            break
    
    if not matching_group:
        raise Http404(f"'{group_name}' guruh topilmadi.")
    
    # Tizim sozlamalaridan ruxsat etilgan guruhlarni olish
    settings_obj = SystemSettings.objects.first()
    allowed_groups = []
    if settings_obj:
        allowed_groups = settings_obj.get_allowed_groups()
    
    # Ruxsat tekshirish (case-insensitive)
    if allowed_groups:
        allowed_lower = [g.lower() for g in allowed_groups]
        if group_name_lower not in allowed_lower:
            raise Http404(f"'{group_name}' guruhiga ruxsat yo'q.")
    
    # Bugungi kunni aniqlash
    today = datetime.date.today()
    day_of_week = today.isoweekday()  # 1-Dushanba ... 7-Yakshanba
    
    # Barcha darslarni olish (matching_group asl nomi bilan)
    slots = TimetableSlot.objects.filter(group_name=matching_group).order_by('day_of_week', 'pair_number')
    
    # Kunlarga bo'lish
    schedule_by_day = {}
    for day in range(1, 7):
        schedule_by_day[day] = []
    
    for slot in slots:
        schedule_by_day[slot.day_of_week].append(slot)
    
    # Template uchun ma'lumotlarni tayyorlash
    schedule_data = []
    for day_num in range(1, 7):
        if schedule_by_day[day_num]:
            schedule_data.append({
                'day_num': day_num,
                'day_name': DAY_NAMES.get(day_num, str(day_num)),
                'slots': schedule_by_day[day_num]
            })
    
    context = {
        'group_name': matching_group,  # Asl nomini ko'rsatish
        'schedule_data': schedule_data,
        'today': day_of_week,
    }
    
    # Export formatini tekshirish
    export_format = request.GET.get('format', None)
    if export_format == 'csv':
        return export_schedule_csv(matching_group, slots)
    elif export_format == 'pdf':
        return export_schedule_pdf(matching_group, slots, DAY_NAMES)
    
    return render(request, 'group_schedule.html', context)


def export_schedule_csv(group_name, slots):
    """CSV export"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{group_name}_jadval.csv"'

    writer = csv.writer(response, quoting=csv.QUOTE_ALL)
    writer.writerow(['Kun', 'Para', 'Fan', 'Dars turi', "O'qituvchi", 'Auditoriya'])

    for slot in slots:
        day_name = DAY_NAMES.get(slot.day_of_week, str(slot.day_of_week))
        lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
        writer.writerow([
            day_name,
            f"{slot.pair_number}",
            slot.subject.name,
            lesson_type_uz,
            slot.teacher.full_name,
            slot.room.name,
        ])

    return response


def export_schedule_pdf(group_name, slots, day_names):
    """PDF export - optimizatsiyalangan"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{group_name}_jadval.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24,
    )
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center

    elements.append(Paragraph(f"{group_name} Guruh Jadvali", title_style))
    elements.append(Spacer(1, 16))

    header_style = ParagraphStyle(
        'header', fontName='Helvetica-Bold', fontSize=9,
        textColor=colors.whitesmoke, alignment=TA_CENTER, leading=11,
    )
    cell_style = ParagraphStyle(
        'cell', fontName='Helvetica', fontSize=8,
        alignment=TA_CENTER, leading=10, wordWrap='CJK',
    )

    headers = ['Kun', 'Para', 'Fan', 'Dars turi', "O'qituvchi", 'Auditoriya']
    data = [[Paragraph(h, header_style) for h in headers]]

    for slot in slots:
        day_name = day_names.get(slot.day_of_week, str(slot.day_of_week))
        lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
        row_values = [
            day_name,
            str(slot.pair_number),
            slot.subject.name,
            lesson_type_uz,
            slot.teacher.full_name,
            slot.room.name,
        ]
        data.append([Paragraph(str(v), cell_style) for v in row_values])

    col_widths = [65, 40, 170, 75, 155, 90]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    return response
