from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup


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
        [KeyboardButton(text="� Guruh jadvalini yuklab olish")],
        [KeyboardButton(text="�🔄 Jadvalni yangilash")],
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


def get_admin_inline_keyboard():
    """Admin inline klaviaturasi - tizimli tartib"""
    buttons = [
        [
            InlineKeyboardButton(text="📚 Resurslar", callback_data="admin_resources"),
        ],
        [
            InlineKeyboardButton(text="👨‍🏫 O'qituvchilar", callback_data="admin_teacher"),
            InlineKeyboardButton(text="📚 Fanlar", callback_data="admin_subject"),
        ],
        [
            InlineKeyboardButton(text="🚪 Auditoriyalar", callback_data="admin_room"),
            InlineKeyboardButton(text="👥 Guruhlar", callback_data="admin_group"),
        ],
        [
            InlineKeyboardButton(text="📝 O'quv rejalari", callback_data="admin_course"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Tizim sozlamalari", callback_data="admin_settings"),
        ],
        [
            InlineKeyboardButton(text="🔄 Jadval yangilash", callback_data="admin_regenerate"),
            InlineKeyboardButton(text="📥 Jadval yuklab olish", callback_data="admin_export"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_resources_inline_keyboard():
    """Resurslar inline klaviaturasi"""
    buttons = [
        [
            InlineKeyboardButton(text="�‍🏫 O'qituvchilar", callback_data="admin_teacher"),
            InlineKeyboardButton(text="📚 Fanlar", callback_data="admin_subject"),
        ],
        [
            InlineKeyboardButton(text="🚪 Auditoriyalar", callback_data="admin_room"),
            InlineKeyboardButton(text="👥 Guruhlar", callback_data="admin_group"),
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_teacher_list_inline_keyboard(teachers):
    """O'qituvchilar ro'yxati inline klaviaturasi"""
    buttons = []
    for teacher in teachers:
        buttons.append([InlineKeyboardButton(text=teacher.full_name, callback_data=f"teacher_{teacher.id}")])
    
    buttons.append([InlineKeyboardButton(text="➕ Yangi o'qituvchi qo'shish", callback_data="teacher_add")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_subject_list_inline_keyboard(subjects):
    """Fanlar ro'yxati inline klaviaturasi"""
    buttons = []
    for subject in subjects:
        buttons.append([InlineKeyboardButton(text=f"{subject.name} ({subject.code})", callback_data=f"subject_{subject.id}")])
    
    buttons.append([InlineKeyboardButton(text="➕ Yangi fan qo'shish", callback_data="subject_add")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_room_list_inline_keyboard(rooms):
    """Auditoriyalar ro'yxati inline klaviaturasi"""
    buttons = []
    for room in rooms:
        buttons.append([InlineKeyboardButton(text=f"{room.name} ({room.capacity})", callback_data=f"room_{room.id}")])
    
    buttons.append([InlineKeyboardButton(text="➕ Yangi auditoriya qo'shish", callback_data="room_add")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_group_list_inline_keyboard(groups):
    """Guruhlar ro'yxati inline klaviaturasi"""
    buttons = []
    for group in groups:
        buttons.append([InlineKeyboardButton(text=group, callback_data=f"group_{group}")])
    
    buttons.append([InlineKeyboardButton(text="➕ Yangi guruh qo'shish", callback_data="group_add")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
