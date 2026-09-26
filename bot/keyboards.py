from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def get_phone_keyboard():
    """Telefon raqam yuborish tugmasi bilan klaviatura"""
    button = KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)
    keyboard = ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True)
    return keyboard


def get_main_keyboard():
    """Asosiy klaviatura"""
    buttons = [
        [KeyboardButton(text="📅 Bugungi dars jadvalim")],
        [KeyboardButton(text="📊 Haftalik jadval")],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    return keyboard


def get_admin_keyboard():
    """Admin klaviaturasi"""
    buttons = [
        [KeyboardButton(text="👨‍🏫 O'qituvchi qo'shish")],
        [KeyboardButton(text="📚 Fan qo'shish")],
        [KeyboardButton(text="🚪 Auditoriya qo'shish")],
        [KeyboardButton(text="📝 O'quv rejasi qo'shish")],
        [KeyboardButton(text="⚙️ Tizim sozlamalari")],
        [KeyboardButton(text="🔄 Jadvalni yangilash")],
        [KeyboardButton(text="📅 Bugungi dars jadvalim")],
        [KeyboardButton(text="📊 Haftalik jadval")],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    return keyboard


def get_degree_keyboard():
    """Daraja tanlash klaviaturasi"""
    buttons = [
        [KeyboardButton(text="Professor")],
        [KeyboardButton(text="Dotsent")],
        [KeyboardButton(text="Katta o'qituvchi")],
        [KeyboardButton(text="Assistent")],
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    return keyboard


def get_remove_keyboard():
    """Klaviaturani olib tashlash"""
    return ReplyKeyboardRemove()
