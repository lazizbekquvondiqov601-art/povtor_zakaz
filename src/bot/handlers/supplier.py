import uuid
import asyncio
import logging
import pandas as pd
from datetime import datetime
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.fsm.context import FSMContext

import config
import src.database.db_manager as db_manager
from src.bot.init_bot import bot, OBR_CACHE, STAT_CACHE
from src.bot.keyboards.supplier import get_supplier_keyboard
from src.bot.states.bot_states import Registration
from src.utils.helpers import format_money, is_dona_category

logger = logging.getLogger(__name__)
router = Router()

async def get_orders_for_supplier(supplier_name: str) -> pd.DataFrame:
    cleaned_name = supplier_name.replace('\u00A0', ' ').strip()
    def _read_db():
        try:
            query = "SELECT * FROM generated_orders WHERE supplier = :name"
            df = pd.read_sql(query, db_manager.engine, params={"name": cleaned_name})
            return df
        except Exception as e:
            logger.error(f"❌ Bazadan o'qishda xatolik: {e}")
            return pd.DataFrame()
    df = await asyncio.to_thread(_read_db)
    return df

from src.bot.keyboards.admin import get_admin_keyboard

@router.message(F.text == "🔑 Admin Bo'lish")
async def become_admin_handler(message: Message):
    user_id = message.from_user.id
    success = db_manager.add_admin_db(user_id)
    if success:
        await message.answer(
            "🎉 <b>Tabriklaymiz! Siz muvaffaqiyatli ADMIN qilib tayyinlandingiz.</b>\n\n"
            "Endi siz hisobotlar, statistika, qoldiqlar va kelgan tovarlar tahlilini ko'ra olasiz.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            "⚠️ Siz allaqachon adminlar ro'yxatida mavjudsiz. Menyuni tanlang:",
            reply_markup=get_admin_keyboard()
        )

@router.message(F.text == "📝 Ismni o'zgartirish")
async def change_name_text(message: Message, state: FSMContext):
    categories = db_manager.get_unassigned_categories()
    if not categories:
        await message.answer("⚠️ Hozircha bo'sh yetkazib beruvchilar yoki zakazlar yo'q.")
        return
    kb_builder = []
    for cat in categories:
        kb_builder.append([InlineKeyboardButton(text=cat, callback_data=f"regCat_{cat}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_builder)
    await message.answer("📂 Iltimos, faoliyatingiz turini (Kategoriya) tanlang:", reply_markup=keyboard)
    await state.set_state(Registration.filter_category)

@router.message(F.text == "📈 Statistika")
async def show_statistics(message: Message):
    user_id = message.from_user.id
    # We don't check for IsAdmin here because this handler is in supplier.py, 
    # but since both can trigger it, we'll implement the supplier logic. 
    # If they are an admin, the admin.py handler will catch it first.
    
    supplier = db_manager.get_supplier_by_id(user_id)
    current_name = supplier.name if supplier else "Noma'lum"
    data = db_manager.get_supplier_stats_detailed(user_id)

    if not data:
        await message.answer(f"👤 Ism: <b>{current_name}</b>\n✅ Hozircha sizda bajarilmagan zakazlar yo'q.")
        return

    report = {}
    total_packs = 0
    for cat, sub, qty in data:
        if cat not in report:
            report[cat] = []
        report[cat].append(f"▫️ {sub}: <b>{int(qty)} pochka</b>")
        total_packs += qty

    text = f"📊 <b>SIZNING ZAKAZLARINGIZ:</b>\n"
    text += f"👤 Ism: <b>{current_name}</b>\n\n"
    for category, lines in report.items():
        text += f"📂 <b>{category}</b>\n"
        text += "\n".join(lines) + "\n\n"
    text += f"━━━━━━━━━━━━━━\n🚛 <b>JAMI: {int(total_packs)} POCHKA</b>"
    
    await message.answer(text)

@router.message(F.text == "🔄 Supplier Menyu")
async def switch_to_supplier_handler(message: Message):
    user_id = message.from_user.id
    logger.info(f"User {user_id} switching to supplier menu")
    supplier = db_manager.get_supplier_by_id(user_id)
    
    if supplier:
        await message.answer(
            "📦 <b>Yetkazib beruvchi (Supplier) menyusiga o'tdingiz.</b>",
            reply_markup=get_supplier_keyboard()
        )
    else:
        await message.answer("⚠️ Siz yetkazib beruvchi (supplier) sifatida ro'yxatdan o'tmagansiz!")

@router.message(F.text == "📦 Zakazlarim (Yangi)")
async def my_orders_handler(message: Message):
    user_id = message.from_user.id
    logger.info(f"Supplier {user_id} checking new orders")
    supplier = db_manager.get_supplier_by_id(user_id)
    if not supplier:
        await message.answer("❌ Tizimga kirmagansiz. /start")
        return

    msg = await message.answer("⏳ Yuklanmoqda...")
    orders_df = await get_orders_for_supplier(supplier.name)

    if orders_df.empty:
        await msg.edit_text("✅ Zakazlar yo'q.")
        return

    new_orders = orders_df[orders_df['status'] == 'Kutilmoqda'].copy()
    pending_orders = orders_df[orders_df['status'] == 'Topdim'].copy()
    
    red_orders = pd.DataFrame()
    if not pending_orders.empty:
        pending_orders['created_at_dt'] = pd.to_datetime(pending_orders['created_at'])
        now = datetime.now()
        mask_red = (now - pending_orders['created_at_dt']).dt.days >= 3
        red_orders = pending_orders[mask_red].copy()

    await msg.delete()

    if new_orders.empty and red_orders.empty:
        await message.answer("✅ Yangi yoki Muammoli zakazlar yo'q.\n'⏳ Jarayonda' tugmasini tekshiring.")
        return

    # --- QIZIL (KECHIKKANLAR) ---
    if not red_orders.empty:
        await message.answer(f"🚨 <b>DIQQAT! KELMAGAN TOVARLAR:</b>\n<i>3 kundan oshdi!</i>")
        for article, group in red_orders.groupby('artikul'):
            first = group.iloc[0]
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Qayta Olish", callback_data=f"feedback:Topdim:{article}"),
                 InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_order:{article}")]
            ])
            caption = build_caption_helper(article, group, first, "red")
            await bot.send_message(message.chat.id, caption, reply_markup=kb)
            await asyncio.sleep(0.2)

    # --- OQ (YANGI) ---
    if not new_orders.empty:
        await message.answer(f"🔥 <b>YANGI ZAKAZLAR:</b>")
        for article, group in new_orders.groupby('artikul'):
            first = group.iloc[0]
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Topdim", callback_data=f"feedback:Topdim:{article}"),
                 InlineKeyboardButton(text="❌ Topilmadi", callback_data=f"feedback:Topilmadi:{article}")]
            ])
            caption = build_caption_helper(article, group, first, "white", pending_orders)
            photo = str(first.get('photo', ''))
            try:
                if photo.startswith('http'):
                    await bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=kb)
                else:
                    await bot.send_message(message.chat.id, caption, reply_markup=kb)
            except Exception as e:
                logger.error(f"Error sending photo for {article}: {e}")
                await bot.send_message(message.chat.id, caption, reply_markup=kb)
            await asyncio.sleep(0.3)

@router.message(F.text == "⏳ Jarayonda")
async def pending_orders_text(message: types.Message):
    def _get_cats():
        return pd.read_sql(
            "SELECT DISTINCT category FROM generated_orders WHERE status = 'Topdim' ORDER BY category",
            db_manager.engine
        )

    cats_df = await asyncio.to_thread(_get_cats)

    if cats_df.empty:
        await message.answer("✅ Jarayonda (Yo'lda) hech qanday zakaz yo'q.")
        return

    kb = []
    for cat in cats_df['category']:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = cat
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"pendCat_{unique_id}")])
    
    # 🟢 Billz uchun Excel tugmasini qo'shamiz
    kb.append([InlineKeyboardButton(text="📥 Billz uchun Excel (Sklad)", callback_data="download_sklad_excel")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])

    await message.answer(
        "⏳ <b>JARAYONDA (YO'LDA)</b>\nQaysi bo'limni ko'rmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data == "download_sklad_excel")
async def download_sklad_excel_handler(callback: CallbackQuery):
    await callback.message.answer("⏳ <b>Sklad uchun Excel fayl shakllantirilmoqda...</b>\nBiroz kuting.")
    
    excel_buf = await asyncio.to_thread(db_manager.generate_sklad_excel)

    if not excel_buf:
        await callback.message.answer("⚠️ Hozircha 'Jarayonda' turgan (Topdim) tovarlar yo'q.")
        await callback.answer()
        return

    today_str = datetime.now().strftime("%d.%m.%Y")
    file = BufferedInputFile(excel_buf.getvalue(), filename=f"Billz_Import_{today_str}.xlsx")

    caption_text = (
        "📥 <b>Sklad uchun import fayli tayyor!</b>\n\n"
        "👉 <i>Bu faylda 'Jarayonda'gi barcha tovarlar joylangan.</i>\n"
        "👉 <i>Barcode va Kol-vo ustunlari bo'sh qoldirildi.</i>\n\n"
        "👨‍💻 Skladchi mollar kelganda sanab, faqat eng oxirgi <b>'Кол-во'</b> ustuniga sonini yozadi va to'g'ridan-to'g'ri Billz ga yuklaydi."
    )

    await callback.message.answer_document(file, caption=caption_text)
    await callback.answer()

@router.callback_query(F.data.startswith("pendCat_"))
async def pending_category_click(callback: CallbackQuery):
    uid      = callback.data.split("_")[1]
    category = STAT_CACHE.get(uid)

    if not category:
        await callback.answer("⚠️ Eskirgan ma'lumot.", show_alert=True)
        return

    def _get_subs():
        return pd.read_sql(
            """SELECT DISTINCT subcategory FROM generated_orders
               WHERE status = 'Topdim' AND category = :cat ORDER BY subcategory""",
            db_manager.engine, params={"cat": category}
        )

    subs_df = await asyncio.to_thread(_get_subs)

    kb = []
    for sub in subs_df['subcategory']:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (category, sub)
        kb.append([InlineKeyboardButton(text=f"🔹 {sub}", callback_data=f"pendSub_{unique_id}")])
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_pend_cats")])

    await callback.message.edit_text(
        f"📂 <b>{category}</b> (Jarayonda)\nPodkategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data == "back_to_pend_cats")
async def back_pend_cats(callback: CallbackQuery):
    await callback.message.delete()
    await pending_orders_text(callback.message)

@router.callback_query(F.data.startswith("pendSub_"))
async def pending_subcategory_click(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data: return

    category, subcategory = data

    query = """
    SELECT * FROM generated_orders
    WHERE status = 'Topdim' AND category = :cat AND subcategory = :sub
    """
    orders_df = pd.read_sql(query, db_manager.engine, params={"cat": category, "sub": subcategory})

    if orders_df.empty:
        await callback.answer("✅ Bu bo'lim tozalandi (Hamma yuk kelgan).", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(f"⏳ <b>{subcategory}</b>\nYuklanmoqda...")

    orders_df['created_at_dt'] = pd.to_datetime(orders_df['created_at'])
    now = datetime.now()
    mask_red = (now - orders_df['created_at_dt']).dt.days >= 3

    red_orders = orders_df[mask_red].copy()
    yellow_orders = orders_df[~mask_red].copy()

    if not red_orders.empty:
        await show_pending_group(callback.message, red_orders, "🚨 <b>DIQQAT! KECHIKKANLAR (3+ kun):</b>", "red") 

    if not yellow_orders.empty:
        await show_pending_group(callback.message, yellow_orders, "⏳ <b>JARAYONDA (Yo'lda):</b>", "yellow")       

    kb = [[InlineKeyboardButton(text="🔄 Boshqa bo'lim", callback_data="back_to_pend_cats")]]
    await bot.send_message(callback.message.chat.id, "✅ Ro'yxat tugadi.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

async def show_pending_group(message, df, title, color_type):
    await bot.send_message(message.chat.id, title)

    for article, group in df.groupby('artikul'):
        first   = group.iloc[0]
        caption = build_caption_helper(article, group, first, color_type)
        kb = [[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_order:{article}")]]

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

@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order_handler(callback: CallbackQuery):
    artikul = callback.data.split(":")[1]
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ha, Bekor qilish", callback_data=f"confirm_cancel:{artikul}"),
         InlineKeyboardButton(text="Yo'q, Qaytish", callback_data="del_msg")]
    ])
    await callback.message.answer(f"⚠️ <b>{artikul}</b> ni 'Kutilmoqda' ro'yxatidan o'chirib tashlamoqchimisiz?\n(Keyingi safar yana Yangi bo'lib chiqadi)", reply_markup=confirm_kb)
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_cancel:"))
async def confirm_cancel_handler(callback: CallbackQuery):
    artikul = callback.data.split(":")[1]
    try:
        from sqlalchemy import text
        with db_manager.engine.begin() as conn:
            query = text(f"""
                UPDATE generated_orders
                SET status = 'Kutilmoqda'
                WHERE artikul = '{artikul}' AND status = 'Topdim'
            """)
            result = conn.execute(query)

        if result.rowcount > 0:
            await callback.message.edit_text(f"✅ <b>{artikul}</b> bekor qilindi.\nQaytadan 'Yangi Zakazlar'ga tushdi.")
        else:
            await callback.message.edit_text(f"⚠️ <b>{artikul}</b> o'zgarmadi. Balki allaqachon bekor qilingandir?")

    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {e}")

def build_caption_helper(article, group, first, color_type, pending_df=None):
    icon = {'white': '📦', 'yellow': '🟡', 'red': '🔴'}.get(color_type, '📦')
    subcat = str(first.get('subcategory', '-')).strip()
    unit = 'dona' if is_dona_category(first.get('category', '')) else 'pochka'

    warning = ''
    if color_type == 'white' and pending_df is not None and not pending_df.empty:
        match = pending_df[pending_df['artikul'] == article]
        if not match.empty:
            warning = f"\n⚠️ <b>Eslatma:</b> {int(match['quantity'].sum())} ta yo'lda."

    caption = f"{icon} <b>{article}</b>\n<i>{subcat}</i>{warning}\n"

    if color_type == 'white':
        price_str = format_money(first.get('supply_price', 0))
        caption += f"👤 {first.get('supplier', '-')}\n💵 {price_str} so'm\n"
    elif color_type in ('yellow', 'red'):
        _unknown = 'Noma\u02bclum'
        caption += f"({first.get('supplier', _unknown)})\n"

    for shop, s_group in group.groupby('shop'):
        caption += f"\n🏪 <b>{shop}:</b>"
        for _, row in s_group.iterrows():
            qoldiq = int(float(row.get('hozirgi_qoldiq', 0) or 0))
            sotuv  = int(float(row.get('prodano', 0) or 0))
            caption += f"\n  - {row.get('color','-')}: <b>{int(row.get('quantity',0))} {unit}</b> (Q:{qoldiq}) (S:{sotuv})"

    return caption

@router.callback_query(F.data.startswith("feedback:"))
async def feedback_handler(callback: CallbackQuery):
    _, status, artikul = callback.data.split(":")
    logger.info(f"Supplier {callback.from_user.id} gave feedback {status} for {artikul}")

    if status == 'Topdim':
        if db_manager.update_order_status(artikul, 'Topdim'):
            try:
                old_text = callback.message.html_text or ""
                new_text = f"✅ <b>QABUL QILINDI VA YO'LDA</b>\n\n{old_text}"
                if callback.message.photo: 
                    await callback.message.edit_caption(caption=new_text, reply_markup=None)
                else: 
                    await callback.message.edit_text(new_text, reply_markup=None)
            except Exception as e:
                logger.error(f"Error updating feedback message: {e}")

            # Kanalga hisobot yuborish logikasi
            try:
                details_df = db_manager.get_confirmed_order_details(artikul)
                if not details_df.empty:
                    first_row = details_df.iloc[0]
                    supplier_name = first_row['supplier']
                    photo_url = str(first_row['photo'])
                    price = first_row.get('supply_price', 0)
                    try:
                        price_str = f"{float(price):,.0f}".replace(",", " ")
                    except:
                        price_str = "0"

                    total_qty = details_df['quantity'].sum()

                    report = f"✅ <b>YUK KELYAPTI! (Tasdiqlandi)</b>\n\n"
                    report += f"📦 Artikul: <b>{artikul}</b>\n"
                    report += f"💵 Tan Narx: <b>{price_str} so'm</b>\n"
                    report += f"🚛 Yetkazuvchi: <b>{supplier_name}</b>\n"
                    report += f"👤 Tasdiqladi: <b>{callback.from_user.full_name}</b>\n"
                    report += f"🔢 Jami miqdor: <b>{int(total_qty)} pochka</b>\n"
                    report += "━━━━━━━━━━━━━━\n"
                    report += "📋 <b>TARQATISH RO'YXATI:</b>\n"

                    for shop, group in details_df.groupby('shop'):
                        report += f"\n🏪 <b>{shop}:</b>"
                        for _, row in group.iterrows():
                            color_info = row['color']
                            qty_info = int(row['quantity'])
                            report += f"\n   — {color_info}: <b>{qty_info} pochka</b>"

                    report += "\n━━━━━━━━━━━━━━\n⚠️ <i>Skladchi diqqatiga: Yuk kelganda shu ro'yxat bo'yicha qabul tarqating!</i>"

                    if hasattr(config, 'ARCHIVE_CHANNEL_ID') and config.ARCHIVE_CHANNEL_ID:
                        if photo_url and photo_url.startswith('http'):
                            await bot.send_photo(chat_id=config.ARCHIVE_CHANNEL_ID, photo=photo_url, caption=report)  
                        else:
                            await bot.send_message(chat_id=config.ARCHIVE_CHANNEL_ID, text=report)
            except Exception as e:
                logger.error(f"Kanalga yuborishda xato: {e}")
    else:
        await callback.message.delete()
        await callback.answer("❌ Tushunarli, topilmadi.", show_alert=True)
