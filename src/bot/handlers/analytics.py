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
    group = callback.data.split("_")[1]

    groups_map = {
        "Tops": "('Верхняя одежда', 'Комплект', 'Плечевые одежды')",
        "Bottoms": "('Поясные одежды')",
        "Shoes": "('Обувь')",
        "Newborn": "('Новорождённый')",
        "Others": "('Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье')"
    }

    titles_map = {
        "Tops": "🧥 UST KIYIMLAR",
        "Bottoms": "👖 SHIMLAR VA YUBKALAR",
        "Shoes": "👟 OYOQ KIYIMLAR",
        "Newborn": "👶 CHAQALOQLAR UCHUN",
        "Others": "🧢 AKSESSUAR VA BOSHQA"
    }

    target_cats = groups_map.get(group)
    title = titles_map.get(group)

    if not target_cats:
        return

    settings = db_manager.get_all_settings()
    min_day = int(settings.get('m4_min_days', 1))
    max_day = int(settings.get('m2_max_days', 15))

    await callback.message.delete()
    msg = await callback.message.answer(f"⏳ <b>{title}</b>\nMa'lumotlar yuklanmoqda ({min_day}-{max_day} kunlik)...")

    query = text(f"""
    SELECT * FROM generated_orders
    WHERE days_passed >= :min_day AND days_passed <= :max_day
    AND category IN {target_cats}
    ORDER BY supplier ASC, subcategory ASC, artikul ASC
    """)

    try:
        all_orders = pd.read_sql(query, db_manager.engine, params={"min_day": min_day, "max_day": max_day})       
    except Exception as e:
        await msg.edit_text(f"❌ Xatolik: {e}")
        return

    if all_orders.empty:
        await msg.edit_text(f"✅ Hozircha <b>{title}</b> yo'nalishida {min_day}-{max_day} kunlik zakazlar topilmadi.")
        return

    unique_artikuls = all_orders['artikul'].unique()

    batch_id = str(uuid.uuid4())[:8]
    STAT_CACHE[batch_id] = {
        'full_df': all_orders,
        'artikuls': unique_artikuls,
        'offset': 0,
        'batch_size': 10
    }

    await send_mix_batch(callback.message.chat.id, batch_id)

@router.callback_query(F.data.startswith("impRange_"))
async def imp_range_click(callback: CallbackQuery):
    mn, mx = map(int, callback.data.split("_")[1].split("-"))

    cats = db_manager.get_stats_by_import_days(mn, mx)

    if not cats:
        await callback.answer("⚠️ Bu muddatda zakazlar yo'q", show_alert=True)
        return

    kb = []
    for cat in cats:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (mn, mx, cat)
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"impCat_{unique_id}")])

    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="impBack_root")])

    await callback.message.edit_text(
        f"📅 <b>{mn}-{mx} kunlik tovarlar</b>\nKategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("impCat_"))
async def imp_cat_click(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data: return

    mn, mx, cat = data
    subs = db_manager.get_stats_by_import_days(mn, mx, category=cat)

    kb = []
    for sub in subs:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (mn, mx, cat, sub)
        kb.append([InlineKeyboardButton(text=f"🔹 {sub}", callback_data=f"impSub_{unique_id}")])

    kb.append([InlineKeyboardButton(text="⬅️ Boshiga", callback_data="impBack_root")])

    await callback.message.edit_text(
        f"📂 <b>{cat}</b> ({mn}-{mx} kun)\nPodkategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("impSub_"))
async def imp_sub_click(callback: CallbackQuery):
    uid  = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data:
        return

    mn, mx, cat, sub = data

    def _get_orders():
        return pd.read_sql(
            text("SELECT * FROM generated_orders WHERE category = :cat AND subcategory = :sub"),
            db_manager.engine, params={"cat": cat, "sub": sub}
        )

    all_orders = await asyncio.to_thread(_get_orders)

    if all_orders.empty:
        await callback.answer("⚠️ Ma'lumot topilmadi.", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(f"⏳ <b>{cat} > {sub}</b>\nMa'lumotlar yuklanmoqda...")

    now = datetime.now()
    all_orders['created_at_dt'] = pd.to_datetime(all_orders['created_at'])

    is_topdim = all_orders['status'] == 'Topdim'
    is_new    = all_orders['status'] == 'Kutilmoqda'
    is_late   = (now - all_orders['created_at_dt']).dt.days >= 3

    red_df    = all_orders[is_topdim & is_late].copy()
    yellow_df = all_orders[is_topdim & ~is_late].copy()
    white_df  = all_orders[is_new].copy()

    if not red_df.empty:
        await message_sender(callback.message, red_df,    "🚨 <b>DIQQAT! KECHIKKANLAR (3+ kun):</b>", "red")      
    if not white_df.empty:
        await message_sender(callback.message, white_df,  "🔥 <b>YANGI EHTIYOJLAR:</b>",              "white", pending_df=yellow_df)
    if not yellow_df.empty:
        await message_sender(callback.message, yellow_df, "⏳ <b>JARAYONDA (Yo'lda):</b>",            "yellow")    

    kb = [[InlineKeyboardButton(text="🔄 Boshqa bo'lim", callback_data="impBack_root")]]
    await bot.send_message(callback.message.chat.id, "✅ Ro'yxat tugadi.",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

async def message_sender(message, df, title, color_type, pending_df=None):
    await bot.send_message(message.chat.id, title)

    for article, group in df.groupby('artikul'):
        first   = group.iloc[0]
        caption = build_caption(article, group, first, color_type, pending_df)

        kb = []
        if color_type == 'white':
            kb.append([
                InlineKeyboardButton(text="✅ Topdim",    callback_data=f"feedback:Topdim:{article}"),
                InlineKeyboardButton(text="❌ Topilmadi", callback_data=f"feedback:Topilmadi:{article}")
            ])
        else:
            kb.append([
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_order:{article}")
            ])

        photo = str(first.get('photo', ''))
        try:
            if photo.startswith('http'):
                await bot.send_photo(message.chat.id, photo, caption=caption,
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            else:
                await bot.send_message(message.chat.id, caption,
                                       reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        except Exception:
            await bot.send_message(message.chat.id, caption,
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await asyncio.sleep(0.2)

@router.callback_query(F.data == "impBack_root")
async def imp_back_root(callback: CallbackQuery):
    await import_analysis_start(callback.message)

async def send_mix_batch(chat_id, batch_id):
    data = STAT_CACHE.get(batch_id)
    if not data:
        await bot.send_message(chat_id, "⚠️ Ma'lumot eskirgan. Iltimos, bo'limga qaytadan kiring.")
        return

    full_df = data['full_df']
    all_artikuls = data['artikuls']
    offset = data['offset']
    limit = data['batch_size']

    current_artikuls = all_artikuls[offset : offset + limit]

    if len(current_artikuls) == 0:
        await bot.send_message(chat_id, "✅ Ro'yxat to'liq tugadi.")
        return

    await bot.send_message(chat_id, f"🚀 <b>YUKLANMOQDA...</b>\n{offset+1} dan {offset+len(current_artikuls)} gacha (Jami: {len(all_artikuls)})")

    batch_df = full_df[full_df['artikul'].isin(current_artikuls)].copy()

    now = datetime.now()
    batch_df['created_at_dt'] = pd.to_datetime(batch_df['created_at'])

    is_topdim = batch_df['status'] == 'Topdim'
    is_late = (now - batch_df['created_at_dt']).dt.days >= 3

    batch_df = batch_df.sort_values(by=['supplier', 'artikul'])

    red_df = batch_df[is_topdim & is_late]
    yellow_df = batch_df[is_topdim & ~is_late]
    white_df = batch_df[batch_df['status'] == 'Kutilmoqda']

    class DummyMsg:
        def __init__(self, cid): self.chat = type('obj', (object,), {'id': cid})

    dummy_msg = DummyMsg(chat_id)

    if not red_df.empty:
        await message_sender(dummy_msg, red_df, "🚨 <b>DIQQAT! KECHIKKANLAR:</b>", "red")

    if not white_df.empty:
        full_yellow = full_df[(full_df['status']=='Topdim') & ~(full_df['artikul'].isin(current_artikuls))]       
        await message_sender(dummy_msg, white_df, "🔥 <b>YANGI ZAKAZLAR:</b>", "white", pending_df=full_yellow)   

    if not yellow_df.empty:
        await message_sender(dummy_msg, yellow_df, "⏳ <b>JARAYONDA (Yo'lda):</b>", "yellow")

    data['offset'] += limit

    if data['offset'] < len(all_artikuls):
        remains = len(all_artikuls) - data['offset']
        kb = [
            [InlineKeyboardButton(text=f"▶️ DAVOM ETISH (Yana {remains} ta)", callback_data=f"nextMix_{batch_id}")],
            [InlineKeyboardButton(text="⏹ TO'XTATISH", callback_data="del_msg")]
        ]
        await bot.send_message(chat_id, "👇 Keyingi partiyani yuklaymizmi?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        kb = [[InlineKeyboardButton(text="🔄 Menyuga qaytish", callback_data="impBack_root")]]
        await bot.send_message(chat_id, "✅ <b>BARCHASI YUBORILDI.</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("nextMix_"))
async def next_mix_batch_handler(callback: CallbackQuery):
    batch_id = callback.data.split("_")[1]
    try:
        await callback.message.delete()
    except:
        pass
    await send_mix_batch(callback.message.chat.id, batch_id)
