import uuid
import asyncio
import io
import pandas as pd
from datetime import datetime, timezone, timedelta
from aiogram import Router, F, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import text

import src.database.db_manager as db_manager
import data_engine
import import_file
from src.bot.init_bot import bot, OBR_CACHE, STAT_CACHE
from src.services.analytics_service import generate_macro_image, generate_sales_table_image
from src.bot.keyboards.common import get_inline_calendar, get_close_keyboard
from src.utils.helpers import build_caption, format_money

router = Router()

# --- ORDER STATISTICS ---

@router.callback_query(F.data == "stat_zakaz")
async def stat_zakaz_click(callback: CallbackQuery):
    categories = db_manager.get_stat_categories_global()
    if not categories:
        await callback.answer("✅ Hozircha aktiv zakazlar yo'q.", show_alert=True)
        return
    kb = []
    for cat in categories:
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"stCat_{cat}")])
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stat_back")])
    await callback.message.edit_text(
        "📦 <b>ZAKAZ STATISTIKASI</b>\n\nKategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("stCat_"))
async def stat_category_click(callback: CallbackQuery):
    category = callback.data.split("stCat_", 1)[1]
    subs = db_manager.get_stat_subcategories_global(category)
    kb = []
    for sub in subs:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (category, sub)
        kb.append([InlineKeyboardButton(text=f"🔹 {sub}", callback_data=f"stSub_{unique_id}")])
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stat_back_root")])
    await callback.message.edit_text(
        f"📂 <b>{category}</b>\nIchki turlarni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("stSub_"))
async def stat_subcategory_click(callback: CallbackQuery):
    unique_id = callback.data.split("stSub_", 1)[1]
    data = STAT_CACHE.get(unique_id)
    if not data:
        await callback.answer("⚠️ Ma'lumot eskirgan, qaytadan oching.", show_alert=True)
        return
    category, subcategory = data
    total_packs = db_manager.get_stat_total_packs(category, subcategory)
    kb = [[InlineKeyboardButton(text="⬅️ Ortga qaytish", callback_data=f"stCat_{category}")]]
    await callback.message.edit_text(
        f"📊 <b>NATIJA:</b>\n\n📂 Kategoriya: <b>{category}</b>\n🔹 Podkategoriya: <b>{subcategory}</b>\n\n📦 Jami zakaz: <b>{int(total_packs)} pochka</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data == "stat_back_root")
async def stat_back_root(callback: CallbackQuery):
    categories = db_manager.get_stat_categories_global()
    kb = []
    for cat in categories:
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"stCat_{cat}")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])
    await callback.message.edit_text(
        "📊 <b>UMUMIY STATISTIKA</b>\n\nQaysi bo'limni ko'rmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data == "stat_back")
async def stat_back_to_main(callback: CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="📦 Zakaz statistikasi", callback_data="stat_zakaz")],
        [InlineKeyboardButton(text="📊 Sotuv tahlili", callback_data="stat_sotuv")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]
    ]
    await callback.message.edit_text(
        "📈 <b>STATISTIKA</b>\nQaysi bo'limni ko'rmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

# --- SALES ANALYSIS ---

@router.callback_query(F.data == "stat_sotuv")
async def stat_sotuv_click(callback: CallbackQuery):
    today = datetime.now(timezone(timedelta(hours=5))).replace(tzinfo=None)
    kb = []
    for days in [5, 10, 15, 20]:
        start = (today - timedelta(days=days-1)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (start, end, f"So'nggi {days} kun")
        kb.append([InlineKeyboardButton(text=f"📅 So'nggi {days} kun", callback_data=f"sotuv_{unique_id}")])
    kb.append([InlineKeyboardButton(text="✏️ O'zim sana kiriting", callback_data="sotuv_custom")])
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stat_back")])
    await callback.message.edit_text(
        "📊 <b>SOTUV TAHLILI</b>\n\nQaysi davr uchun ko'rmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("sotuv_"), ~F.data.in_({"sotuv_custom"}))
async def sotuv_period_click(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data:
        await callback.answer("⚠️ Eskirgan ma'lumot.", show_alert=True)
        return
    start_date, end_date, label = data
    await callback.message.edit_text(f"⏳ <b>{label}</b> yuklanmoqda...")
    await show_sales_result(callback.message, start_date, end_date, label)

@router.callback_query(F.data == "sotuv_custom")
async def sotuv_custom_click(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    now = datetime.now()
    await callback.message.edit_text(
        "📅 <b>Boshlang'ich sanani tanlang:</b>",
        reply_markup=get_inline_calendar(now.year, now.month, "start")
    )

async def show_sales_result(message, start_date: str, end_date: str, label: str):
    asosiy, aksiya = await asyncio.to_thread(db_manager.get_sales_by_period, start_date, end_date)
    if not asosiy and not aksiya:
        await message.edit_text(f"⚠️ <b>{label}</b>\nMa'lumot topilmadi.")
        return
    asosiy_qoldiq, aksiya_qoldiq = await asyncio.to_thread(db_manager.get_stock_by_category)
    chart_buf = await asyncio.to_thread(generate_sales_table_image, asosiy, aksiya, asosiy_qoldiq, aksiya_qoldiq, label)
    kb = [[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stat_sotuv")],
          [InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]]
    if chart_buf:
        photo = BufferedInputFile(chart_buf.getvalue(), filename="sales.png")
        await message.delete()
        await bot.send_photo(chat_id=message.chat.id, photo=photo, caption=f"📊 <b>SOTUV TAHLILI</b>\n📅 <b>{label}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await message.edit_text("❌ Jadval yaratishda xatolik.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# --- CALENDAR PROCESSING ---

@router.callback_query(F.data.startswith("cal:"))
async def process_calendar_selection(callback: CallbackQuery, state: FSMContext):
    _, state_label, action, value = callback.data.split(":")
    if action == "ignore":
        await callback.answer()
        return
    elif action == "nav":
        year, month = map(int, value.split("-"))
        title = {"start": "Boshlang'ich (Sotuv)", "end": "Tugash (Sotuv)", "imp_start": "Boshlang'ich (Import)", "imp_end": "Tugash (Import)"}.get(state_label, "Sana")
        try: await callback.message.edit_text(f"📅 <b>{title} sanani tanlang:</b>", reply_markup=get_inline_calendar(year, month, state_label))
        except: pass
        await callback.answer()
    elif action == "day":
        if state_label == "start":
            await state.update_data(start_date=value)
            dt = datetime.strptime(value, "%Y-%m-%d")
            await callback.message.edit_text(f"📅 Boshlang'ich sana: <b>{value}</b>\n\n📅 <b>Tugash sanasini tanlang:</b>", reply_markup=get_inline_calendar(dt.year, dt.month, "end"))
        elif state_label == "end":
            data = await state.get_data()
            start_str = data.get("start_date")
            if not start_str: return
            start_dt, end_dt = datetime.strptime(start_str, "%Y-%m-%d"), datetime.strptime(value, "%Y-%m-%d")
            if end_dt < start_dt: await callback.answer("❌ Tugash sanasi noto'g'ri!", show_alert=True); return
            await state.clear(); label = f"{start_str} — {value}"
            await callback.message.edit_text(f"⏳ <b>{label}</b> yuklanmoqda...")
            await show_sales_result(callback.message, start_str, value, label)
        elif state_label == "imp_start":
            await state.update_data(imp_start_date=value)
            dt = datetime.strptime(value, "%Y-%m-%d")
            await callback.message.edit_text(f"📥 Boshlang'ich: <b>{value}</b>\n\n📅 <b>Tugash sanasini tanlang:</b>", reply_markup=get_inline_calendar(dt.year, dt.month, "imp_end"))
        elif state_label == "imp_end":
            data = await state.get_data()
            start_str = data.get("imp_start_date")
            if not start_str: return
            start_dt, end_dt = datetime.strptime(start_str, "%Y-%m-%d"), datetime.strptime(value, "%Y-%m-%d")
            if end_dt < start_dt: await callback.answer("❌ Tugash sanasi noto'g'ri!", show_alert=True); return
            await callback.answer("⏳ Import yuklanmoqda..."); await state.clear()
            await callback.message.edit_text(f"⏳ <b>{start_str} — {value}</b> oralig'idagi importlar yuklanmoqda...")
            access_token = data_engine.get_billz_access_token()
            result, res_data = await asyncio.to_thread(import_file.sync_imports_by_dates, access_token, db_manager.engine, start_str, value)
            if result == "dax":
                text_out = await asyncio.to_thread(import_file.get_imported_summary_by_dax, db_manager.engine, start_str, value)
                await callback.message.edit_text(text_out, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]]))
            else: await callback.message.edit_text(f"⚠️ Import topilmadi.")

# --- IMPORT ANALYSIS ---

@router.message(F.text == "📅 Import Tahlili")
async def import_analysis_start(message: types.Message):
    settings = db_manager.get_all_settings()
    kb = [
        [InlineKeyboardButton(text="🧥 Ust kiyimlar", callback_data="impMix_Tops"), InlineKeyboardButton(text="👖 Shim/Yubka", callback_data="impMix_Bottoms")],
        [InlineKeyboardButton(text="👟 Oyoq kiyim", callback_data="impMix_Shoes"), InlineKeyboardButton(text="👶 Chaqaloqlar", callback_data="impMix_Newborn")],
        [InlineKeyboardButton(text="🧢 Boshqalar", callback_data="impMix_Others")]
    ]
    rule_labels = {4: "🔥 4-Qoida", 3: "⚡️ 3-Qoida", 2: "⚠️ 2-Qoida", 1: "❄️ 1-Qoida"}
    for i in [4, 3, 2, 1]:
        min_d, max_d = int(settings.get(f'm{i}_min_days', 0)), int(settings.get(f'm{i}_max_days', 0))
        if max_d > 0: kb.append([InlineKeyboardButton(text=f"{rule_labels[i]}: {min_d}-{max_d} kun", callback_data=f"impRange_{min_d}-{max_d}")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])
    await message.answer("📅 <b>IMPORT TAHLILI</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("impMix_"))
async def import_mix_click(callback: CallbackQuery):
    cat_label = callback.data.split("_")[1]
    await callback.answer(f"⏳ {cat_label} tahlili...")
    # Tahlil mantiqi (hozircha rasm yoki matn)
    await callback.message.answer(f"📊 {cat_label} bo'yicha import tahlili yaqin orada qo'shiladi (mantiqiy hisob-kitoblar talab etiladi).")

@router.callback_query(F.data.startswith("impRange_"))
async def import_range_click(callback: CallbackQuery):
    d_range = callback.data.split("_")[1]
    await callback.answer(f"⏳ {d_range} kunlik import tahlili...")
    # Tahlil mantiqi
    await callback.message.answer(f"📊 {d_range} kunlik import tahlili yaqin orada qo'shiladi.")
