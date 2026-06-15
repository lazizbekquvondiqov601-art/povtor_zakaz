from aiogram import Dispatcher
from . import common, admin, super_admin, supplier, registration, analytics

def setup_handlers(dp: Dispatcher):
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(super_admin.router)
    dp.include_router(supplier.router)
    dp.include_router(registration.router)
    dp.include_router(analytics.router)
