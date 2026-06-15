from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_admin_keyboard(is_super_admin: bool = False, is_locked: bool = False) -> ReplyKeyboardMarkup:
    """Adminlar uchun asosiy menyu."""
    if is_super_admin:
        lock_text = "🟢 Tizimni OCHISH" if is_locked else "🔴 Tizimni YOPISH"
        kb = [
            [KeyboardButton(text="📊 Asosiy Zakaz (OBR)"), KeyboardButton(text="🔍 Supplier Tahlil")],
            [KeyboardButton(text="📈 Statistika"), KeyboardButton(text="📊 Hisobot")],
            [KeyboardButton(text="📦 Qoldiqlar"), KeyboardButton(text="📥 Kelgan Tovar")],
            [KeyboardButton(text="📅 Import Tahlili"), KeyboardButton(text="⚙️ Sozlamalar")],
            [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="🛠 Tizim Sozlamalari")]
        ]
    else:
        kb = [
            [KeyboardButton(text="📊 Hisobot"), KeyboardButton(text="📈 Statistika")],
            [KeyboardButton(text="📦 Qoldiqlar"), KeyboardButton(text="📅 Import Tahlili")],
            [KeyboardButton(text="📥 Kelgan Tovar"), KeyboardButton(text="🔄 Supplier Menyu")],
        ]
    
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Kerakli bo'limni tanlang..."
    )

def get_system_tools_keyboard(is_locked: bool = False) -> ReplyKeyboardMarkup:
    """Super Admin uchun tizim sozlamalari menyusi."""
    lock_text = "🟢 Tizimni OCHISH" if is_locked else "🔴 Tizimni YOPISH"
    kb = [
        [KeyboardButton(text=lock_text)],
        [KeyboardButton(text="🔄 Majburiy Yangilash")],
        [KeyboardButton(text="🗑 Bazani Tozalash")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_users_management_keyboard() -> ReplyKeyboardMarkup:
    """Super Admin uchun foydalanuvchilarni boshqarish menyusi."""
    kb = [
        [KeyboardButton(text="✅ VIP Qo'shish"), KeyboardButton(text="❌ VIP Olish")],
        [KeyboardButton(text="🔒 Bloklash"), KeyboardButton(text="🔓 Blokdan ochish")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
