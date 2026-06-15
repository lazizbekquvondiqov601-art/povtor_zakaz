import io
import uuid
import asyncio
import logging
import pandas as pd
from datetime import datetime
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext

import config
import db_manager
import auto_zakaz
import data_engine
from src.bot.init_bot import bot, OBR_CACHE, STAT_CACHE
from src.bot.keyboards.admin import get_admin_keyboard
from src.bot.keyboards.common import get_inline_calendar, get_close_keyboard
from src.bot.states.bot_states import SettingsManagement, AdminStates
from src.services.analytics_service import generate_macro_image, generate_sales_table_image
from src.utils.helpers import format_money

logger = logging.getLogger(__name__)
router = Router()

class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return db_manager.is_admin(message.from_user.id)

# --- SOZLAMALAR ---

@router.message(IsAdmin(), F.text == "⚙️ Sozlamalar")
@router.message(IsAdmin(), Command("settings"))
async def show_settings_handler(message: Message, state: FSMContext):
    logger.info(f"Admin {message.from_user.id} opened settings")
    await state.clear()
    settings = db_manager.get_all_settings()

    text = "<b>⚙️ Tahlil qoidalari:</b>\n\n"
    rules = [
        (f"<b>{i}-Qoida:</b> {int(settings.get(f'm{i}_min_days', 0))}-{int(settings.get(f'm{i}_max_days', 0))} kun, "
         f"{int(settings.get(f'm{i}_percentage', 0))}%+")
        for i in range(1, 5)
    ]
    text += "\n".join(rules)

    buttons = [
        [InlineKeyboardButton(text=f"✏️ {i}-Qoida", callback_data=f"edit_rule_{i}")] for i in range(1, 5)
    ]
    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# --- KELGAN TOVAR ---

@router.message(IsAdmin(), F.text == "📥 Kelgan Tovar")
async def kelgan_tovar_click(message: Message, state: FSMContext):
    logger.info(f"Admin {message.from_user.id} clicked Kelgan Tovar")
    await state.clear()
    now = datetime.now()
    await message.answer(
        "📥 <b>Kelgan yuk tahlili (Billz Import)</b>\n\n"
        "Kirim qilingan tovarlarni bilish uchun <b>boshlang'ich sanani</b> tanlang:",
        reply_markup=get_inline_calendar(now.year, now.month, "imp_start")
    )

# --- ASOSIY ZAKAZ (OBR) ---

@router.message(IsAdmin(), F.text == "📊 Asosiy Zakaz (OBR)")
async def auto_zakaz_click(message: Message):
    logger.info(f"Admin {message.from_user.id} requested OBR calculation")
    msg = await message.answer("⏳ <b>Asosiy Zakaz (OBR) hisoblanmoqda...</b>\n\nBu jarayon 10-20 soniya olishi mumkin.")

    df = await asyncio.to_thread(auto_zakaz.calculate_auto_zakaz, db_manager.engine)

    if df.empty:
        await msg.edit_text("✅ Hozirgi holat bo'yicha 'Zakaz' qilish kerak bo'lgan hech qanday tovar yo'q.")
        return

    session_id = str(uuid.uuid4())[:8]
    OBR_CACHE[session_id] = df

    cats = sorted(df['Категория'].unique().tolist())
    kb = []
    
    for c in cats:
        if not c: continue
        cat_id = str(uuid.uuid4())[:8]
        OBR_CACHE[f"cat_{cat_id}"] = c
        kb.append([InlineKeyboardButton(text=f"📁 {c}", callback_data=f"obrCat_{session_id}_{cat_id}")])

    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])

    await msg.edit_text(
        "📊 <b>ASOSIY ZAKAZ (OBR)</b>\n\nQaysi kategoriyani ko'rmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

# --- MAJBURIY YANGILASH ---

@router.message(IsAdmin(), F.text == "🔄 Majburiy Yangilash")
@router.message(IsAdmin(), Command("force_update"))
async def force_update_handler(message: Message):
    logger.info(f"Admin {message.from_user.id} requested force update")
    await message.answer("⏳ <b>Yangilash boshlandi...</b>\n\nBot ishlashda davom etadi. Jarayon yakunlangach sizga darhol xabar beriladi! 🔔")
    asyncio.create_task(run_update_and_notify(message.chat.id))

async def run_update_and_notify(chat_id: int):
    try:
        await asyncio.to_thread(data_engine.run_full_update)
        await bot.send_message(
            chat_id=chat_id,
            text="✅ <b>Barcha ma'lumotlar muvaffaqiyatli yangilandi!</b>\n\n"
                 "📊 Sotuvlar va Qoldiqlar oxirgi holatga keltirildi."
        )
    except Exception as e:
        logger.error(f"Error in force update: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ <b>Yangilash jarayonida jiddiy xatolik yuz berdi:</b>\n<code>{e}</code>"
        )

# --- HISOBOT ---

@router.message(IsAdmin(), F.text == "📊 Hisobot")
@router.message(IsAdmin(), Command("report"))
async def report_handler(message: Message):
    logger.info(f"Admin {message.from_user.id} requested full report")
    await message.answer("⏳ Hisobot tayyorlanmoqda...")
    report_df = await asyncio.to_thread(db_manager.get_full_report_data)

    if report_df.empty:
        await message.answer("⚠️ Ma'lumot yo'q.")
        return

    # Vaqtni Toshkent vaqtiga o'tkazish
    for col in report_df.select_dtypes(include=['datetimetz', 'datetime']).columns:
        if report_df[col].dt.tz is not None:
            report_df[col] = report_df[col].dt.tz_convert('Asia/Tashkent')
            report_df[col] = report_df[col].dt.tz_localize(None)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        report_df.to_excel(writer, index=False, sheet_name='Hisobot')
        worksheet = writer.sheets['Hisobot']
        for i, col in enumerate(report_df.columns):
            width = max(report_df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, width)

    output.seek(0)
    file = BufferedInputFile(output.getvalue(), filename=f"hisobot_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
    await message.answer_document(file, caption="✅ Hisobot tayyor.")

# --- STATISTIKA ---

@router.message(IsAdmin(), F.text == "📈 Statistika")
async def show_statistics(message: Message):
    logger.info(f"Admin {message.from_user.id} opened statistics menu")
    kb = [
        [InlineKeyboardButton(text="📦 Zakaz statistikasi", callback_data="stat_zakaz")],
        [InlineKeyboardButton(text="📊 Sotuv tahlili", callback_data="stat_sotuv")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]
    ]
    await message.answer(
        "📈 <b>STATISTIKA</b>\nQaysi bo'limni ko'rmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

# --- QOLDIQLAR ---

@router.message(IsAdmin(), F.text == "📦 Qoldiqlar")
async def show_stock_dates(message: Message):
    logger.info(f"Admin {message.from_user.id} opened stock dates")
    dates = db_manager.get_last_7_stock_dates()
    if not dates:
        await message.answer("⚠️ Hozircha qoldiqlar jadvalida ma'lumot mavjud emas.")
        return

    kb = []
    for d in dates:
        dt_obj = datetime.strptime(d, "%Y-%m-%d")
        pretty_date = dt_obj.strftime("%d.%m.%Y")
        kb.append([InlineKeyboardButton(text=f"📅 {pretty_date}", callback_data=f"stqDate_{d}")])
    
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])
    
    await message.answer(
        f"📦 <b>QOLDIQLAR TAHLILI</b>\n\n"
        f"Hisobotni ko'rish uchun oxirgi 7 kunlikdan sanani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
