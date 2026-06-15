import logging
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
import config
import db_manager

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user: 
            return await handler(event, data)
        
        user_id = user.id

        # 1. SUPER ADMIN (Har doim ruxsat)
        if user_id == config.SUPER_ADMIN_ID:
            return await handler(event, data)

        # 2. QORA RO'YXAT (Individual blok)
        if db_manager.is_blocked(user_id):
            logger.warning(f"Blocked user {user_id} attempted access.")
            return # Foydalanuvchi bloklangan bo'lsa hech narsa qaytarmaymiz

        # 3. GLOBAL QULF (Tizim yopiqmi?)
        if db_manager.is_global_locked():
            logger.info(f"System is locked. Checking access for user {user_id}")
            # Agar tizim yopiq bo'lsa, faqat "Ruxsat berilganlar" (VIP) kira oladi
            # is_allowed funksiyasi db_manager da bo'lishi kerak
            try:
                if not db_manager.is_allowed(user_id):
                    logger.warning(f"Unauthorized access attempt by user {user_id} during global lock.")
                    return
            except AttributeError:
                # Agar is_allowed hali implement qilinmagan bo'lsa, adminligini tekshiramiz
                if not db_manager.is_admin(user_id):
                    logger.warning(f"Unauthorized access attempt by non-admin user {user_id} during global lock.")
                    return

        return await handler(event, data)
