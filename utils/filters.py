from aiogram.filters import BaseFilter
from aiogram.types import Message
import db_manager

class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return db_manager.is_admin(message.from_user.id)
