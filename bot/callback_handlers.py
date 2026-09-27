from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from timetable.models import Teacher, Subject, Room, TimetableSlot, CoursePlan, SystemSettings
from .keyboards import (
    get_admin_inline_keyboard,
    get_resources_inline_keyboard,
    get_teacher_list_inline_keyboard,
    get_subject_list_inline_keyboard,
    get_room_list_inline_keyboard,
    get_group_list_inline_keyboard
)
import datetime
from reportlab.lib.units import inch

router = Router()

SUPERADMIN_ID = 1685342390


@router.callback_query(F.data == "admin_resources")
async def callback_admin_resources(callback: types.CallbackQuery):
    """Resurslar menusi"""
    await callback.message.edit_text(
        "📚 Resurslar boshqaruvi",
        reply_markup=get_resources_inline_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_teacher")
async def callback_admin_teacher(callback: types.CallbackQuery):
    """O'qituvchilar ro'yxatini ko'rsatish"""
    teachers = await sync_to_async(list)(Teacher.objects.all())
    
    if not teachers:
        await callback.message.edit_text("👨‍🏫 O'qituvchilar ro'yxati bo'sh.")
        return
    
    await callback.message.edit_text(
        "👨‍🏫 O'qituvchilar ro'yxati:",
        reply_markup=get_teacher_list_inline_keyboard(teachers)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("teacher_"))
async def callback_teacher_detail(callback: types.CallbackQuery):
    """O'qituvchi tafsilotlari"""
    teacher_id = int(callback.data.split("_")[1])
    teacher = await sync_to_async(Teacher.objects.get)(id=teacher_id)
    
    text = (
        f"👨‍🏫 {teacher.full_name}\n\n"
        f"🎓 Daraja: {teacher.get_degree_display()}\n"
        f"📱 Telefon: {teacher.phone_number}\n"
        f"📊 Stavka: {teacher.stavka}\n"
        f"⏰ Kunlik maksimal: {teacher.max_daily_hours} soat\n"
        f"🔁 Tanaffus: har 3 paradan keyin\n"
    )
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "teacher_add")
async def callback_teacher_add(callback: types.CallbackQuery, state: FSMContext):
    """Yangi o'qituvchi qo'shish"""
    await callback.message.edit_text("👨‍🏫 Yangi o'qituvchi qo'shish\n\nIsmingizni kiriting:")
    await state.set_state("teacher_add_name")
    await callback.answer()


@router.callback_query(F.data == "admin_subject")
async def callback_admin_subject(callback: types.CallbackQuery):
    """Fanlar ro'yxatini ko'rsatish"""
    subjects = await sync_to_async(list)(Subject.objects.all())
    
    if not subjects:
        await callback.message.edit_text("📚 Fanlar ro'yxati bo'sh.")
        return
    
    await callback.message.edit_text(
        "📚 Fanlar ro'yxati:",
        reply_markup=get_subject_list_inline_keyboard(subjects)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_room")
async def callback_admin_room(callback: types.CallbackQuery):
    """Auditoriyalar ro'yxatini ko'rsatish"""
    rooms = await sync_to_async(list)(Room.objects.all())
    
    if not rooms:
        await callback.message.edit_text("🚪 Auditoriyalar ro'yxati bo'sh.")
        return
    
    await callback.message.edit_text(
        "🚪 Auditoriyalar ro'yxati:",
        reply_markup=get_room_list_inline_keyboard(rooms)
    )
    await callback.answer()


@router.callback_query(F.data == "admin_group")
async def callback_admin_group(callback: types.CallbackQuery):
    """Guruhlar ro'yxatini ko'rsatish"""
    # Jadvaldan guruhlarni olish
    groups = await sync_to_async(
        lambda: list(TimetableSlot.objects.values_list('group_name', flat=True).distinct())
    )()
    
    # Tizim sozlamalaridan ruxsat etilgan guruhlarni olish
    settings_obj = await sync_to_async(SystemSettings.objects.first)()
    allowed_groups = []
    if settings_obj:
        allowed_groups = settings_obj.get_allowed_groups()
    
    if not groups:
        await callback.message.edit_text("👥 Guruhlar ro'yxati bo'sh.")
        return
    
    # Ruxsat etilgan guruhlarni belgilash
    group_list = []
    for group in groups:
        status = "✅" if group in allowed_groups else "❌"
        group_list.append(f"{status} {group}")
    
    text = "👥 Guruhlar ro'yxati:\n\n" + "\n".join(group_list)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_group_list_inline_keyboard(groups)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("group_"))
async def callback_group_detail(callback: types.CallbackQuery):
    """Guruh tafsilotlari"""
    group_name = callback.data.split("_")[1]
    
    # Guruh jadvalini olish
    slots = await sync_to_async(
        lambda: list(TimetableSlot.objects.filter(group_name=group_name).order_by('day_of_week', 'pair_number'))
    )()
    
    if not slots:
        await callback.message.edit_text(f"👥 {group_name} guruh uchun jadval yo'q.")
        return
    
    text = f"👥 {group_name} guruh jadvali:\n\n"
    
    current_day = None
    for slot in slots:
        if slot.day_of_week != current_day:
            current_day = slot.day_of_week
            day_names = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
            text += f"--- {day_names.get(current_day)} ---\n\n"
        
        lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
        text += f"🔹 {slot.pair_number}-para: {slot.subject.name} ({lesson_type_uz})\n"
        text += f"   👨‍🏫 {slot.teacher.full_name}\n"
        text += f"   🚪 {slot.room.name}\n\n"
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "group_add")
async def callback_group_add(callback: types.CallbackQuery, state: FSMContext):
    """Yangi guruh qo'shish"""
    await callback.message.edit_text("👥 Yangi guruh qo'shish\n\nGuruh nomini kiriting (masalan: KI-220):")
    await state.set_state("group_add_name")
    await callback.answer()


@router.callback_query(F.data == "admin_settings")
async def callback_admin_settings(callback: types.CallbackQuery):
    """Tizim sozlamalari"""
    user_id = callback.from_user.id
    
    if user_id != SUPERADMIN_ID:
        await callback.answer("❌ Faqat superadmin", show_alert=True)
        return
    
    settings_obj = await sync_to_async(SystemSettings.objects.first)()
    
    if settings_obj:
        allowed_groups = settings_obj.get_allowed_groups()
        groups_text = ", ".join(allowed_groups) if allowed_groups else "Yo'q"
        
        text = (
            f"⚙️ Tizim sozlamalari\n\n"
            f"📊 1 stavka = {settings_obj.hours_per_stavka} soat/hafta\n"
            f"👥 Ruxsat etilgan guruhlar: {groups_text}\n\n"
            f"O'zgartirish uchun /settings buyrug'ini bosing."
        )
    else:
        text = "⚙️ Tizim sozlamalari yo'q. /settings buyrug'ini bosing."
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "admin_regenerate")
async def callback_admin_regenerate(callback: types.CallbackQuery):
    """Jadvalni qayta generatsiya qilish"""
    await callback.message.edit_text("🔄 Jadval generatsiyasi boshlanmoqda...")
    
    try:
        from django.core.management import call_command
        await sync_to_async(call_command)('generate_schedule')
        await callback.message.edit_text("✅ Jadval muvaffaqiyatli yangilandi!")
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {str(e)}")
    
    await callback.answer()


@router.callback_query(F.data == "admin_export")
async def callback_admin_export(callback: types.CallbackQuery):
    """Guruh jadvalini yuklab olish - file yuborish"""
    groups = await sync_to_async(
        lambda: list(TimetableSlot.objects.values_list('group_name', flat=True).distinct())
    )()
    
    if not groups:
        await callback.message.edit_text("❌ Jadvalda guruhlar topilmadi.")
        return
    
    # Guruhlar uchun inline keyboard yaratish
    from .keyboards import get_group_export_keyboard
    await callback.message.edit_text(
        "📥 Guruh jadvalini yuklab olish\n\nGuruhni tanlang:",
        reply_markup=get_group_export_keyboard(groups)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("export_csv_"))
async def callback_export_csv(callback: types.CallbackQuery):
    """CSV file yuborish"""
    try:
        group_name = callback.data.replace("export_csv_", "")
        
        # Jadval ma'lumotlarini olish
        slots = await sync_to_async(
            lambda: list(TimetableSlot.objects.filter(group_name=group_name).order_by('day_of_week', 'pair_number'))
        )()
        
        if not slots:
            await callback.answer("❌ Jadval topilmadi", show_alert=True)
            return
        
        # CSV yaratish
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Sarlavha
        writer.writerow(['Kun', 'Para', 'Fan', 'Dars turi', "O'qituvchi", 'Auditoriya'])
        
        # Ma'lumotlar
        day_names = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
        
        for slot in slots:
            day_name = day_names.get(slot.day_of_week, str(slot.day_of_week))
            lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
            writer.writerow([
                day_name,
                str(slot.pair_number),
                slot.subject.name,
                lesson_type_uz,
                slot.teacher.full_name,
                slot.room.name
            ])
        
        # File yuborish
        output.seek(0)
        file = types.BufferedInputFile(
            output.getvalue().encode('utf-8-sig'),
            filename=f"{group_name}_jadval.csv"
        )
        
        await callback.message.edit_text(f"📄 {group_name} guruh jadvali (CSV)")
        await callback.message.answer_document(file)
        await callback.answer("✅ CSV yuborildi")
        
    except Exception as e:
        print(f"CSV export xatoligi: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("export_pdf_"))
async def callback_export_pdf(callback: types.CallbackQuery):
    """PDF file yuborish"""
    try:
        group_name = callback.data.replace("export_pdf_", "")
        
        # Jadval ma'lumotlarini olish
        slots = await sync_to_async(
            lambda: list(TimetableSlot.objects.filter(group_name=group_name).order_by('day_of_week', 'pair_number'))
        )()
        
        if not slots:
            await callback.answer("❌ Jadval topilmadi", show_alert=True)
            return
        
        # PDF yaratish
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        import io
        
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Sarlavha
        title_style = styles['Heading1']
        title_style.alignment = 1  # Center
        elements.append(Paragraph(f"{group_name} Guruh Jadvali", title_style))
        elements.append(Spacer(1, 20))
        
        # Jadval ma'lumotlari
        data = [['Kun', 'Para', 'Fan', 'Dars turi', "O'qituvchi", 'Auditoriya']]
        
        day_names = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
        
        for slot in slots:
            day_name = day_names.get(slot.day_of_week, str(slot.day_of_week))
            lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
            data.append([
                day_name,
                f"{slot.pair_number}",
                slot.subject.name,
                lesson_type_uz,
                slot.teacher.full_name,
                slot.room.name
            ])
        
        # Jadval yaratish
        table = Table(data, colWidths=[1.5*inch, 1*inch, 2*inch, 1.5*inch, 2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        # File yuborish
        output.seek(0)
        file = types.BufferedInputFile(
            output.getvalue(),
            filename=f"{group_name}_jadval.pdf"
        )
        
        await callback.message.edit_text(f"📄 {group_name} guruh jadvali (PDF)")
        await callback.message.answer_document(file)
        await callback.answer("✅ PDF yuborildi")
        
    except Exception as e:
        print(f"PDF export xatoligi: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)


@router.callback_query(F.data == "admin_back")
async def callback_admin_back(callback: types.CallbackQuery):
    """Asosiy menuga qaytish"""
    await callback.message.edit_text(
        "⚙️ Admin panel",
        reply_markup=get_admin_inline_keyboard()
    )
    await callback.answer()
