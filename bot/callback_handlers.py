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

DAY_NAMES = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}


@router.callback_query(F.data.startswith("select_group_"))
async def callback_select_group(callback: types.CallbackQuery, state: FSMContext):
    """Talaba guruh tanlash"""
    group_name = callback.data.replace("select_group_", "")
    
    # Guruhni saqlash (state ichida)
    await state.update_data(selected_group=group_name)
    
    # Talaba klaviaturasini yuborish
    from .keyboards import get_main_keyboard
    await callback.message.edit_text(
        f"✅ Guruh tanlandi: {group_name}\n\n"
        f"Endi o'z jadvalingizni ko'rishingiz mumkin!",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


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
    
    # Guruh jadvalini olish - select_related bilan related fieldsni yuklash
    slots = await sync_to_async(
        lambda: list(TimetableSlot.objects.filter(group_name=group_name)
                    .select_related('subject', 'teacher', 'room')
                    .order_by('day_of_week', 'pair_number'))
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
    """CSV file yuborish - optimizatsiyalangan"""
    try:
        callback_data = callback.data
        print(f"CSV export callback data: {callback_data}")
        
        group_name = callback_data.replace("export_csv_", "")
        print(f"Extracted group name: {group_name}")
        
        # Sync contextda export funksiyasini ishlatish
        def export_csv_sync():
            slots = list(TimetableSlot.objects.filter(group_name=group_name)
                        .select_related('subject', 'teacher', 'room')
                        .order_by('day_of_week', 'pair_number'))
            
            if not slots:
                return None, None
            
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_ALL)
            writer.writerow(['Kun', 'Para', 'Fan', 'Dars turi', "O'qituvchi", 'Auditoriya'])
            
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
            
            output.seek(0)
            csv_data = output.getvalue().encode('utf-8-sig')
            return csv_data, len(slots)
        
        csv_data, slot_count = await sync_to_async(export_csv_sync)()
        
        if csv_data is None:
            await callback.answer("❌ Jadval topilmadi", show_alert=True)
            return
        
        print(f"CSV data size: {len(csv_data)} bytes, slots: {slot_count}")
        
        file = types.BufferedInputFile(
            csv_data,
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
    """PDF file yuborish - optimizatsiyalangan"""
    try:
        group_name = callback.data.replace("export_pdf_", "")
        
        # Sync contextda export funksiyasini ishlatish
        def export_pdf_sync():
            slots = list(TimetableSlot.objects.filter(group_name=group_name)
                        .select_related('subject', 'teacher', 'room')
                        .order_by('day_of_week', 'pair_number'))
            
            if not slots:
                return None
            
            # PDF yaratish
            from reportlab.lib.pagesizes import letter, A4, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            import io
            
            output = io.BytesIO()
            doc = SimpleDocTemplate(
                output,
                pagesize=landscape(A4),
                leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24,
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Sarlavha
            title_style = styles['Heading1']
            title_style.alignment = 1
            elements.append(Paragraph(f"{group_name} Guruh Jadvali", title_style))
            elements.append(Spacer(1, 16))
            
            # Header va cell styles
            header_style = ParagraphStyle(
                'header', fontName='Helvetica-Bold', fontSize=9,
                textColor=colors.whitesmoke, alignment=TA_CENTER, leading=11,
            )
            cell_style = ParagraphStyle(
                'cell', fontName='Helvetica', fontSize=8,
                alignment=TA_CENTER, leading=10, wordWrap='CJK',
            )
            
            # Jadval ma'lumotlari
            headers = ['Kun', 'Para', 'Fan', 'Dars turi', "O'qituvchi", 'Auditoriya']
            data = [[Paragraph(h, header_style) for h in headers]]
            
            day_names = {1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba', 5: 'Juma', 6: 'Shanba'}
            
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
            
            # Jadval yaratish
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
            
            output.seek(0)
            return output.getvalue()
        
        pdf_data = await sync_to_async(export_pdf_sync)()
        
        if pdf_data is None:
            await callback.answer("❌ Jadval topilmadi", show_alert=True)
            return
        
        file = types.BufferedInputFile(
            pdf_data,
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
