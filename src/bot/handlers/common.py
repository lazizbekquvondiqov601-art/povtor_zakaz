import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

import config
import src.database.db_manager as db_manager
from src.bot.init_bot import bot
from src.bot.keyboards.admin import get_admin_keyboard
from src.bot.keyboards.supplier import get_supplier_keyboard
from src.bot.keyboards.common import get_close_keyboard
from src.bot.states.bot_states import Registration

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def send_welcome(message: Message, state: FSMContext):
    """Start buyrug'i uchun handler."""
    logger.info(f"User {message.from_user.id} started the bot")
    await state.clear()
    user_id = message.from_user.id

    # 1. SUPER ADMIN
    if user_id == config.SUPER_ADMIN_ID:
        is_locked = db_manager.is_global_locked()
        await message.answer(
            f"👑 <b>Bosh Admin Panel</b>\nHolat: {'🚫 Yopiq' if is_locked else '✅ Ochiq'}",
            reply_markup=get_admin_keyboard(is_super_admin=True, is_locked=is_locked)
        )
        return

    # 2. ADMIN
    if db_manager.is_admin(user_id):
        await message.answer(
            "👋 Assalomu alaykum, <b>Admin!</b>\n\nQuyidagi menyudan kerakli bo'limni tanlang:",
            reply_markup=get_admin_keyboard()
        )
        return

    # 3. SUPPLIER
    supplier = db_manager.get_supplier_by_id(user_id)
    if supplier:
        await message.answer(
            f"👋 Assalomu alaykum, <b>{supplier.name}</b>!\n\nYangi zakazlarni ko'rish uchun tugmani bosing:",
            reply_markup=get_supplier_keyboard()
        )
        return

    # 4. YANGI FOYDALANUVCHI (Registration boshlanadi)
    categories = db_manager.get_unassigned_categories()
    if not categories:
        await message.answer("Hozircha bo'sh yetkazib beruvchi nomlari yo'q.")
        return

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb_builder = []
    for cat in categories:
        kb_builder.append([InlineKeyboardButton(text=cat, callback_data=f"regCat_{cat}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_builder)
    await message.answer(
        "👋 Assalomu alaykum! Tizimga kirish uchun avval faoliyat turingizni (Kategoriya) tanlang:",
        reply_markup=keyboard
    )
    await state.set_state(Registration.filter_category)

@router.callback_query(F.data == "del_msg")
async def delete_message_callback(callback: CallbackQuery):
    """Xabarni o'chirish handler."""
    logger.info(f"User {callback.from_user.id} clicked delete message")
    await callback.message.delete()
    await callback.answer()

@router.message(Command("help"))
async def help_command(message: Message):
    """Yordam xabari."""
    logger.info(f"User {message.from_user.id} requested help")
    await message.answer("Ushbu bot orqali siz zakazlarni boshqarishingiz va tahlil qilishingiz mumkin.")
