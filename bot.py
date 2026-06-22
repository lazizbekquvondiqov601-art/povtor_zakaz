import sys
import asyncio
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.bot.init_bot import bot, dp, OBR_CACHE, STAT_CACHE
from src.bot.handlers import setup_handlers
from src.bot.middlewares.security import SecurityMiddleware
import src.database.db_manager as db_manager
import data_engine
import config
import supplier_analytics

async def scheduled_update_job():
    print("⏰ Avto-yangilash boshlandi...")
    try:
        await asyncio.to_thread(data_engine.run_full_update)
        print("✅ Avto-yangilash tugadi.")
    except Exception as e:
        print(f"❌ Avto-yangilashda xatolik: {e}")

async def cleanup_caches():
    OBR_CACHE.cleanup()
    STAT_CACHE.cleanup()

async def send_reminders():
    pending = db_manager.get_pending_orders_for_reminder(24)
    if not pending: return
    reminders = {}
    for o in pending:
        reminders.setdefault(o['telegram_id'], []).append(f"- {o['subcategory']} ({o['artikul']})")

    for uid, items in reminders.items():
        try:
            await bot.send_message(uid, "<b>🔔 Eslatma!</b> Javob berilmagan zakazlar:\n" + "\n".join(items))
        except Exception: pass

async def main():
    # Baza init
    db_manager.init_db()

    # Middlewares
    dp.message.outer_middleware(SecurityMiddleware())
    dp.callback_query.outer_middleware(SecurityMiddleware())

    # Handlers
    setup_handlers(dp)
    
    # Qo'shimcha handlerlar (agar modullashtirilmagan bo'lsa)
    supplier_analytics.register_handlers(dp, bot, STAT_CACHE, OBR_CACHE)

    # Scheduler — faqat xizmat ishlari (Billz sync MANUAL tugma orqali)
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(cleanup_caches, 'interval', minutes=10)
    scheduler.add_job(send_reminders, 'cron', hour=10, minute=0)
    scheduler.start()

    print("🤖 Bot yangi modulli arxitektura bilan ishga tushdi...")

    # Webhook o'rnatish
    webhook_url = f"{config.WEB_URL}/bot/webhook/"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    print(f"🔗 Webhook o'rnatildi: {webhook_url}")

    # Super adminga xabar
    try:
        await bot.send_message(config.SUPER_ADMIN_ID, "🚀 Bot webhook rejimida ishga tushdi!")
    except Exception as e:
        print(f"⚠️ {e}")

    # Polling yo'q — scheduler ishlaydi, jarayon tirik turadi
    print("⏰ Scheduler ishlayapti, polling yo'q.")
    await asyncio.sleep(float('inf'))

if __name__ == "__main__":
    asyncio.run(main())
