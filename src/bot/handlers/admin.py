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
import src.database.db_manager as db_manager
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

@router.callback_query(F.data.startswith("obrBackRoot_"))
async def obr_back_root(callback: CallbackQuery):
    session_id = callback.data.split("_")[1]
    df = OBR_CACHE.get(session_id)
    if df is None:
        await callback.answer("⏳ Ma'lumot eskirgan, qaytadan hisoblang.", show_alert=True)
        return
    
    cats = sorted(df['Категория'].unique().tolist())
    kb = []
    for c in cats:
        if not c: continue
        cat_id = str(uuid.uuid4())[:8]
        OBR_CACHE[f"cat_{cat_id}"] = c
        kb.append([InlineKeyboardButton(text=f"📁 {c}", callback_data=f"obrCat_{session_id}_{cat_id}")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])

    text = "📊 <b>ASOSIY ZAKAZ (OBR)</b>\n\nQaysi kategoriyani ko'rmoqchisiz?"
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    try:
        if callback.message.photo:
            await callback.message.delete()
            await bot.send_message(callback.message.chat.id, text, reply_markup=markup)
        else:
            await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        await bot.send_message(callback.message.chat.id, text, reply_markup=markup)

@router.callback_query(F.data.startswith("obrCat_"))
async def obr_category_click(callback: CallbackQuery):
    _, session_id, cat_id = callback.data.split("_")
    df = OBR_CACHE.get(session_id)
    category = OBR_CACHE.get(f"cat_{cat_id}")

    if df is None or category is None:
        await callback.answer("⏳ Ma'lumot eskirgan, qaytadan hisoblang.", show_alert=True)
        return

    cat_df = df[df['Категория'] == category]
    subs = sorted(cat_df['Подкатегория'].unique().tolist())

    kb = []
    for s in subs:
        if not s: continue
        sub_id = str(uuid.uuid4())[:8]
        OBR_CACHE[f"sub_{sub_id}"] = s
        kb.append([InlineKeyboardButton(text=f"🔹 {s}", callback_data=f"obrSub_{session_id}_{cat_id}_{sub_id}")])

    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"obrBackRoot_{session_id}")]) 

    text = f"📂 <b>{category}</b>\n\nIchki turlarni (podkategoriya) tanlang:"
    markup = InlineKeyboardMarkup(inline_keyboard=kb)

    try:
        if callback.message.photo:
            await callback.message.delete()
            await bot.send_message(callback.message.chat.id, text, reply_markup=markup)
        else:
            await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        await bot.send_message(callback.message.chat.id, text, reply_markup=markup)

@router.callback_query(F.data.startswith("obrSub_"))
async def obr_subcategory_click(callback: CallbackQuery):
    parts = callback.data.split("_")
    session_id = parts[1]
    cat_id = parts[2]
    sub_id = parts[3]

    df = OBR_CACHE.get(session_id)
    sub_name = OBR_CACHE.get(f"sub_{sub_id}")

    if df is None or sub_name is None:
        await callback.answer("⏳ Eskirgan.", show_alert=True)
        return

    await callback.answer(f"📊 {sub_name} tahlili...")

    img_buf = await asyncio.to_thread(generate_macro_image, df, sub_name)

    sub_df = df[df['Подкатегория'] == sub_name]
    segments = sorted(sub_df['Real_Sotuv_Segmenti'].unique().tolist())

    kb = []
    for seg in segments:
        if not seg: continue
        seg_id = str(uuid.uuid4())[:8]
        OBR_CACHE[f"seg_{seg_id}"] = seg
        kb.append([InlineKeyboardButton(
            text=f"🔹 {seg.split('(')[0].strip()}",
            callback_data=f"obrSegMenu_{session_id}_{cat_id}_{sub_id}_{seg_id}"
        )])

    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"obrCat_{session_id}_{cat_id}")])

    if img_buf:
        try:
            await callback.message.delete()
        except:
            pass
        photo = BufferedInputFile(img_buf.getvalue(), filename="obr.png")
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=photo,
            caption=f"📊 <b>OBR TAHLIL: {sub_name}</b>\n\nQaysi segmentni ko'rmoqchisiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
    else:
        await callback.message.edit_text(
            f"❌ {sub_name} uchun grafik yaratishda xatolik.\nQaysi segmentni ko'rmoqchisiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

@router.callback_query(F.data.startswith("obrSegMenu_"))
async def obr_seg_menu_click(callback: CallbackQuery):
    parts = callback.data.split("_")
    _, session_id, cat_id, sub_id, seg_id = parts
    seg_name = OBR_CACHE.get(f"seg_{seg_id}")
    sub_name = OBR_CACHE.get(f"sub_{sub_id}")

    if not seg_name or not sub_name:
        await callback.answer("⏳ Ma'lumot eskirgan.", show_alert=True)
        return

    kb = [
        [InlineKeyboardButton(text="🛒 ZAKAZ KERAK", callback_data=f"obrSegDet_{session_id}_{cat_id}_{sub_id}_{seg_id}_zakaz")],
        [InlineKeyboardButton(text="👁 KUZATUVDA", callback_data=f"obrSegDet_{session_id}_{cat_id}_{sub_id}_{seg_id}_kuzat")],
        [InlineKeyboardButton(text="📋 HAMMASI", callback_data=f"obrSegDet_{session_id}_{cat_id}_{sub_id}_{seg_id}_all")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"obrSub_{session_id}_{cat_id}_{sub_id}")],
    ]

    text = f"📦 <b>{sub_name}</b>\n🔹 <b>{seg_name}</b>\n\nQaysi bo'limni ko'rmoqchisiz?"

    try:
        if callback.message.photo:
            await callback.message.delete()
            await bot.send_message(callback.message.chat.id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        else:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except Exception:
        await bot.send_message(callback.message.chat.id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("obrSegDet_"))
async def obr_seg_detail_click(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    _, session_id, cat_id, sub_id, seg_id, mode = parts 
    df       = OBR_CACHE.get(session_id)
    sub_name = OBR_CACHE.get(f"sub_{sub_id}")
    seg_name = OBR_CACHE.get(f"seg_{seg_id}")

    if df is None or not sub_name or not seg_name:
        await callback.message.answer("⏳ Ma'lumot eskirgan.")
        return
        return

    seg_df = df[
        (df['Подкатегория'] == sub_name) &
        (df['Real_Sotuv_Segmenti'] == seg_name)
    ].copy()

    if mode == "zakaz":
        seg_df = seg_df[seg_df['Zakaz'] > 0]
    elif mode == "kuzat":
        seg_df = seg_df[seg_df['Zakaz'] == 0]
        seg_df = seg_df[~((seg_df['Hozirgi_Qoldiq'] >= 5) & (seg_df['Продано'] < 5))]
    elif mode == "all":
        seg_df = seg_df[~((seg_df['Hozirgi_Qoldiq'] >= 5) & (seg_df['Продано'] < 5))]
        
    if seg_df.empty:
        await callback.answer("⚠️ Bu bo'limda ma'lumot yo'q.", show_alert=True)
        return

    def razmer_sort_key(r):
        r = str(r).strip()
        if '-' in r:
            try: return int(r.split('-')[0])
            except: pass
        try: return int(r)
        except: return 9999

    seg_df['_razmer_sort'] = seg_df['Размер сетка'].apply(razmer_sort_key)

    if 'Пол' in seg_df.columns:
        seg_df['_jins'] = seg_df['Пол'].fillna('').astype(str).str.strip()
    elif 'Вид2' in seg_df.columns:
        seg_df['_jins'] = seg_df['Вид2'].fillna('').astype(str).str.strip()
    else:
        seg_df['_jins'] = 'Универсал'

    seg_df['_jins'] = seg_df['_jins'].replace('', 'Универсал')

    JINS_NORMALIZE = {
        'Девочек': 'Девочки',
        'Мальчик': 'Мальчики',
    }
    seg_df['_jins'] = seg_df['_jins'].apply(lambda x: JINS_NORMALIZE.get(x, x))

    JINS_ORDER = ['Девочки', 'Мальчики', 'Универсал']
    JINS_ICONS = {
        'Девочки': '👧',
        'Мальчики': '👦',
        'Универсал': '🌐'
    }

    def jins_sort_key(v):
        try: return JINS_ORDER.index(str(v).strip())
        except: return len(JINS_ORDER)

    seg_df['_jins_sort'] = seg_df['_jins'].apply(jins_sort_key)
    seg_df = seg_df.sort_values(['_jins_sort', '_razmer_sort']).reset_index(drop=True)

    try:
        await callback.message.delete()
    except:
        pass

    jinslar_sorted = sorted(seg_df['_jins'].unique(), key=jins_sort_key)

    text_blocks = []
    header = f"📦 <b>{sub_name}</b>\n\n"
    current_text = header

    for jins in jinslar_sorted:
        jins_df = seg_df[seg_df['_jins'] == jins]
        icon = JINS_ICONS.get(jins, '👤')

        for _, row in jins_df.iterrows():
            razmer = str(row.get('Размер сетка', '')) or "Noma'lum"
            mat    = str(row.get('Материал2', '')) or "—"
            vid    = str(row.get('Вид2', '')) or "—"
            nom    = str(row.get('Наименование', '')) or "—"
            zakaz  = row.get('Zakaz', 0)
            qoldiq = row.get('Hozirgi_Qoldiq', 0)
            sotuv  = row.get('Продано', 0)
            obr    = row.get('OBR %', '0%')

            item_text = (
                f" {icon} {jins}\n\n"
                f" 📌 <b><i>{nom}</i></b>\n"
                f"{seg_name}|📐 <b>{razmer} yosh </b>|  {mat}  | 🎨 {vid} |\n"
                f"  🛒 <b>ZAKAZ: {zakaz} ta</b>\n\n"
                f"  | Sotuv: <b>{sotuv}</b> | Qoldiq: <b>{qoldiq}</b> | OBR: <b>{obr}</b> |\n"
                "  ──────────────────────\n"
            )

            if len(current_text) + len(item_text) > 4000:
                text_blocks.append(current_text)
                current_text = item_text
            else:
                current_text += item_text

        current_text += "\n"

    if current_text.strip():
        text_blocks.append(current_text)

    kb = [[InlineKeyboardButton(
        text="⬅️ Orqaga",
        callback_data=f"obrSegMenu_{session_id}_{cat_id}_{sub_id}_{seg_id}"
    )]]

    for i, t_block in enumerate(text_blocks):
        if i == len(text_blocks) - 1:
            await bot.send_message(callback.message.chat.id, t_block, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        else:
            await bot.send_message(callback.message.chat.id, t_block)

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

@router.callback_query(F.data.startswith("stqDate_"))
async def stock_date_click(callback: CallbackQuery):
    target_date = callback.data.split("stqDate_", 1)[1]
    categories = db_manager.get_stock_categories_on_date(target_date)

    dt_obj = datetime.strptime(target_date, "%Y-%m-%d")
    pretty_date = dt_obj.strftime("%d.%m.%Y")

    if not categories:
        await callback.answer(f"⚠️ {pretty_date} sanasi uchun ma'lumot yo'q.", show_alert=True)
        return

    kb = []
    for cat in categories:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (cat, target_date)
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"stqCat_{unique_id}")])

    kb.append([InlineKeyboardButton(text=f"📥 {pretty_date} bo'yicha Excel", callback_data=f"downStockEx_{target_date}")])
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_stock_dates")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])

    await callback.message.edit_text(
        f"📦 <b>QOLDIQLAR TAHLILI</b>\n"
        f"📅 Tanlangan sana: <b>{pretty_date}</b>\n\n"
        f"Hisobotni ko'rish uchun kategoriyani tanlang yoki Excel yuklab oling:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data == "back_to_stock_dates")
async def back_to_stock_dates(callback: CallbackQuery):
    dates = db_manager.get_last_7_stock_dates()
    kb = []
    for d in dates:
        dt_obj = datetime.strptime(d, "%Y-%m-%d")
        pretty_date = dt_obj.strftime("%d.%m.%Y")
        kb.append([InlineKeyboardButton(text=f"📅 {pretty_date}", callback_data=f"stqDate_{d}")])

    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])

    await callback.message.edit_text(
        f"📦 <b>QOLDIQLAR TAHLILI</b>\n\n"
        f"Hisobotni ko'rish uchun oxirgi 7 kunlikdan sanani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("stqCat_"))
async def stock_category_click(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)

    if not data:
        await callback.answer("⚠️ Ma'lumot eskirgan, qaytadan bosing.", show_alert=True)
        return

    category, target_date = data
    dt_obj = datetime.strptime(target_date, "%Y-%m-%d")
    pretty_date = dt_obj.strftime("%d.%m.%Y")

    asosiy_summary, aksiya_summary = db_manager.get_stock_subcategories_summary_v2(category, target_date)

    text = f"📊 <b>{category} (Qoldiqlar)</b>\n"
    text += f"📅 Sana: <b>{pretty_date}</b>\n\n"

    text += "🏢 <b>ASOSIY TOVARLAR (010/011 bo'lmagan):</b>\n"
    total_asosiy = 0
    if asosiy_summary:
        for sub, gender, qty in asosiy_summary:
            text += f" 🔹 {sub} ({gender}): <b>{int(qty)} dona</b>\n"
            total_asosiy += qty
        text += f" 📦 <b>Jami Asosiy: {int(total_asosiy)} dona</b>\n\n"
    else:
        text += " <i>Ma'lumot yo'q</i>\n\n"

    text += "━━━━━━━━━━━━━━\n\n"

    text += "🎁 <b>AKSIYA TOVARLARI (010/011 Artikullar):</b>\n"
    total_aksiya = 0
    if aksiya_summary:
        for sub, gender, qty in aksiya_summary:
            text += f" 🔸 {sub} ({gender}): <b>{int(qty)} dona</b>\n"
            total_aksiya += qty
        text += f" 📦 <b>Jami Aksiya: {int(total_aksiya)} dona</b>\n\n"
    else:
        text += " <i>Ma'lumot yo'q</i>\n\n"

    text += "━━━━━━━━━━━━━━\n"
    text += f"🚛 <b>UMUMIY JAMI QOLDIQ: {int(total_asosiy + total_aksiya)} dona</b>"

    kb = [
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"stqDate_{target_date}")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("downStockEx_"))
async def download_stock_excel_handler(callback: CallbackQuery):
    target_date = callback.data.split("_")[1]

    msg = await callback.message.answer("⏳ Excel fayl tayyorlanmoqda, kuting...")

    df_asosiy, df_aksiya, _ = await asyncio.to_thread(db_manager.get_all_stock_summary_for_excel, target_date)    

    if df_asosiy.empty and df_aksiya.empty:
        await msg.edit_text("⚠️ Ma'lumot topilmadi.")
        return

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if not df_asosiy.empty:
            df_asosiy.to_excel(writer, index=False, sheet_name='Asosiy (Aksiyasiz)')
            worksheet = writer.sheets['Asosiy (Aksiyasiz)']
            for i, col in enumerate(df_asosiy.columns):
                width = max(df_asosiy[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, width)

        if not df_aksiya.empty:
            df_aksiya.to_excel(writer, index=False, sheet_name='Aksiya (010)')
            worksheet = writer.sheets['Aksiya (010)']
            for i, col in enumerate(df_aksiya.columns):
                width = max(df_aksiya[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, width)

    output.seek(0)

    dt_obj = datetime.strptime(target_date, "%Y-%m-%d")
    pretty_date = dt_obj.strftime("%d.%m.%Y")

    file = BufferedInputFile(output.getvalue(), filename=f"Qoldiqlar_{pretty_date}.xlsx")
    await callback.message.answer_document(file, caption=f"📦 <b>Qoldiqlar hisoboti</b>\n📅 Sana: {pretty_date}") 
    await msg.delete()
    await callback.answer()
