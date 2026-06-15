from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import calendar

def get_close_keyboard() -> InlineKeyboardMarkup:
    """Xabarni o'chirish tugmasi."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]
    ])

def get_inline_calendar(year: int, month: int, state_label: str) -> InlineKeyboardMarkup:
    """Telegram inline klaviaturasi shaklida oylik kalendar yaratadi."""
    kb = []
    
    months_uz = [
        "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", 
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
    ]
    month_name = months_uz[month - 1]
    
    # Oy va yil sarlavhasi
    kb.append([
        InlineKeyboardButton(text=f"📅 {month_name} {year}", callback_data=f"cal:{state_label}:ignore:0")
    ])
    
    # Hafta kunlari sarlavhasi
    kb.append([
        InlineKeyboardButton(text=d, callback_data=f"cal:{state_label}:ignore:0")
        for d in ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
    ])
    
    # Kunlar setkasi
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append(InlineKeyboardButton(text=" ", callback_data=f"cal:{state_label}:ignore:0"))
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                week_row.append(InlineKeyboardButton(text=str(day), callback_data=f"cal:{state_label}:day:{date_str}"))
        kb.append(week_row)
        
    # Navigatsiya tugmalari
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    kb.append([
        InlineKeyboardButton(text="◀️ Oy", callback_data=f"cal:{state_label}:nav:{prev_year}-{prev_month:02d}"),
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stat_sotuv"),
        InlineKeyboardButton(text="Oy ▶️", callback_data=f"cal:{state_label}:nav:{next_year}-{next_month:02d}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)
