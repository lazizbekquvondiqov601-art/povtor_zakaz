import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

import db_manager
from src.bot.states.bot_states import Registration
from src.bot.keyboards.supplier import get_supplier_keyboard
from src.bot.handlers.common import send_welcome

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(Registration.filter_category, F.data.startswith("regCat_"))
async def category_selected(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("regCat_", 1)[1]
    logger.info(f"User {callback.from_user.id} selected category {category}")
    await state.update_data(selected_category=category)
    subcategories = db_manager.get_unassigned_subcategories(category)

    if not subcategories:
        await callback.message.edit_text("⚠️ Bu kategoriyada podkategoriyalar topilmadi.")
        return

    kb_builder = []
    for sub in subcategories:
        kb_builder.append([InlineKeyboardButton(text=sub, callback_data=f"uniSub_{sub}")])
    kb_builder.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_cats_uni")])

    await callback.message.edit_text(
        f"📂 <b>{category}</b> tanlandi.\nEndi aniq turini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_builder)
    )
    await state.set_state(Registration.filter_subcategory)

@router.callback_query(Registration.filter_subcategory, F.data.startswith("uniSub_"))
async def subcategory_selected(callback: CallbackQuery, state: FSMContext):
    subcategory = callback.data.split("uniSub_", 1)[1]
    logger.info(f"User {callback.from_user.id} selected subcategory {subcategory}")
    data = await state.get_data()
    category = data.get("selected_category")

    suppliers = db_manager.get_unassigned_suppliers_by_filter(category, subcategory)

    if not suppliers:
        await callback.message.edit_text("⚠️ Afsuski, bu bo'limda bo'sh nomlar qolmadi.")
        return

    kb_builder = []
    user_id = callback.from_user.id
    is_registered = db_manager.get_supplier_by_id(user_id) is not None

    for name in suppliers:
        action = f"change_{name}" if is_registered else f"register_{name}"
        kb_builder.append([InlineKeyboardButton(text=name, callback_data=action)])
    kb_builder.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_subs_uni")])

    await callback.message.edit_text(
        f"✅ <b>{subcategory}</b> bo'yicha bo'sh nomlar:\nO'zingiznikini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_builder)
    )

@router.callback_query(F.data.startswith("register_"))
async def process_register(callback: CallbackQuery, state: FSMContext):
    name = callback.data.split("_", 1)[1]
    user_id = callback.from_user.id
    logger.info(f"User {user_id} registering as {name}")
    if db_manager.register_supplier(user_id, name):
        await callback.message.delete()
        await callback.message.answer(f"✅ Xush kelibsiz, <b>{name}</b>!", reply_markup=get_supplier_keyboard())
    else:
        logger.warning(f"Registration failed for user {user_id} as {name}")
        await callback.message.edit_text("❌ Bu nom band.")
    await state.clear()

@router.callback_query(F.data.startswith("change_"))
async def process_change(callback: CallbackQuery, state: FSMContext):
    new_name = callback.data.split("_", 1)[1]
    user_id = callback.from_user.id
    logger.info(f"User {user_id} changing name to {new_name}")
    success, old_name = db_manager.update_supplier_name(user_id, new_name)
    if success:
        await callback.message.delete()
        await callback.message.answer(
            f"🔄 Ism o'zgardi:\nEski: {old_name}\nYangi: <b>{new_name}</b>",
            reply_markup=get_supplier_keyboard()
        )
    else:
        logger.warning(f"Name change failed for user {user_id} to {new_name}")
        await callback.message.edit_text("❌ Xatolik.")
    await state.clear()
