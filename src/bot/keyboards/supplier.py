from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_supplier_keyboard() -> ReplyKeyboardMarkup:
    """Yetkazib beruvchilar uchun asosiy menyu."""
    kb = [
        [KeyboardButton(text="📦 Zakazlarim (Yangi)"), KeyboardButton(text="⏳ Jarayonda")],
        [KeyboardButton(text="📈 Statistika"), KeyboardButton(text="📅 Import Tahlili")],
        [KeyboardButton(text="📝 Ismni o'zgartirish"), KeyboardButton(text="🔑 Admin Bo'lish")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb, 
        resize_keyboard=True,
        input_field_placeholder="Yetkazib beruvchi buyruqlari..."
    )
