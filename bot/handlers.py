from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async
from django.conf import settings
from timetable.models import Teacher, TimetableSlot, Subject, Room, CoursePlan, SystemSettings
from .keyboards import get_phone_keyboard, get_main_keyboard, get_remove_keyboard, get_admin_keyboard, get_degree_keyboard
import datetime
import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


router = Router()


class AuthStates(StatesGroup):
    waiting_for_phone = State('waiting_for_phone')


class AdminStates(StatesGroup):
    # Teacher qo'shish
    teacher_name = State('teacher_name')
    teacher_degree = State('teacher_degree')
    teacher_phone = State('teacher_phone')
    teacher_max_hours = State('teacher_max_hours')
    teacher_rest_hours = State('teacher_rest_hours')
    
    # Subject qo'shish
    subject_name = State('subject_name')
    subject_code = State('subject_code')
    
    # Room qo'shish
    room_name = State('room_name')
    room_capacity = State('room_capacity')
    
    # CoursePlan qo'shish
    course_subject = State('course_subject')
    course_teacher = State('course_teacher')
    course_group = State('course_group')
    course_lecture_hours = State('course_lecture_hours')
    course_seminar_hours = State('course_seminar_hours')
    
    # System settings
    settings_hours_per_stavka = State('settings_hours_per_stavka')
    
    # Group schedule export
    export_group_name = State('export_group_name')


SUPERADMIN_ID = 1685342390


@router.message(F.text == '/start')
async def cmd_start(message: types.Message, state: FSMContext):
    """Start komandasi - avtorizatsiyani boshlash"""
    await state.clear()
    
    user_id = message.from_user.id
    
    # Superadmin tekshirish
    if user_id == SUPERADMIN_ID:
        teacher = await sync_to_async(Teacher.objects.filter)(telegram_id=user_id)
        teacher_obj = await sync_to_async(teacher.first)()
        
        if teacher_obj:
            await message.answer(
                f"👑 Assalomu alaykum, Superadmin {message.from_user.first_name}!\n\n"
                "Siz tizimga kirgansiz.",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer(
                f"👑 Assalomu alaykum, Superadmin {message.from_user.first_name}!\n\n"
                "Siz hali ro'yxatdan o'tmagansiz. Admin paneldan foydalanish uchun avval o'zingizni qo'shing.",
                reply_markup=get_main_keyboard()
            )
        return
    
    # Foydalanuvchi allaqachon avtorizatsiyadan o'tganmi tekshirish
    teacher = await sync_to_async(Teacher.objects.filter)(telegram_id=user_id)
    teacher_exists = await sync_to_async(teacher.exists)()
    
    if teacher_exists:
        teacher_obj = await sync_to_async(teacher.first)()
        if teacher_obj.is_admin or teacher_obj.is_superadmin:
            await message.answer(
                f"👨‍🏫 Assalomu alaykum, Admin {message.from_user.first_name}!\n\n"
                "Siz tizimga kirgansiz.",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer(
                f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
                "Siz allaqachon tizimga kirgansiz.",
                reply_markup=get_main_keyboard()
            )
    else:
        await message.answer(
            f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
            "Dars jadvalini ko'rish uchun avtorizatsiyadan o'ting. "
            "Iltimos, telefon raqamingizni yuboring.",
            reply_markup=get_phone_keyboard()
        )
        await state.set_state(AuthStates.waiting_for_phone)


@router.message(AuthStates.waiting_for_phone, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    """Telefon raqamini qabul qilish va tekshirish"""
    contact = message.contact
    phone_number = contact.phone_number
    
    # Telefon raqamni tozalash (+998901234567 -> 998901234567)
    clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
    
    # Bazadan o'qituvchini qidirish
    teacher = await sync_to_async(Teacher.objects.filter)(phone_number=clean_phone)
    teacher_obj = await sync_to_async(teacher.first)()
    
    if teacher_obj:
        # Telegram ID ni saqlash
        teacher_obj.telegram_id = user_id
        await sync_to_async(teacher_obj.save)()
        
        await message.answer(
            f"✅ Muvaffaqiyatli kirildi!\n\n"
            f"Xush kelibsiz, {teacher_obj.full_name}!",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            "❌ Bu telefon raqam bilan o'qituvchi topilmadi.\n\n"
            "Iltimos, administrator bilan bog'laning yoki boshqa raqamni kiriting.",
            reply_markup=get_phone_keyboard()
        )


@router.message(F.text == '📅 Bugungi dars jadvalim')
@router.message(F.text == '/myday')
async def cmd_myday(message: types.Message):
    """Bugungi dars jadvalini ko'rsatish"""
    user_id = message.from_user.id
    
    # O'qituvchini topish
    teacher = await sync_to_async(Teacher.objects.filter)(telegram_id=user_id)
    teacher_obj = await sync_to_async(teacher.first)()
    
    if not teacher_obj:
        await message.answer(
            "❌ Siz avtorizatsiyadan o'tmagansiz. Iltimos, /start buyrug'ini bosing.",
            reply_markup=get_remove_keyboard()
        )
        return
    
    # Bugungi kunni aniqlash
    today = datetime.date.today()
    day_of_week = today.isoweekday()  # 1-Dushanba ... 7-Yakshanba
    
    if day_of_week == 7:  # Yakshanba
        await message.answer("🎉 Bugun yakshanba! Darslar yo'q.")
        return
    
    if day_of_week > 6:  # Shanba dan keyin
        await message.answer("Bugun dars kuni emas.")
        return
    
    # Bugungi darslarni olish
    slots = await sync_to_async(
        lambda: list(TimetableSlot.objects.filter(
            teacher=teacher_obj,
            day_of_week=day_of_week
        ).order_by('pair_number'))
    )()
    
    if not slots:
        day_name = _get_day_name(day_of_week)
        await message.answer(f"📅 {day_name} uchun darslar yo'q.")
        return
    
    # Jadvalni formatlash
    day_name = _get_day_name(day_of_week)
    response = f"📅 **Bugungi dars jadvalingiz ({day_name}):**\n\n"
    
    for slot in slots:
        lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
        response += f"🔹 **{slot.pair_number}-para:** {slot.subject.name} ({lesson_type_uz})\n"
        response += f"   👥 Guruh: {slot.group_name}\n"
        response += f"   🚪 Auditoriya: {slot.room.name}\n\n"
    
    await message.answer(response, parse_mode='Markdown')


@router.message(F.text == '📊 Haftalik jadval')
async def cmd_weekly(message: types.Message):
    """Haftalik dars jadvalini ko'rsatish"""
    user_id = message.from_user.id
    
    # O'qituvchini topish
    teacher = await sync_to_async(Teacher.objects.filter)(telegram_id=user_id)
    teacher_obj = await sync_to_async(teacher.first)()
    
    if not teacher_obj:
        await message.answer(
            "❌ Siz avtorizatsiyadan o'tmagansiz. Iltimos, /start buyrug'ini bosing.",
            reply_markup=get_remove_keyboard()
        )
        return
    
    # Haftalik darslarni olish
    slots = await sync_to_async(
        lambda: list(TimetableSlot.objects.filter(
            teacher=teacher_obj
        ).order_by('day_of_week', 'pair_number'))
    )()
    
    if not slots:
        await message.answer("📊 Sizda darslar yo'q.")
        return
    
    # Jadvalni formatlash
    response = "📊 **Haftalik dars jadvalingiz:**\n\n"
    
    current_day = None
    for slot in slots:
        if slot.day_of_week != current_day:
            current_day = slot.day_of_week
            day_name = _get_day_name(current_day)
            response += f"--- {day_name} ---\n\n"
        
        lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
        response += f"🔹 {slot.pair_number}-para: {slot.subject.name} ({lesson_type_uz})\n"
        response += f"   👥 {slot.group_name} | 🚪 {slot.room.name}\n\n"
    
    await message.answer(response, parse_mode='Markdown')


def _get_day_name(day_of_week):
    """Hafta kunini o'zbekcha nomini qaytarish"""
    days = {
        1: 'Dushanba',
        2: 'Seshanba',
        3: 'Chorshanba',
        4: 'Payshanba',
        5: 'Juma',
        6: 'Shanba',
    }
    return days.get(day_of_week, str(day_of_week))


# ==================== ADMIN HANDLERS ====================

async def check_admin(message: types.Message):
    """Foydalanuvchi admin ekanligini tekshirish"""
    user_id = message.from_user.id
    if user_id == SUPERADMIN_ID:
        return True
    
    teacher = await sync_to_async(Teacher.objects.filter)(telegram_id=user_id)
    teacher_obj = await sync_to_async(teacher.first)()
    
    if teacher_obj and (teacher_obj.is_admin or teacher_obj.is_superadmin):
        return True
    return False


@router.message(F.text == "👨‍🏫 O'qituvchi qo'shish")
async def cmd_add_teacher(message: types.Message, state: FSMContext):
    """O'qituvchi qo'shishni boshlash"""
    if not await check_admin(message):
        await message.answer("❌ Sizda bu amalni bajarish uchun huquq yo'q.")
        return
    
    await state.clear()
    await message.answer("👨‍🏫 O'qituvchi qo'shish\n\nIltimos, o'qituvchining to'liq ismini kiriting:")
    await state.set_state(AdminStates.teacher_name)


@router.message(AdminStates.teacher_name)
async def process_teacher_name(message: types.Message, state: FSMContext):
    """O'qituvchi ismini qabul qilish"""
    await state.update_data(full_name=message.text)
    await message.answer("Darajani tanlang:", reply_markup=get_degree_keyboard())
    await state.set_state(AdminStates.teacher_degree)


@router.message(AdminStates.teacher_degree)
async def process_teacher_degree(message: types.Message, state: FSMContext):
    """O'qituvchi darajasini qabul qilish"""
    degree_map = {
        'Professor': 'professor',
        'Dotsent': 'dotsent',
        'Katta o\'qituvchi': 'katta_oqituvchi',
        'Assistent': 'assistent',
    }
    degree = degree_map.get(message.text, 'assistent')
    await state.update_data(degree=degree)
    await message.answer("Telefon raqamini kiriting (masalan: 998901234567):", reply_markup=get_remove_keyboard())
    await state.set_state(AdminStates.teacher_phone)


@router.message(AdminStates.teacher_phone)
async def process_teacher_phone(message: types.Message, state: FSMContext):
    """O'qituvchi telefon raqamini qabul qilish"""
    phone = message.text.replace('+', '').replace(' ', '').replace('-', '')
    
    # Telefon raqam unik ekanligini tekshirish
    existing = await sync_to_async(Teacher.objects.filter)(phone_number=phone)
    if await sync_to_async(existing.exists)():
        await message.answer("❌ Bu telefon raqam allaqachon ro'yxatdan o'tgan. Boshqa raqam kiriting:")
        return
    
    await state.update_data(phone_number=phone)
    await message.answer("Kunlik maksimal soat sonini kiriting (masalan: 4):")
    await state.set_state(AdminStates.teacher_max_hours)


@router.message(AdminStates.teacher_max_hours)
async def process_teacher_max_hours(message: types.Message, state: FSMContext):
    """O'qituvchi kunlik maksimal soatini qabul qilish"""
    try:
        max_hours = int(message.text)
        await state.update_data(max_daily_hours=max_hours)
        await message.answer("Tanaffus soatlarini kiriting (masalan: 1 - har 3 paradan keyin 1 para tanaffus):")
        await state.set_state(AdminStates.teacher_rest_hours)
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting:")


@router.message(AdminStates.teacher_rest_hours)
async def process_teacher_rest_hours(message: types.Message, state: FSMContext):
    """O'qituvchi tanaffus soatlarini qabul qilish"""
    try:
        rest_hours = int(message.text)
        data = await state.get_data()
        
        # O'qituvchini yaratish
        teacher = await sync_to_async(Teacher.objects.create)(
            full_name=data['full_name'],
            degree=data['degree'],
            phone_number=data['phone_number'],
            max_daily_hours=data['max_daily_hours'],
            rest_hours_required=rest_hours
        )
        
        await message.answer(
            f"✅ O'qituvchi muvaffaqiyatli qo'shildi!\n\n"
            f"👤 Ism: {teacher.full_name}\n"
            f"🎓 Daraja: {teacher.get_degree_display()}\n"
            f"📱 Telefon: {teacher.phone_number}",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting:")


@router.message(F.text == "📚 Fan qo'shish")
async def cmd_add_subject(message: types.Message, state: FSMContext):
    """Fan qo'shishni boshlash"""
    if not await check_admin(message):
        await message.answer("❌ Sizda bu amalni bajarish uchun huquq yo'q.")
        return
    
    await state.clear()
    await message.answer("📚 Fan qo'shish\n\nIltimos, fan nomini kiriting:")
    await state.set_state(AdminStates.subject_name)


@router.message(AdminStates.subject_name)
async def process_subject_name(message: types.Message, state: FSMContext):
    """Fan nomini qabul qilish"""
    await state.update_data(name=message.text)
    await message.answer("Fan kodini kiriting (masalan: MATH101):")
    await state.set_state(AdminStates.subject_code)


@router.message(AdminStates.subject_code)
async def process_subject_code(message: types.Message, state: FSMContext):
    """Fan kodini qabul qilish"""
    code = message.text.upper()
    
    # Kod unik ekanligini tekshirish
    existing = await sync_to_async(Subject.objects.filter)(code=code)
    if await sync_to_async(existing.exists)():
        await message.answer("❌ Bu fan kodi allaqachon mavjud. Boshqa kod kiriting:")
        return
    
    data = await state.get_data()
    
    subject = await sync_to_async(Subject.objects.create)(
        name=data['name'],
        code=code
    )
    
    await message.answer(
        f"✅ Fan muvaffaqiyatli qo'shildi!\n\n"
        f"📚 Nomi: {subject.name}\n"
        f"🔢 Kodi: {subject.code}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@router.message(F.text == "🚪 Auditoriya qo'shish")
async def cmd_add_room(message: types.Message, state: FSMContext):
    """Auditoriya qo'shishni boshlash"""
    if not await check_admin(message):
        await message.answer("❌ Sizda bu amalni bajarish uchun huquq yo'q.")
        return
    
    await state.clear()
    await message.answer("🚪 Auditoriya qo'shish\n\nIltimos, auditoriya nomini kiriting (masalan: 302-xona):")
    await state.set_state(AdminStates.room_name)


@router.message(AdminStates.room_name)
async def process_room_name(message: types.Message, state: FSMContext):
    """Auditoriya nomini qabul qilish"""
    await state.update_data(name=message.text)
    await message.answer("Auditoriya sig'imini kiriting (masalan: 30):")
    await state.set_state(AdminStates.room_capacity)


@router.message(AdminStates.room_capacity)
async def process_room_capacity(message: types.Message, state: FSMContext):
    """Auditoriya sig'imini qabul qilish"""
    try:
        capacity = int(message.text)
        data = await state.get_data()
        
        room = await sync_to_async(Room.objects.create)(
            name=data['name'],
            capacity=capacity
        )
        
        await message.answer(
            f"✅ Auditoriya muvaffaqiyatli qo'shildi!\n\n"
            f"🚪 Nomi: {room.name}\n"
            f"👥 Sig'imi: {room.capacity} o'rin",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting:")


@router.message(F.text == "📝 O'quv rejasi qo'shish")
async def cmd_add_course_plan(message: types.Message, state: FSMContext):
    """O'quv rejasi qo'shishni boshlash"""
    if not await check_admin(message):
        await message.answer("❌ Sizda bu amalni bajarish uchun huquq yo'q.")
        return
    
    await state.clear()
    
    # Fanlarni ro'yxatini olish
    subjects = await sync_to_async(list)(Subject.objects.all())
    
    if not subjects:
        await message.answer("❌ Avval fan qo'shing!")
        return
    
    subject_list = "\n".join([f"{i+1}. {s.name} ({s.code})" for i, s in enumerate(subjects)])
    await message.answer(
        f"📝 O'quv rejasi qo'shish\n\n"
        f"Mavjud fanlar:\n{subject_list}\n\n"
        f"Iltimos, fan kodini kiriting:"
    )
    await state.set_state(AdminStates.course_subject)


@router.message(AdminStates.course_subject)
async def process_course_subject(message: types.Message, state: FSMContext):
    """Fan kodini qabul qilish"""
    code = message.text.upper()
    subject = await sync_to_async(Subject.objects.filter)(code=code).first()
    
    if not subject:
        await message.answer("❌ Fan topilmadi. Kodni tekshirib qayta kiriting:")
        return
    
    await state.update_data(subject=subject)
    
    # O'qituvchilarni ro'yxatini olish
    teachers = await sync_to_async(list)(Teacher.objects.all())
    
    if not teachers:
        await message.answer("❌ Avval o'qituvchi qo'shing!")
        return
    
    teacher_list = "\n".join([f"{i+1}. {t.full_name}" for i, t in enumerate(teachers)])
    await message.answer(
        f"Mavjud o'qituvchilar:\n{teacher_list}\n\n"
        f"Iltimos, o'qituvchi ismini kiriting:"
    )
    await state.set_state(AdminStates.course_teacher)


@router.message(AdminStates.course_teacher)
async def process_course_teacher(message: types.Message, state: FSMContext):
    """O'qituvchi ismini qabul qilish"""
    full_name = message.text
    teacher = await sync_to_async(Teacher.objects.filter)(full_name__icontains=full_name).first()
    
    if not teacher:
        await message.answer("❌ O'qituvchi topilmadi. Ismni tekshirib qayta kiriting:")
        return
    
    await state.update_data(teacher=teacher)
    await message.answer("Guruh nomini kiriting (masalan: KI-210):")
    await state.set_state(AdminStates.course_group)


@router.message(AdminStates.course_group)
async def process_course_group(message: types.Message, state: FSMContext):
    """Guruh nomini qabul qilish"""
    await state.update_data(group_name=message.text)
    await message.answer("Ma'ruza soatlari sonini kiriting (haftada, masalan: 2):")
    await state.set_state(AdminStates.course_lecture_hours)


@router.message(AdminStates.course_lecture_hours)
async def process_course_lecture_hours(message: types.Message, state: FSMContext):
    """Ma'ruza soatlarini qabul qilish"""
    try:
        lecture_hours = int(message.text)
        await state.update_data(lecture_hours_per_week=lecture_hours)
        await message.answer("Seminar soatlari sonini kiriting (haftada, masalan: 2):")
        await state.set_state(AdminStates.course_seminar_hours)
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting:")


@router.message(AdminStates.course_seminar_hours)
async def process_course_seminar_hours(message: types.Message, state: FSMContext):
    """Seminar soatlarini qabul qilish"""
    try:
        seminar_hours = int(message.text)
        data = await state.get_data()
        
        course_plan = await sync_to_async(CoursePlan.objects.create)(
            subject=data['subject'],
            teacher=data['teacher'],
            group_name=data['group_name'],
            lecture_hours_per_week=data['lecture_hours_per_week'],
            seminar_hours_per_week=seminar_hours
        )
        
        await message.answer(
            f"✅ O'quv rejasi muvaffaqiyatli qo'shildi!\n\n"
            f"📚 Fan: {course_plan.subject.name}\n"
            f"👨‍🏫 O'qituvchi: {course_plan.teacher.full_name}\n"
            f"👥 Guruh: {course_plan.group_name}\n"
            f"📖 Ma'ruza: {course_plan.lecture_hours_per_week} soat/hafta\n"
            f"💻 Seminar: {course_plan.seminar_hours_per_week} soat/hafta",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting:")


@router.message(F.text == "🔄 Jadvalni yangilash")
async def cmd_regenerate_schedule(message: types.Message):
    """Jadvalni qayta generatsiya qilish"""
    if not await check_admin(message):
        await message.answer("❌ Sizda bu amalni bajarish uchun huquq yo'q.")
        return
    
    await message.answer("🔄 Jadval generatsiyasi boshlanmoqda...")
    
    try:
        from django.core.management import call_command
        await sync_to_async(call_command)('generate_schedule')
        await message.answer("✅ Jadval muvaffaqiyatli yangilandi!", reply_markup=get_admin_keyboard())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")


@router.message(F.text == "⚙️ Tizim sozlamalari")
async def cmd_system_settings(message: types.Message, state: FSMContext):
    """Tizim sozlamalarini ko'rsatish va o'zgartirish"""
    user_id = message.from_user.id
    
    # Faqat superadmin
    if user_id != SUPERADMIN_ID:
        await message.answer("❌ Bu amalni faqat superadmin bajarishi mumkin.")
        return
    
    # Hozirgi sozlamalarni olish
    settings_obj = await sync_to_async(SystemSettings.objects.first)()
    
    if settings_obj:
        await message.answer(
            f"⚙️ Tizim sozlamalari\n\n"
            f"📊 1 stavka = {settings_obj.hours_per_stavka} soat/hafta\n\n"
            f"O'zgartirish uchun yangi qiymatni kiriting:",
            reply_markup=get_remove_keyboard()
        )
    else:
        await message.answer(
            "⚙️ Tizim sozlamalari\n\n"
            "Hozircha sozlamalar yo'q. 1 stavkada nechi soat bo'lishini kiriting:",
            reply_markup=get_remove_keyboard()
        )
    
    await state.set_state(AdminStates.settings_hours_per_stavka)


@router.message(AdminStates.settings_hours_per_stavka)
async def process_settings_hours(message: types.Message, state: FSMContext):
    """Tizim sozlamalarini saqlash"""
    try:
        hours = int(message.text)
        
        if hours < 1 or hours > 40:
            await message.answer("❌ Soatlar soni 1 dan 40 gacha bo'lishi kerak. Qayta kiriting:")
            return
        
        # Sozlamalarni yangilash yoki yaratish
        settings_obj = await sync_to_async(SystemSettings.objects.first)()
        
        if settings_obj:
            await sync_to_async(settings_obj.save)(update_fields=['hours_per_stavka'])
        else:
            await sync_to_async(SystemSettings.objects.create)(hours_per_stavka=hours)
        
        await message.answer(
            f"✅ Tizim sozlamalari yangilandi!\n\n"
            f"📊 Endi 1 stavka = {hours} soat/hafta\n\n"
            f"Bu o'zgarish jadval generatsiyasida qo'llaniladi.",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting:")


@router.message(F.text == "📥 Guruh jadvalini yuklab olish")
async def cmd_export_group_schedule(message: types.Message, state: FSMContext):
    """Guruh jadvalini yuklab olish"""
    if not await check_admin(message):
        await message.answer("❌ Sizda bu amalni bajarish uchun huquq yo'q.")
        return
    
    await state.clear()
    
    # Mavjud guruhlarni olish
    groups = await sync_to_async(
        lambda: list(TimetableSlot.objects.values_list('group_name', flat=True).distinct())
    )()
    
    if not groups:
        await message.answer("❌ Jadvalda guruhlar topilmadi. Avval jadval generatsiya qiling.")
        return
    
    group_list = "\n".join([f"{i+1}. {group}" for i, group in enumerate(groups)])
    await message.answer(
        f"📥 Guruh jadvalini yuklab olish\n\n"
        f"Mavjud guruhlar:\n{group_list}\n\n"
        f"Iltimos, guruh nomini kiriting:"
    )
    await state.set_state(AdminStates.export_group_name)


@router.message(AdminStates.export_group_name)
async def process_export_group(message: types.Message, state: FSMContext):
    """Guruh jadvalini export qilish"""
    group_name = message.text
    
    # Guruh jadvalini olish
    slots = await sync_to_async(
        lambda: list(TimetableSlot.objects.filter(group_name=group_name).order_by('day_of_week', 'pair_number'))
    )()
    
    if not slots:
        await message.answer(f"❌ '{group_name}' guruh uchun jadval topilmadi.")
        await state.clear()
        return
    
    # CSV yaratish
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    
    # Header
    csv_writer.writerow(['Kun', 'Para', 'Fan', 'Dars turi', 'O\'qituvchi', 'Auditoriya'])
    
    # Ma'lumotlar
    for slot in slots:
        day_name = _get_day_name(slot.day_of_week)
        lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
        csv_writer.writerow([
            day_name,
            f"{slot.pair_number}-para",
            slot.subject.name,
            lesson_type_uz,
            slot.teacher.full_name,
            slot.room.name
        ])
    
    csv_buffer.seek(0)
    
    # PDF yaratish
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    
    # Jadval ma'lumotlari
    data = [['Kun', 'Para', 'Fan', 'Dars turi', 'O\'qituvchi', 'Auditoriya']]
    
    for slot in slots:
        day_name = _get_day_name(slot.day_of_week)
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
    table = Table(data)
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
    
    doc.build([table])
    pdf_buffer.seek(0)
    
    # CSV yuborish
    csv_buffer.seek(0)
    await message.answer_document(
        types.BufferedInputFile(
            csv_buffer.getvalue().encode('utf-8'),
            filename=f"{group_name}_jadval.csv"
        ),
        caption=f"📄 {group_name} guruh jadvali (CSV)"
    )
    
    # PDF yuborish
    pdf_buffer.seek(0)
    await message.answer_document(
        types.BufferedInputFile(
            pdf_buffer.getvalue(),
            filename=f"{group_name}_jadval.pdf"
        ),
        caption=f"📄 {group_name} guruh jadvali (PDF)"
    )
    
    await message.answer("✅ Jadval muvaffaqiyatli yuborildi!", reply_markup=get_admin_keyboard())
    await state.clear()
