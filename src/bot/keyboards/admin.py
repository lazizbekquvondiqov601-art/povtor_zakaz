from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_admin_keyboard(is_super_admin: bool = False, is_locked: bool = False) -> ReplyKeyboardMarkup:
    """Adminlar uchun asosiy menyu."""
    if is_super_admin:
        lock_text = "🟢 Tizimni OCHISH" if is_locked else "🔴 Tizimni YOPISH"
        kb = [
            [KeyboardButton(text=lock_text)],
            [KeyboardButton(text="✅ VIP Qo'shish"), KeyboardButton(text="❌ VIP Olish")],
            [KeyboardButton(text="🔒 Bloklash"), KeyboardButton(text="🔓 Blokdan ochish")],
            [KeyboardButton(text="📊 Hisobot"), KeyboardButton(text="📈 Statistika")],
            [KeyboardButton(text="📦 Qoldiqlar"), KeyboardButton(text="📅 Import Tahlili")],
            [KeyboardButton(text="📊 Asosiy Zakaz (OBR)"), KeyboardButton(text="📥 Kelgan Tovar")],
            [KeyboardButton(text="🔄 Majburiy Yangilash")],
            [KeyboardButton(text="🔍 Supplier Tahlil")],
            [KeyboardButton(text="⚙️ Sozlamalar")]
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
        input_field_placeholder="Admin buyruqlarini tanlang..."
    )
