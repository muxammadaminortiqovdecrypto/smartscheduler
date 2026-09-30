from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async
from django.conf import settings
from timetable.models import Teacher, TimetableSlot, Subject, Room, CoursePlan, SystemSettings
from .keyboards import get_phone_keyboard, get_main_keyboard, get_remove_keyboard, get_admin_keyboard, get_degree_keyboard, get_role_keyboard
import datetime


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


class StudentStates(StatesGroup):
    """Talaba uchun guruh tanlash"""
    waiting_for_group = State('waiting_for_group')


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
        # Talaba uchun guruh tanlash
        await message.answer(
            f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
            "Siz talabamisiz yoki o'qituvchimi?",
            reply_markup=get_role_keyboard()
        )


@router.message(F.text == "👨‍🎓 Talaba")
async def cmd_student_mode(message: types.Message, state: FSMContext):
    """Talaba rejimi - guruh tanlash"""
    await state.clear()
    
    # Barcha guruhlarni olish
    groups = await sync_to_async(
        lambda: list(TimetableSlot.objects.values_list('group_name', flat=True).distinct())
    )()
    
    if not groups:
        await message.answer("❌ Hozircha jadvalda guruhlar yo'q.")
        return
    
    # Inline keyboard yaratish
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for group in sorted(groups):
        buttons.append([InlineKeyboardButton(text=group, callback_data=f"select_group_{group}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        "👨‍🎓 Talaba rejimi\n\n"
        "O'zingizning guruhingizni tanlang:",
        reply_markup=keyboard
    )


@router.message(F.text == "👨‍🏫 O'qituvchi")
async def cmd_teacher_mode(message: types.Message, state: FSMContext):
    """O'qituvchi rejimi - telefon raqam orqali avtorizatsiya"""
    await state.clear()
    await message.answer(
        "👨‍🏫 O'qituvchi rejimi\n\n"
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
async def cmd_myday(message: types.Message, state: FSMContext):
    """Bugungi dars jadvalini ko'rsatish (talaba yoki o'qituvchi)"""
    user_id = message.from_user.id
    
    # Avval o'qituvchi ekanligini tekshirish
    teacher = await sync_to_async(Teacher.objects.filter)(telegram_id=user_id)
    teacher_obj = await sync_to_async(teacher.first)()
    
    if teacher_obj:
        # O'qituvchi rejimi
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
            ).select_related('subject', 'teacher', 'room').order_by('pair_number'))
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
    else:
        # Talaba rejimi - guruhni state'dan olish
        data = await state.get_data()
        group_name = data.get('selected_group')
        
        if not group_name:
            await message.answer(
                "❌ Avval guruh tanlang. /start buyrug'ini bosing.",
                reply_markup=get_remove_keyboard()
            )
            return
        
        # Bugungi kunni aniqlash
        today = datetime.date.today()
        day_of_week = today.isoweekday()
        
        if day_of_week == 7:
            await message.answer("🎉 Bugun yakshanba! Darslar yo'q.")
            return
        
        if day_of_week > 6:
            await message.answer("Bugun dars kuni emas.")
            return
        
        # Guruhning bugungi darslarini olish
        slots = await sync_to_async(
            lambda: list(TimetableSlot.objects.filter(
                group_name=group_name,
                day_of_week=day_of_week
            ).select_related('subject', 'teacher', 'room').order_by('pair_number'))
        )()
        
        if not slots:
            day_name = _get_day_name(day_of_week)
            await message.answer(f"📅 {day_name} uchun darslar yo'q.")
            return
        
        # Jadvalni formatlash
        day_name = _get_day_name(day_of_week)
        response = f"📅 **Bugungi dars jadvalingiz ({group_name} - {day_name}):**\n\n"
        
        for slot in slots:
            lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
            response += f"🔹 **{slot.pair_number}-para:** {slot.subject.name} ({lesson_type_uz})\n"
            response += f"   �‍🏫 O'qituvchi: {slot.teacher.full_name}\n"
            response += f"   🚪 Auditoriya: {slot.room.name}\n\n"
        
        await message.answer(response, parse_mode='Markdown')


@router.message(F.text == '📊 Haftalik jadval')
async def cmd_weekly(message: types.Message, state: FSMContext):
    """Haftalik dars jadvalini ko'rsatish (talaba yoki o'qituvchi)"""
    user_id = message.from_user.id
    
    # Avval o'qituvchi ekanligini tekshirish
    teacher = await sync_to_async(Teacher.objects.filter)(telegram_id=user_id)
    teacher_obj = await sync_to_async(teacher.first)()
    
    if teacher_obj:
        # O'qituvchi rejimi
        # Haftalik darslarni olish
        slots = await sync_to_async(
            lambda: list(TimetableSlot.objects.filter(
                teacher=teacher_obj
            ).select_related('subject', 'teacher', 'room').order_by('day_of_week', 'pair_number'))
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
    else:
        # Talaba rejimi - guruhni state'dan olish
        data = await state.get_data()
        group_name = data.get('selected_group')
        
        if not group_name:
            await message.answer(
                "❌ Avval guruh tanlang. /start buyrug'ini bosing.",
                reply_markup=get_remove_keyboard()
            )
            return
        
        # Guruhning haftalik darslarini olish
        slots = await sync_to_async(
            lambda: list(TimetableSlot.objects.filter(
                group_name=group_name
            ).select_related('subject', 'teacher', 'room').order_by('day_of_week', 'pair_number'))
        )()
        
        if not slots:
            await message.answer("📊 Guruhda darslar yo'q.")
            return
        
        # Jadvalni formatlash
        response = f"📊 **Haftalik dars jadvalingiz ({group_name}):**\n\n"
        
        current_day = None
        for slot in slots:
            if slot.day_of_week != current_day:
                current_day = slot.day_of_week
                day_name = _get_day_name(current_day)
                response += f"--- {day_name} ---\n\n"
            
            lesson_type_uz = "Ma'ruza" if slot.lesson_type == 'lecture' else "Seminar"
            response += f"🔹 {slot.pair_number}-para: {slot.subject.name} ({lesson_type_uz})\n"
            response += f"   �‍🏫 {slot.teacher.full_name} | 🚪 {slot.room.name}\n\n"
        
        await message.answer(response, parse_mode='Markdown')


@router.message(F.text == "📥 Jadval yuklab olish")
async def cmd_export(message: types.Message, state: FSMContext):
    """Jadval yuklab olish (talaba yoki o'qituvchi)"""
    user_id = message.from_user.id
    
    # Avval o'qituvchi ekanligini tekshirish
    teacher = await sync_to_async(Teacher.objects.filter)(telegram_id=user_id)
    teacher_obj = await sync_to_async(teacher.first)()
    
    if teacher_obj:
        # O'qituvchi rejimi - o'z jadvalini yuklab olish
        # Web link yuborish (chunki PDF/CSV generatsiya web view orqali amalga oshiriladi)
        await message.answer(
            "📥 Jadval yuklab olish\n\n"
            "Jadvalni yuklab olish uchun web saytdan foydalaning:\n"
            "http://localhost:8000/schedule/all/\n\n"
            "Yoki admin panel orqali export qiling.",
            reply_markup=get_remove_keyboard()
        )
    else:
        # Talaba rejimi - guruh tanlash
        data = await state.get_data()
        group_name = data.get('selected_group')
        
        if not group_name:
            await message.answer(
                "❌ Avval guruh tanlang. /start buyrug'ini bosing.",
                reply_markup=get_remove_keyboard()
            )
            return
        
        # Guruh jadvalini yuklab olish uchun web link yuborish
        await message.answer(
            f"📥 {group_name} guruh jadvalini yuklab olish\n\n"
            f"CSV: http://localhost:8000/schedule/{group_name}/?format=csv\n"
            f"PDF: http://localhost:8000/schedule/{group_name}/?format=pdf\n\n"
            "Yoki admin panel orqali export qiling.",
            reply_markup=get_remove_keyboard()
        )


@router.message(F.text == "🔙 Orqaga")
async def cmd_back(message: types.Message):
    """Orqaga qaytish"""
    await message.answer(
        "🏠 Bosh menyu",
        reply_markup=get_role_keyboard()
    )


@router.message(F.text == "📊 Statistika")
async def cmd_statistics(message: types.Message):
    """Statistika ko'rish (superadmin)"""
    if message.from_user.id != SUPERADMIN_ID:
        await message.answer("❌ Bu amal faqat superadmin uchun.")
        return
    
    # Statistikani olish
    teachers_count = await sync_to_async(Teacher.objects.count)()
    subjects_count = await sync_to_async(Subject.objects.count)()
    rooms_count = await sync_to_async(Room.objects.count)()
    groups_count = await sync_to_async(
        lambda: TimetableSlot.objects.values_list('group_name', flat=True).distinct().count()
    )()
    slots_count = await sync_to_async(TimetableSlot.objects.count)()
    course_plans_count = await sync_to_async(CoursePlan.objects.count)()
    
    response = "📊 **Tizim statistikasi:**\n\n"
    response += f"👨‍🏫 O'qituvchilar: {teachers_count} ta\n"
    response += f"📚 Fanlar: {subjects_count} ta\n"
    response += f"🚪 Auditoriyalar: {rooms_count} ta\n"
    response += f"👥 Guruhlar: {groups_count} ta\n"
    response += f"📝 O'quv rejalari: {course_plans_count} ta\n"
    response += f"📅 Jadval slotlari: {slots_count} ta\n"
    
    await message.answer(response, parse_mode='Markdown')


@router.message(F.text == "🔄 Jadval yangilash")
async def cmd_regenerate_schedule(message: types.Message):
    """Jadvalni yangilash (superadmin)"""
    if message.from_user.id != SUPERADMIN_ID:
        await message.answer("❌ Bu amal faqat superadmin uchun.")
        return
    
    await message.answer("🔄 Jadval yangilanmoqda...")
    
    # Jadval generatsiyasini ishga tushirish
    import subprocess
    try:
        result = subprocess.run(
            ['python', 'manage.py', 'generate_schedule'],
            capture_output=True,
            text=True,
            cwd='d:/smartscheduler'
        )
        
        if result.returncode == 0:
            await message.answer("✅ Jadval muvaffaqiyatli yangilandi!")
        else:
            await message.answer(f"❌ Xatolik: {result.stderr}")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")


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


@router.message(F.text == "📥 Guruh jadvalini yuklab olish")
async def cmd_export_schedule(message: types.Message):
    """Guruh jadvalini yuklab olish - inline keyboard yuborish"""
    print(f"🔍 EXPORT HANDLER TRIGGERED: {message.text}")
    if not await check_admin(message):
        await message.answer("❌ Sizda bu amalni bajarish uchun huquq yo'q.")
        return
    
    from .keyboards import get_admin_inline_keyboard
    await message.answer(
        "⚙️ Admin panel",
        reply_markup=get_admin_inline_keyboard()
    )
    print("🔍 INLINE KEYBOARD SENT")


@router.message(F.text == "/settings")
async def cmd_settings(message: types.Message, state: FSMContext):
    """Tizim sozlamalarini o'zgartirish"""
    user_id = message.from_user.id
    
    # Faqat superadmin
    if user_id != SUPERADMIN_ID:
        await message.answer("❌ Bu amalni faqat superadmin bajarishi mumkin.")
        return
    
    await state.clear()
    
    # Hozirgi sozlamalarni olish
    settings_obj = await sync_to_async(SystemSettings.objects.first)()
    
    if settings_obj:
        allowed_groups = settings_obj.get_allowed_groups()
        groups_text = ", ".join(allowed_groups) if allowed_groups else "Yo'q"
        
        await message.answer(
            f"⚙️ Tizim sozlamalari\n\n"
            f"📊 1 stavka = {settings_obj.hours_per_stavka} soat/hafta\n"
            f"👥 Ruxsat etilgan guruhlar: {groups_text}\n\n"
            f"O'zgartirish uchun:\n"
            f"/stavka [soat] - 1 stavkada soatlar soni\n"
            f"/group_add [nomi] - Guruh qo'shish\n"
            f"/group_remove [nomi] - Guruh o'chirish",
            reply_markup=get_remove_keyboard()
        )
    else:
        await message.answer(
            "⚙️ Tizim sozlamalari\n\n"
            "Hozircha sozlamalar yo'q. 1 stavkada nechi soat bo'lishini kiriting:\n"
            "/stavka [soat]",
            reply_markup=get_remove_keyboard()
        )
    
    await state.set_state(AdminStates.settings_hours_per_stavka)


@router.message(F.text.startswith("/stavka"))
async def cmd_set_stavka(message: types.Message):
    """Stavka soatlarini o'zgartirish"""
    user_id = message.from_user.id
    
    if user_id != SUPERADMIN_ID:
        await message.answer("❌ Faqat superadmin.")
        return
    
    try:
        hours = int(message.text.split()[1])
        
        if hours < 1 or hours > 40:
            await message.answer("❌ Soatlar soni 1 dan 40 gacha bo'lishi kerak.")
            return
        
        settings_obj = await sync_to_async(SystemSettings.objects.first)()
        
        if settings_obj:
            await sync_to_async(settings_obj.save)(update_fields=['hours_per_stavka'])
        else:
            await sync_to_async(SystemSettings.objects.create)(hours_per_stavka=hours)
        
        await message.answer(f"✅ 1 stavka = {hours} soat/hafta")
    except (IndexError, ValueError):
        await message.answer("❌ Format: /stavka [soat] (masalan: /stavka 20)")


@router.message(F.text.startswith("/group_add"))
async def cmd_add_group(message: types.Message):
    """Guruh qo'shish"""
    user_id = message.from_user.id
    
    if user_id != SUPERADMIN_ID:
        await message.answer("❌ Faqat superadmin.")
        return
    
    try:
        group_name = message.text.split()[1]
        
        settings_obj = await sync_to_async(SystemSettings.objects.first)()
        if not settings_obj:
            await sync_to_async(SystemSettings.objects.create)()
            settings_obj = await sync_to_async(SystemSettings.objects.first)()
        
        settings_obj.add_group(group_name)
        await message.answer(f"✅ Guruh '{group_name}' qo'shildi.")
    except IndexError:
        await message.answer("❌ Format: /group_add [nomi] (masalan: /group_add KI-220)")


@router.message(F.text.startswith("/group_remove"))
async def cmd_remove_group(message: types.Message):
    """Guruh o'chirish"""
    user_id = message.from_user.id
    
    if user_id != SUPERADMIN_ID:
        await message.answer("❌ Faqat superadmin.")
        return
    
    try:
        group_name = message.text.split()[1]
        
        settings_obj = await sync_to_async(SystemSettings.objects.first)()
        if not settings_obj:
            await message.answer("❌ Tizim sozlamalari yo'q.")
            return
        
        settings_obj.remove_group(group_name)
        await message.answer(f"✅ Guruh '{group_name}' o'chirildi.")
    except IndexError:
        await message.answer("❌ Format: /group_remove [nomi] (masalan: /group_remove KI-220)")


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


def _get_day_name(day_of_week):
    """Kun nomini qaytarish"""
    day_names = {
        1: 'Dushanba',
        2: 'Seshanba',
        3: 'Chorshanba',
        4: 'Payshanba',
        5: 'Juma',
        6: 'Shanba',
    }
    return day_names.get(day_of_week, str(day_of_week))
