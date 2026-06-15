import uuid
import asyncio
import logging
import pandas as pd
from datetime import datetime
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.fsm.context import FSMContext

import config
import db_manager
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
        await message.answer("✅ Yangi yoki Muammoli zakazlar yo'q.")
        return

    # --- QIZIL (KECHIKKANLAR) ---
    if not red_orders.empty:
        await message.answer(f"🚨 <b>DIQQAT! KELMAGAN TOVARLAR:</b>")
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
        caption += f"({first.get('supplier', 'Noma\u02bclum')})\n"

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
            new_text = f"✅ <b>{artikul}</b> qabul qilindi."
            try:
                if callback.message.photo: await callback.message.edit_caption(caption=new_text, reply_markup=None)
                else: await callback.message.edit_text(new_text, reply_markup=None)
            except Exception as e:
                logger.error(f"Error updating feedback message: {e}")
            
            # Kanalga hisobot yuborish logikasi (bot.py dan)
            # ... (bu qismni keyinroq optimallashtiramiz)
            pass
    else:
        await callback.message.delete()
        await callback.answer("❌ Tushunarli, topilmadi.", show_alert=True)
