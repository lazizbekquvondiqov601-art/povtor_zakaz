import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import config
import src.database.db_manager as db_manager
from src.bot.states.bot_states import AdminStates
from src.bot.handlers.common import send_welcome

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text.in_(["🔴 Tizimni YOPISH", "🟢 Tizimni OCHISH"]))
async def toggle_system_lock(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: 
        return
    
    should_lock = "YOPISH" in message.text
    logger.info(f"Super Admin {message.from_user.id} toggled system lock to {should_lock}")
    db_manager.set_global_lock(should_lock)
    
    await message.answer(f"✅ Bajarildi! Hozir: {'🚫 Tizim YOPIQ' if should_lock else '✅ Tizim OCHIQ'}")
    await send_welcome(message, state) 

# --- BLOKLASH ---

@router.message(F.text == "🔒 Bloklash")
async def ask_block(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: return
    await message.answer("Bloklash kerak bo'lgan ID ni yuboring:")
    await state.set_state(AdminStates.waiting_block_id)

@router.message(AdminStates.waiting_block_id)
async def do_block(message: Message, state: FSMContext):
    try:
        tid = int(message.text)
        logger.info(f"Super Admin {message.from_user.id} blocking user {tid}")
        if tid == config.SUPER_ADMIN_ID:
            await message.answer("O'zingizni bloklay olmaysiz!")
        else:
            db_manager.toggle_block_user(tid, True)
            await message.answer(f"✅ {tid} bloklandi.")
    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        await message.answer("❌ ID faqat raqam bo'lishi kerak.")
    await state.clear()

# --- BLOKDAN OCHISH ---

@router.message(F.text == "🔓 Blokdan ochish")
async def ask_unblock(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: return
    await message.answer("Blokdan chiqarish kerak bo'lgan ID ni yuboring:")
    await state.set_state(AdminStates.waiting_unblock_id)

@router.message(AdminStates.waiting_unblock_id)
async def do_unblock(message: Message, state: FSMContext):
    try:
        tid = int(message.text)
        logger.info(f"Super Admin {message.from_user.id} unblocking user {tid}")
        if db_manager.toggle_block_user(tid, False):
            await message.answer(f"✅ {tid} blokdan chiqarildi.")
        else:
            await message.answer(f"⚠️ {tid} aslida blokda emas edi.")
    except Exception as e:
        logger.error(f"Error unblocking user: {e}")
        await message.answer("❌ ID faqat raqam bo'lishi kerak.")
    await state.clear()

# --- VIP (RUXSAT BERISH) ---

@router.message(F.text == "✅ VIP Qo'shish")
async def ask_allow(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: return
    await message.answer("Tizim yopiq paytida ham kira oladigan ID ni yuboring:")
    await state.set_state(AdminStates.waiting_allow_id)

@router.message(AdminStates.waiting_allow_id)
async def do_allow(message: Message, state: FSMContext):
    try:
        tid = int(message.text)
        logger.info(f"Super Admin {message.from_user.id} adding VIP user {tid}")
        try:
            db_manager.toggle_allow_user(tid, True)
            await message.answer(f"✅ {tid} ga ruxsat berildi.")
        except AttributeError:
            await message.answer("❌ is_allowed logikasi hali to'liq implement qilinmagan.")
    except Exception as e:
        logger.error(f"Error adding VIP user: {e}")
        await message.answer("❌ ID faqat raqam bo'lishi kerak.")
    await state.clear()

@router.message(F.text == "❌ VIP Olish")
async def ask_disallow(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: return
    await message.answer("VIP ro'yxatdan o'chirish kerak bo'lgan ID ni yuboring:")
    await state.set_state(AdminStates.waiting_disallow_id)

@router.message(AdminStates.waiting_disallow_id)
async def do_disallow(message: Message, state: FSMContext):
    try:
        tid = int(message.text)
        logger.info(f"Super Admin {message.from_user.id} removing VIP user {tid}")
        try:
            db_manager.toggle_allow_user(tid, False)
            await message.answer(f"❌ {tid} dan maxsus ruxsat olib tashlandi.")
        except AttributeError:
            await message.answer("❌ is_allowed logikasi hali to'liq implement qilinmagan.")
    except Exception as e:
        logger.error(f"Error removing VIP user: {e}")
        await message.answer("❌ ID faqat raqam bo'lishi kerak.")
    await state.clear()

# --- DATABASE RESET ---

@router.message(Command("reset_db"))
async def reset_db_handler(message: Message):
    if message.from_user.id != config.SUPER_ADMIN_ID:
        return

    logger.warning(f"Super Admin {message.from_user.id} requested DB reset")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💥 Ha, bazani tozalash", callback_data="confirm_db_reset")],
        [InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="del_msg")]
    ])
    
    await message.answer(
        "⚠️ <b>DIQQAT! BAZANI NOLDAN TOZALASH</b>\n\n"
        "Haqiqatan ham hamma narsani o'chirib, noldan boshlamoqchimisiz?",
        reply_markup=kb)

@router.callback_query(F.data == "confirm_db_reset")
async def confirm_db_reset_handler(callback: CallbackQuery):
    if callback.from_user.id != config.SUPER_ADMIN_ID:
        return

    logger.critical(f"Super Admin {callback.from_user.id} confirmed DB reset!")
    try:
        from sqlalchemy import text
        with db_manager.engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS f_sotuvlar;"))
            conn.execute(text("DROP TABLE IF EXISTS f_qoldiqlar;"))
            conn.execute(text("DROP TABLE IF EXISTS d_mahsulotlar;"))
        
        db_manager.init_db()
        await callback.message.edit_text("✅ <b>Baza muvaffaqiyatli tozalandi!</b>")
    except Exception as e:
        logger.error(f"Error resetting DB: {e}")
        await callback.message.edit_text(f"❌ Tozalashda xatolik: {e}")
