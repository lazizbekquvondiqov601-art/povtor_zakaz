# --- BU BOT.PY FAYLINING ZAMONAVIY INTERFEYSLI VARIANTI ---
import uuid # <-- Buni importlar qatoriga qo'shing
import asyncio
import pandas as pd
import io
import calendar
import matplotlib
matplotlib.use('Agg')  # Serverda orqa fonda xatosiz ishlashi uchun GUI'ni o'chirib qo'yamiz
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import datetime, timedelta, timezone
import io
from datetime import datetime, timedelta  # timedelta qo'shiladi
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from sqlalchemy import text # (agar yuqorida import qilinmagan bo'lsa)
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, BaseFilter

from sqlalchemy import text 

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import import_file 

import config
import db_manager
import data_engine
# Buni esa importlardan keyin, bot=Bot(...) dan oldinroqqa qo'ying
STAT_CACHE = {}
# --- Bot sozlamalari ---
bot = Bot(token=config.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
class SecurityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user: return await handler(event, data)
        
        user_id = user.id

        # 1. SUPER ADMIN (Har doim ruxsat)
        if user_id == config.SUPER_ADMIN_ID:
            return await handler(event, data)

        # 2. QORA RO'YXAT (Individual blok)
        if db_manager.is_blocked(user_id):
            msg = ""
            if isinstance(event, Message): await event.answer(msg)
            elif isinstance(event, CallbackQuery): await event.answer(msg, show_alert=True)
            return

        # 3. GLOBAL QULF (Tizim yopiqmi?)
        if db_manager.is_global_locked():
            # Agar tizim yopiq bo'lsa, faqat "Ruxsat berilganlar" (VIP) kira oladi
            if not db_manager.is_allowed(user_id):
                msg = ""
                if isinstance(event, Message): await event.answer(msg)
                elif isinstance(event, CallbackQuery): await event.answer(msg, show_alert=True)
                return

        return await handler(event, data)
dp = Dispatcher()
dp.message.outer_middleware(SecurityMiddleware())
dp.callback_query.outer_middleware(SecurityMiddleware())
class Registration(StatesGroup):
    choosing_name = State()
    changing_name = State()
    # Yangi statelar:
    filter_category = State()
    filter_subcategory = State()
class AdminStates(StatesGroup):
    waiting_block_id = State()
    waiting_unblock_id = State()
    waiting_allow_id = State()    # <-- YANGI
    waiting_disallow_id = State() # <-- YANGI

class SettingsManagement(StatesGroup):
    waiting_for_new_value = State()
    choosing_setting = State()

class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return db_manager.is_admin(message.from_user.id)

# --- MENYU TUGMALARI (ZAMONAVIY) ---

def get_admin_keyboard():
    """Adminlar uchun asosiy menyu"""
    kb = [
        [KeyboardButton(text="📊 Hisobot"), KeyboardButton(text="📈 Statistika")],
        [KeyboardButton(text="📦 Qoldiqlar"), KeyboardButton(text="📅 Import Tahlili")],
        [KeyboardButton(text="📥 Kelgan Tovar"), KeyboardButton(text="🔄 Majburiy Yangilash")], # <-- Yangi tugma qo'shildi
        [KeyboardButton(text="⚙️ Sozlamalar")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Admin buyruqlarini tanlang..."
    )
def get_supplier_keyboard():
    """Yetkazib beruvchilar uchun asosiy menyu"""
    kb = [
        [KeyboardButton(text="📦 Zakazlarim (Yangi)"), KeyboardButton(text="⏳ Jarayonda")],
        [KeyboardButton(text="📈 Statistika"), KeyboardButton(text="📅 Import Tahlili")],
        [KeyboardButton(text="📝 Ismni o'zgartirish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
# --- Yordamchi Funksiyalar ---

async def get_orders_for_supplier(supplier_name: str) -> pd.DataFrame:
    cleaned_name = supplier_name.replace('\u00A0', ' ').strip()
    def _read_db():
        try:
            query = "SELECT * FROM generated_orders WHERE supplier = :name"
            df = pd.read_sql(query, db_manager.engine, params={"name": cleaned_name})
            return df
        except Exception as e:
            print(f"❌ Bazadan o'qishda xatolik: {e}")
            return pd.DataFrame()
    df = await asyncio.to_thread(_read_db)
    return df

# --- START va MENU Logikasi ---

@dp.message(CommandStart())
async def send_welcome(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    # --- 1. SUPER ADMIN MENYUSI ---
# --- 1. SUPER ADMIN MENYUSI ---
    if user_id == config.SUPER_ADMIN_ID:
        is_locked = db_manager.is_global_locked()
        lock_text = "🟢 Tizimni OCHISH" if is_locked else "🔴 Tizimni YOPISH"
        
        kb = [
            [KeyboardButton(text=lock_text)],
            [KeyboardButton(text="✅ VIP Qo'shish"), KeyboardButton(text="❌ VIP Olish")],
            [KeyboardButton(text="🔒 Bloklash"), KeyboardButton(text="🔓 Blokdan ochish")],
            [KeyboardButton(text="📊 Hisobot"), KeyboardButton(text="📈 Statistika")],
            [KeyboardButton(text="📦 Qoldiqlar"), KeyboardButton(text="📅 Import Tahlili")],
            [KeyboardButton(text="📥 Kelgan Tovar"), KeyboardButton(text="🔄 Majburiy Yangilash")], # <-- MANA SHU YERGA TO'G'RI QO'SHILDI
            [KeyboardButton(text="⚙️ Sozlamalar")]
        ]
        
        await message.answer(
            f"👑 <b>Bosh Admin Panel</b>\nHolat: {'🚫 Yopiq' if is_locked else '✅ Ochiq'}",
            reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        )
        return
    
@dp.message(IsAdmin(), F.text == "⚙️ Sozlamalar")
async def show_settings_text(message: types.Message, state: FSMContext):
    await show_settings_logic(message, state)

@dp.message(IsAdmin(), Command("settings"))
async def show_settings_command(message: types.Message, state: FSMContext):
    await show_settings_logic(message, state)

async def show_settings_logic(message: types.Message, state: FSMContext):
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
    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="cancel_settings")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.message(IsAdmin(), F.text == "📥 Kelgan Tovar")
async def kelgan_tovar_click(message: Message, state: FSMContext):
    await state.clear()
    now = datetime.now()
    # "imp_start" prefiksi bilan yangi kalendarni ochamiz
    await message.answer(
        "📥 <b>Kelgan yuk tahlili (Billz Import)</b>\n\n"
        "Kirim qilingan tovarlarni bilish uchun <b>boshlang'ich sanani</b> tanlang:",
        reply_markup=get_inline_calendar(now.year, now.month, "imp_start")
    )

@dp.message(IsAdmin(), F.text == "🔄 Majburiy Yangilash")
async def force_update_text(message: types.Message):
    await force_update_logic(message)

@dp.message(IsAdmin(), Command("force_update"))
async def force_update_command(message: types.Message):
    await force_update_logic(message)

# 🟢 YANGILASH VA XABAR BERISH UCHUN ASYNC VAZIFA 🟢
async def run_update_and_notify(chat_id: int):
    try:
        # Orqa fonda (thread ichida) yangilashni boshlaymiz
        await asyncio.to_thread(data_engine.run_full_update)
        
        # Yangilash muvaffaqiyatli tugagach adminga xabar yuboramiz
        await bot.send_message(
            chat_id=chat_id,
            text="✅ <b>Barcha ma'lumotlar muvaffaqiyatli yangilandi!</b>\n\n"
                 "📊 Sotuvlar va Qoldiqlar oxirgi holatga keltirildi.\n"
                 
        )
    except Exception as e:
        # Agar yangilashda xato chiqsa ham adminga xabar beradi
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ <b>Yangilash jarayonida jiddiy xatolik yuz berdi:</b>\n<code>{e}</code>"
        )

# YANGILASH TUGMASI BOSILGANDA ISHLAYDIGAN KOD
async def force_update_logic(message: types.Message):
    await message.answer("⏳ <b>Yangilash boshlandi...</b>\n\nBot ishlashda davom etadi. Jarayon yakunlangach sizga darhol xabar beriladi! 🔔")
    # Vazifani orqa fonda ishga tushirib, adminga javob qaytaramiz
    asyncio.create_task(run_update_and_notify(message.chat.id))

@dp.message(IsAdmin(), F.text == "📊 Hisobot")
async def report_text(message: types.Message):
    await report_logic(message)

@dp.message(IsAdmin(), Command("report"))
async def report_command(message: types.Message):
    await report_logic(message)

async def report_logic(message: types.Message):
    await message.answer("⏳ Hisobot tayyorlanmoqda...")
    report_df = await asyncio.to_thread(db_manager.get_full_report_data)

    if report_df.empty:
        await message.answer("⚠️ Ma'lumot yo'q.")
        return

    # --- TUZATISH (VAQTNI TASHKENT VAQTIGA O'TKAZISH) ---
    for col in report_df.select_dtypes(include=['datetimetz', 'datetime']).columns:
        # Agar ustunda vaqt zonasi (timezone) bo'lsa:
        if report_df[col].dt.tz is not None:
            # 1. Avval vaqtni O'zbekiston vaqtiga o'giramiz
            report_df[col] = report_df[col].dt.tz_convert('Asia/Tashkent')
            # 2. Keyin Excel qabul qilishi uchun "timezone" belgisini olib tashlaymiz
            # (Lekin soat o'zgarib ketmaydi, Toshkent vaqtida qoladi)
            report_df[col] = report_df[col].dt.tz_localize(None)
    # --- TUGADI ---

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        report_df.to_excel(writer, index=False, sheet_name='Hisobot')

        # Excel ustunlarini chiroyli qilish (Avtomatik kengaytirish)
        worksheet = writer.sheets['Hisobot']
        for i, col in enumerate(report_df.columns):
            width = max(report_df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, width)

    output.seek(0)

    file = BufferedInputFile(output.getvalue(), filename=f"hisobot_{datetime.now().strftime('%Y-%m-%d')}.xlsx")
    await message.answer_document(file, caption="✅ Hisobot tayyor.")



# test uchun
def generate_sales_chart(asosiy, aksiya, label):
    """Sotuv tahlilidan olingan ma'lumotlar asosida chiroyli grafik yaratadi"""
    # 1. Asosiy va Aksiya daromadlarini bitta ro'yxatga yig'amiz
    profits = {}
    
    if asosiy:
        for cat, data in asosiy.items():
            profits[cat] = profits.get(cat, 0) + data['profit']
    if aksiya:
        for cat, data in aksiya.items():
            profits[cat] = profits.get(cat, 0) + data['profit']
            
    if not profits:
        return None

    # 2. Foyda bo'yicha o'sish tartibida saralaymiz (grafikda eng kattasi tepada turishi uchun)
    sorted_profits = sorted(profits.items(), key=lambda x: x[1])
    
    categories = [x[0] for x in sorted_profits]
    values = [x[1] for x in sorted_profits]

    # 3. Grafik dizaynini tayyorlaymiz
    plt.figure(figsize=(10, 7))
    plt.style.use('ggplot') # Chiroyli fon va setkalar
    
    # Ustunlarni chizish
    bars = plt.barh(categories, values, color='#2fa1b3', edgecolor='black')
    
    # Sarlavha va o'qlarni yozish
    plt.title(f"Kategoriyalar bo'yicha sof foyda\n({label})", fontsize=15, fontweight='bold', pad=20)
    plt.xlabel("Foyda miqdori (so'm)", fontsize=12, fontweight='bold')
    
    # Pastki o'qni (X o'qi) chiroyli son formatiga o'tkazish (masalan: 20 000 000)
    formatter = ticker.FuncFormatter(lambda x, pos: f"{int(x):,} ".replace(",", " "))
    plt.gca().xaxis.set_major_formatter(formatter)
    
    # Har bir ustun oxiriga summani aniq yozib qo'yish
    for bar in bars:
        width = bar.get_width()
        plt.text(width + (max(values) * 0.01),  # Matn biroz o'ngroqda turadi
                 bar.get_y() + bar.get_height()/2, 
                 f"{int(width):,} so'm".replace(",", " "), 
                 va='center', ha='left', fontsize=11, fontweight='bold', color='black')

    plt.tight_layout()

    # 4. Rasmni xotiraga (RAM) saqlash (fayl qilib kompyuterga saqlamaymiz, tez ishlaydi)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close()
    
    return buf

def get_inline_calendar(year: int, month: int, state_label: str) -> InlineKeyboardMarkup:
    """Telegram inline klaviaturasi shaklida oylik kalendar yaratadi"""
    kb = []
    
    # Oy va yil sarlavhasi
    months_uz = [
        "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", 
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
    ]
    month_name = months_uz[month - 1]
    
    kb.append([
        InlineKeyboardButton(text=f"📅 {month_name} {year}", callback_data=f"cal:{state_label}:ignore:0")
    ])
    
    # Hafta kunlari sarlavhasi
    kb.append([
        InlineKeyboardButton(text=d, callback_data=f"cal:{state_label}:ignore:0")
        for d in ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
    ])
    
    # Kunlar setkasi (Grid)
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append(InlineKeyboardButton(text=" ", callback_data=f"cal:{state_label}:ignore:0"))
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                week_row.append(InlineKeyboardButton(text=str(day), callback_data=f"cal:{state_label}:day:{date_str}"))
        kb.append(week_row)
        
    # Navigatsiya tugmalari (Oldingi / Keyingi oy)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    kb.append([
        InlineKeyboardButton(text="◀️ Oy", callback_data=f"cal:{state_label}:nav:{prev_year}-{prev_month:02d}"),
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stat_sotuv"),
        InlineKeyboardButton(text="Oy ▶️", callback_data=f"cal:{state_label}:nav:{next_year}-{next_month:02d}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(IsAdmin(), Command("invite"))
async def invite_command(message: types.Message):
    try:
        ids = [int(p) for p in message.text.split()[1:] if p.isdigit()]
        if not ids:
            await message.answer("Format: <code>/invite 12345678</code>")
            return
        added, existed = db_manager.invite_users(ids)
        await message.answer(f"✅ Qo'shildi: {added}\n⚠️ Mavjud: {existed}")
    except Exception as e:
        await message.answer(f"Xato: {e}")
# SHU YERGA TASHLA:
@dp.message(F.text == "📈 Statistika")
async def show_statistics(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if db_manager.is_admin(user_id):
        kb = [
            [InlineKeyboardButton(text="📦 Zakaz statistikasi", callback_data="stat_zakaz")],
            [InlineKeyboardButton(text="📊 Sotuv tahlili", callback_data="stat_sotuv")],
            [InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]
        ]
        await message.answer(
            "📈 <b>STATISTIKA</b>\nQaysi bo'limni ko'rmoqchisiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
        return

    # Supplier logikasi o'zgarishsiz qoladi
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
# --- SUPPLIER TUGMALARI UCHUN HANDLERLAR ---

# --- ZAKAZ STATISTIKASI (eski logika) ---
@dp.callback_query(F.data == "stat_zakaz")
async def stat_zakaz_click(callback: CallbackQuery):
    categories = db_manager.get_stat_categories_global()
    if not categories:
        await callback.answer("✅ Hozircha aktiv zakazlar yo'q.", show_alert=True)
        return
    kb = []
    for cat in categories:
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"stCat_{cat}")])
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stat_back")])
    await callback.message.edit_text(
        "📦 <b>ZAKAZ STATISTIKASI</b>\n\nKategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )




# test
@dp.message(IsAdmin(), Command("test_sana"))
async def test_sana(message: Message):
    from sqlalchemy import text
    with db_manager.engine.connect() as conn:
        rows = conn.execute(text('''
            SELECT date("Дата"), SUM("Продано за вычетом возвратов")
            FROM f_sotuvlar
            WHERE date("Дата") >= "2026-05-28"
            GROUP BY date("Дата")
            ORDER BY date("Дата")
        ''')).fetchall()
    
    text_out = "\n".join([f"{r[0]}: {int(r[1])}" for r in rows])
    await message.answer(f"<pre>{text_out}</pre>")




# --- SOTUV TAHLILI BOSH MENYU ---
@dp.callback_query(F.data == "stat_sotuv")
async def stat_sotuv_click(callback: CallbackQuery):
    today = datetime.now(timezone(timedelta(hours=5))).replace(tzinfo=None)
    kb = []
    
    for days in [5, 10, 15, 20]:
        start = (today - timedelta(days=days-1)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (start, end, f"So'nggi {days} kun")
        kb.append([InlineKeyboardButton(
            text=f"📅 So'nggi {days} kun", 
            callback_data=f"sotuv_{unique_id}"
        )])
    
    kb.append([InlineKeyboardButton(text="✏️ O'zim sana kiriting", callback_data="sotuv_custom")])
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stat_back")])
    
    await callback.message.edit_text(
        "📊 <b>SOTUV TAHLILI</b>\n\nQaysi davr uchun ko'rmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

# --- TAYYOR DAVR TANLANGANDA ---
@dp.callback_query(F.data.startswith("sotuv_"), ~F.data.in_({"sotuv_custom"}))
async def sotuv_period_click(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data:
        await callback.answer("⚠️ Eskirgan ma'lumot.", show_alert=True)
        return
    
    start_date, end_date, label = data
    await callback.message.edit_text(f"⏳ <b>{label}</b> yuklanmoqda...")
    await show_sales_result(callback.message, start_date, end_date, label)

@dp.callback_query(F.data == "sotuv_custom")
async def sotuv_custom_click(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    now = datetime.now()
    # Boshlang'ich sanani kalendardan tanlash
    await callback.message.edit_text(
        "📅 <b>Boshlang'ich sanani tanlang:</b>",
        reply_markup=get_inline_calendar(now.year, now.month, "start")
    )

@dp.callback_query(F.data.startswith("cal:"))
async def process_calendar_selection(callback: CallbackQuery, state: FSMContext):
    _, state_label, action, value = callback.data.split(":")
    
    if action == "ignore":
        await callback.answer()
        return
        
    elif action == "nav":
        year, month = map(int, value.split("-"))
        # Sarlavhani aniqlash
        if state_label == "start": title = "Boshlang'ich (Sotuv)"
        elif state_label == "end": title = "Tugash (Sotuv)"
        elif state_label == "imp_start": title = "Boshlang'ich (Import)"
        else: title = "Tugash (Import)"
        
        try:
            await callback.message.edit_text(
                f"📅 <b>{title} sanani tanlang:</b>",
                reply_markup=get_inline_calendar(year, month, state_label)
            )
        except Exception:
            pass
        await callback.answer()
        
    elif action == "day":
        # =========================================================
        # === A) SOTUV TAHLILI KALENDARI ===
        # =========================================================
        if state_label == "start":
            # Boshlang'ich sana tanlandi -> Tugash sanasini so'raymiz
            await state.update_data(start_date=value)
            dt = datetime.strptime(value, "%Y-%m-%d")
            await callback.message.edit_text(
                f"📅 Boshlang'ich sana: <b>{value}</b>\n\n📅 <b>Tugash sanasini tanlang:</b>",
                reply_markup=get_inline_calendar(dt.year, dt.month, "end")
            )
            await callback.answer()
            
        elif state_label == "end":
            # Tugash sana tanlandi -> Sotuv tahlilini boshlaymiz
            data = await state.get_data()
            start_str = data.get("start_date")
            end_str = value
            
            if not start_str:
                await callback.message.answer("⚠️ Boshlang'ich sana topilmadi. Qaytadan urinib ko'ring.")
                return
            
            start_dt = datetime.strptime(start_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_str, "%Y-%m-%d")
            
            if end_dt < start_dt:
                await callback.answer("❌ Tugash sanasi boshlang'ichdan oldin bo'lishi mumkin emas!", show_alert=True)
                return
                
            if (end_dt - start_dt).days > 23:
                await callback.answer("❌ Maksimal 23 kunlik davr tanlang!", show_alert=True)
                return
            
            await callback.answer()
            await state.clear()
            label = f"{start_str} — {end_str}"
            await callback.message.edit_text(f"⏳ <b>{label}</b> yuklanmoqda...")
            await show_sales_result(callback.message, start_str, end_str, label)

        # =========================================================
        # === B) KELGAN TOVAR (IMPORT) KALENDARI ===
        # =========================================================
        elif state_label == "imp_start":
            # Import boshlang'ich tanlandi -> Import tugash sanasini so'raymiz
            await state.update_data(imp_start_date=value)
            dt = datetime.strptime(value, "%Y-%m-%d")
            await callback.message.edit_text(
                f"📥 Boshlang'ich: <b>{value}</b>\n\n📅 <b>Tugash sanasini tanlang:</b>",
                reply_markup=get_inline_calendar(dt.year, dt.month, "imp_end")
            )
            await callback.answer()

        elif state_label == "imp_end":
            # Import tugash tanlandi -> Import tahlilini boshlaymiz
            data = await state.get_data()
            start_str = data.get("imp_start_date")
            end_str = value
            
            if not start_str:
                await callback.message.answer("⚠️ Xatolik yuz berdi. Boshidan urinib ko'ring.")
                return
                
            start_dt = datetime.strptime(start_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_str, "%Y-%m-%d")
            
            if end_dt < start_dt:
                await callback.answer("❌ Tugash sanasi boshlang'ichdan oldin bo'lishi mumkin emas!", show_alert=True)
                return
                
            if (end_dt - start_dt).days > 3:
                await callback.answer("❌ Maksimal 3 kunlik ma'lumotni ko'rish mumkin!", show_alert=True)
                return
            
            # Telegram aylanuvchi soatni darhol o'chiramiz
            await callback.answer("⏳ Import yuklanmoqda...")
            await state.clear()
            
            await callback.message.edit_text(
                f"⏳ <b>{start_str} — {end_str}</b> oralig'idagi importlar Billz dan yuklanmoqda...\n"
                f"⚠️ Bu jarayon 1-2 daqiqa vaqt olishi mumkin."
            )
            
            # API va bazani yangilash
            access_token = data_engine.get_billz_access_token()
            result, res_data = await asyncio.to_thread(
                import_file.sync_imports_by_dates, access_token, db_manager.engine, start_str, end_str
            )
            
            def format_money(val):
                return f"{int(val):,}".replace(",", " ")

            if result == "dax":
                summary = await asyncio.to_thread(
                    import_file.get_imported_summary_by_dax, db_manager.engine, start_str, end_str
                )
                
                text_out = f"📥 <b>KELGAN TOVARLAR TAHLILI (DAX)</b>\n"
                text_out += f"📅 Davr: <b>{start_str} — {end_str}</b>\n\n"
                
                grand_total = 0
                for cat, dax_list in sorted(summary.items()):
                    text_out += f"📦 <b>{cat}:</b>\n"
                    cat_total = 0
                    for dax_grp, qty in dax_list:
                        text_out += f"  - {dax_grp}: <b>{int(qty)} dona</b>\n"
                        cat_total += qty
                    text_out += f"  👉 <b>Jami {cat}: {int(cat_total)} dona</b>\n\n"
                    grand_total += cat_total
                    
                text_out += "━━━━━━━━━━━━━━\n"
                text_out += f"🚛 <b>UMUMIY JAMI IMPORT: {int(grand_total)} dona</b>"
                
                kb = [[InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]]
                await callback.message.edit_text(text_out, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            elif result == "summary":
                text_out = f"📥 <b>KELGAN YUKLAR RO'YXATI (UMUMIY)</b>\n"
                text_out += f"📅 Davr: <b>{start_str} — {end_str}</b>\n"
                text_out += f"⚠️ <i>Eslatma: Tovar batafsil tahlili yopiq (403). Quyida umumiy yuklar:</i>\n\n"
                
                grand_total = 0
                for i, imp in enumerate(res_data, 1):
                    name = imp.get("name") or f"Import #{imp.get('external_id')}"
                    qty = int(imp.get("total_arrived_measurement_value", 0))
                    supply_p = int(imp.get("total_supply_price", 0))
                    retail_p = int(imp.get("total_retail_price", 0))
                    date_val = imp.get("created_at", "")
                    
                    text_out += f"<b>{i}. {name}</b>\n"
                    text_out += f"  - Kelgan miqdor: <b>{qty} dona</b>\n"
                    text_out += f"  - Jami tan narxi: <b>{format_money(supply_p)} so'm</b>\n"
                    text_out += f"  - Jami sotuv narxi: <b>{format_money(retail_p)} so'm</b>\n"
                    text_out += f"  - Sana: <code>{date_val}</code>\n\n"
                    grand_total += qty
                    
                text_out += "━━━━━━━━━━━━━━\n"
                text_out += f"🚛 <b>JAMI KELGAN TOVAR: {grand_total} dona</b>"
                
                kb = [[InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]]
                await callback.message.edit_text(text_out, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            else:
                await callback.message.edit_text(
                    f"⚠️ <b>{start_str} — {end_str}</b> kunlarida import topilmadi."
                )
async def show_sales_result(message, start_date: str, end_date: str, label: str):
    print(f"🔍 show_sales_result chaqirildi: {label}")
    
    asosiy, aksiya = await asyncio.to_thread(
        db_manager.get_sales_by_period, start_date, end_date
    )
    
    if not asosiy and not aksiya:
        await message.edit_text(f"⚠️ <b>{label}</b>\nMa'lumot topilmadi.")
        return
    
    def format_money(val):
        return f"{int(val):,}".replace(",", " ")

    def pad_str(text, length, align='left'):
        text = str(text)
        if len(text) > length:
            text = text[:length-2] + ".." 
        if align == 'left':
            return text.ljust(length)
        return text.rjust(length)

    text = f"📊 <b>SOTUV TAHLILI</b>\n"
    text += f"📅 Davr: <b>{label}</b>\n\n"
    
    # --- ASOSIY TOVARLAR ---
    text += "🏢 <b>ASOSIY TOVARLAR:</b>\n"
    total_asosiy_qty = 0
    total_asosiy_profit = 0
    
    if asosiy:
        text += "<pre>\n"
        text += "Kategoriya     | Soni  |       Foyda\n"
        text += "-" * 36 + "\n"
        for cat, data in sorted(asosiy.items()):
            c_name = pad_str(cat, 14, 'left')
            c_qty = pad_str(int(data['qty']), 5, 'right')
            c_prof = pad_str(format_money(data['profit']), 11, 'right')
            text += f"{c_name} | {c_qty} | {c_prof}\n"
            total_asosiy_qty += data['qty']
            total_asosiy_profit += data['profit']
            
        text += "-" * 36 + "\n"
        text += f"JAMI           | {pad_str(int(total_asosiy_qty), 5, 'right')} | {pad_str(format_money(total_asosiy_profit), 11, 'right')}\n"
        text += "</pre>\n"
    else:
        text += " <i>Ma'lumot yo'q</i>\n\n"
    
    # --- AKSIYA TOVARLAR ---
    text += "🎁 <b>AKSIYA TOVARLAR (010/011):</b>\n"
    total_aksiya_qty = 0
    total_aksiya_profit = 0
    
    if aksiya:
        text += "<pre>\n"
        text += "Kategoriya     | Soni  |       Foyda\n"
        text += "-" * 36 + "\n"
        for cat, data in sorted(aksiya.items()):
            c_name = pad_str(cat, 14, 'left')
            c_qty = pad_str(int(data['qty']), 5, 'right')
            c_prof = pad_str(format_money(data['profit']), 11, 'right')
            text += f"{c_name} | {c_qty} | {c_prof}\n"
            total_aksiya_qty += data['qty']
            total_aksiya_profit += data['profit']
            
        text += "-" * 36 + "\n"
        text += f"JAMI           | {pad_str(int(total_aksiya_qty), 5, 'right')} | {pad_str(format_money(total_aksiya_profit), 11, 'right')}\n"
        text += "</pre>\n"
    else:
        text += " <i>Ma'lumot yo'q</i>\n\n"
    
    text += "━━━━━━━━━━━━━━\n"
    text += f"🚛 <b>UMUMIY JAMI: {int(total_asosiy_qty + total_aksiya_qty)} dona</b>\n"
    text += f"💵 <b>UMUMIY FOYDA: {format_money(total_asosiy_profit + total_aksiya_profit)} so'm</b>"
    
    kb = [[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stat_sotuv")],
          [InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]]
    
    # --- Rasm chizish jarayoni ---
    chart_buf = await asyncio.to_thread(generate_sales_chart, asosiy, aksiya, label)
    
    # Agar rasm muvaffaqiyatli chizilsa
    if chart_buf:
        photo = BufferedInputFile(chart_buf.getvalue(), filename="chart.png")
        # 1. Avval "yuklanmoqda..." xabarini o'chiramiz
        await message.delete()
        
        # 2. Rasmni yuboramiz
        await bot.send_photo(chat_id=message.chat.id, photo=photo, caption="📈 <b>Foyda tahlili grafigi</b>")
        
        # 3. Ostidan chiroyli matnli jadvalni va tugmalarni yuboramiz
        await bot.send_message(chat_id=message.chat.id, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        # Agar rasm chizishda nimadir xato ketsa, faqat matnni o'zini yangilab qo'yaqoladi
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
# --- ORQAGA QAYTISH ---
@dp.callback_query(F.data == "stat_back")
async def stat_back(callback: CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="📦 Zakaz statistikasi", callback_data="stat_zakaz")],
        [InlineKeyboardButton(text="📊 Sotuv tahlili", callback_data="stat_sotuv")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]
    ]
    await callback.message.edit_text(
        "📈 <b>STATISTIKA</b>\nQaysi bo'limni ko'rmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
# --- SUPPLIER TUGMALARI UCHUN HANDLERLAR ---

@dp.message(F.text == "📦 Zakazlarim (Yangi)")
async def my_orders_text(message: types.Message):
    supplier = db_manager.get_supplier_by_id(message.from_user.id)
    if not supplier:
        await message.answer("❌ Tizimga kirmagansiz. /start")
        return

    msg = await message.answer("⏳ Yuklanmoqda...")
    orders_df = await get_orders_for_supplier(supplier.name)

    if orders_df.empty:
        await msg.edit_text("✅ Zakazlar yo'q.")
        return

    # Filtrlash
    new_orders = orders_df[orders_df['status'] == 'Kutilmoqda'].copy()
    pending_orders = orders_df[orders_df['status'] == 'Topdim'].copy()
    
    # Qizillarni (3 kundan oshganlarni) topish
    red_orders = pd.DataFrame()
    if not pending_orders.empty:
        pending_orders['created_at_dt'] = pd.to_datetime(pending_orders['created_at'])
        now = datetime.now()
        # 3 kundan oshganlar
        mask_red = (now - pending_orders['created_at_dt']).dt.days >= 3
        red_orders = pending_orders[mask_red].copy()

    await msg.delete()

    if new_orders.empty and red_orders.empty:
        await message.answer("✅ Yangi yoki Muammoli zakazlar yo'q.\n'⏳ Jarayonda' tugmasini tekshiring.")
        return

    # --- 1-QISM: MUAMMOLI (QIZIL) ---
    if not red_orders.empty:
        grouped_red = red_orders.groupby('artikul')
        await message.answer(f"🚨 <b>DIQQAT! KELMAGAN TOVARLAR:</b>\n<i>3 kundan oshdi!</i>")
        
        for article, group in grouped_red:
            first = group.iloc[0]
            # Qizil uchun tugma: Qayta Olish yoki Bekor qilish
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Qayta Olish", callback_data=f"feedback:Topdim:{article}"),
                 InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_order:{article}")]
            ])
            
            # Podkategoriyani olamiz
            subcat_val = str(first.get('subcategory', '-')).strip()
            
            caption = f"🔴 <b>{article}</b> (Kechikyapti!)\n<i>{subcat_val}</i>\n"
            dona_cats = ['Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье']
            unit_name = "dona" if first.get('category') in dona_cats else "pochka"
            for shop, s_group in group.groupby('shop'):
                            caption += f"\n🏪 <b>{shop}:</b>"
                            for _, row in s_group.iterrows():
                                dona_cats = ['Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье']
                                cat_name = str(first.get('category', '')).strip()
                                unit_name = "dona" if cat_name in dona_cats else "pochka"
                                
                                raw_qoldiq = row.get('hozirgi_qoldiq', 0)
                                qoldiq = int(float(raw_qoldiq)) if pd.notna(raw_qoldiq) else 0
                                
                                # 🟢 SOTUV SONINI OLISH (S) 🟢
                                raw_prodano = row.get('prodano', 0)
                                sotuv = int(float(raw_prodano)) if pd.notna(raw_prodano) else 0
                                
                                caption += f"\n  - {row.get('color','-')}: <b>{int(row.get('quantity',0))} {unit_name}</b> (Q:{qoldiq}) (S:{sotuv})"
            
            await bot.send_message(message.chat.id, caption, reply_markup=keyboard)
            await asyncio.sleep(0.2)

    # --- 2-QISM: YANGI (OQ) ---
    if not new_orders.empty:
        grouped_new = new_orders.groupby('artikul')
        await message.answer(f"🔥 <b>YANGI ZAKAZLAR ({len(grouped_new)} ta):</b>")
        
        for article, group in grouped_new:
            first = group.iloc[0]
            # Eslatma (Agar sariq bo'lsa)
            pending_match = pending_orders[pending_orders['artikul'] == article]
            warning_text = ""
            if not pending_match.empty:
                qty = pending_match['quantity'].sum()
                warning_text = f"\n⚠️ <b>Eslatma:</b> {int(qty)} ta yo'lda."

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Topdim", callback_data=f"feedback:Topdim:{article}"),
                 InlineKeyboardButton(text="❌ Topilmadi", callback_data=f"feedback:Topilmadi:{article}")]
            ])
            
            price = first.get('supply_price', 0)
            try: price_str = f"{float(price):,.0f}".replace(",", " ")
            except: price_str = "0"

            caption = f"📦 <b>{article}</b>{warning_text}\n💵 Tan Narx: <b>{price_str} so'm</b>\nToifa: {first.get('subcategory', '-')}\n"

    # O'lchov birligini aniqlash (Tsikldan tashqarida 1 marta aniqlaymiz)
            dona_cats = ['Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье']
            unit_name = "dona" if first.get('category') in dona_cats else "pochka"

            for shop, s_group in group.groupby('shop'):
                            caption += f"\n🏪 <b>{shop}:</b>"
                            for _, row in s_group.iterrows():
                                dona_cats = ['Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье']
                                cat_name = str(first.get('category', '')).strip()
                                unit_name = "dona" if cat_name in dona_cats else "pochka"
                                
                                raw_qoldiq = row.get('hozirgi_qoldiq', 0)
                                qoldiq = int(float(raw_qoldiq)) if pd.notna(raw_qoldiq) else 0
                                
                                # 🟢 SOTUV SONINI OLISH (S) 🟢
                                raw_prodano = row.get('prodano', 0)
                                sotuv = int(float(raw_prodano)) if pd.notna(raw_prodano) else 0
                                
                                caption += f"\n  - {row.get('color','-')}: <b>{int(row.get('quantity',0))} {unit_name}</b> (Q:{qoldiq}) (S:{sotuv})"

            photo = str(first.get('photo', ''))
            try:
                if photo.startswith('http'):
                    await bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=keyboard)
                else:
                    await bot.send_message(message.chat.id, caption, reply_markup=keyboard)
            except:
                await bot.send_message(message.chat.id, caption, reply_markup=keyboard)
            await asyncio.sleep(0.3)

@dp.message(F.text == "⏳ Jarayonda")
async def pending_orders_text(message: types.Message):
    # 1. Bazadan faqat 'Topdim' statusli Kategoriyalarni olamiz
    query = "SELECT DISTINCT category FROM generated_orders WHERE status = 'Topdim' ORDER BY category"
    cats_df = pd.read_sql(query, db_manager.engine)
    
    if cats_df.empty:
        await message.answer("✅ Jarayonda (Yo'lda) hech qanday zakaz yo'q.")
        return

    kb = []
    for cat in cats_df['category']:
        # Uzun nomlar uchun ID ishlatamiz (xuddi Import Tahlilidek)
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = cat
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"pendCat_{unique_id}")])
    kb.append([InlineKeyboardButton(text="📥 Sklad uchun Excel (Billz Import)", callback_data="download_sklad_excel")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])
    
    
    await message.answer(
        "⏳ <b>JARAYONDA (YO'LDA)</b>\nQaysi bo'limni ko'rmoqchisiz?", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@dp.callback_query(F.data.startswith("pendCat_"))
async def pending_category_click(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    category = STAT_CACHE.get(uid)
    
    if not category:
        await callback.answer("⚠️ Eskirgan ma'lumot.", show_alert=True)
        return

    # Podkategoriyalarni olamiz
    query = "SELECT DISTINCT subcategory FROM generated_orders WHERE status = 'Topdim' AND category =:cat ORDER BY subcategory"
    subs_df = pd.read_sql(query, db_manager.engine, params={"cat": category})
    
    kb = []
    for sub in subs_df['subcategory']:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (category, sub) # Ikkalasini saqlaymiz
        kb.append([InlineKeyboardButton(text=f"🔹 {sub}", callback_data=f"pendSub_{unique_id}")])
    
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_pend_cats")])
    
    await callback.message.edit_text(
        f"📂 <b>{category}</b> (Jarayonda)\nPodkategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

# Orqaga qaytish (Kategoriyalarga)
@dp.callback_query(F.data == "back_to_pend_cats")
async def back_pend_cats(callback: CallbackQuery):
    await callback.message.delete()
    # Qayta chaqiramiz (Message obyekti kerak, callback.message ni ishlatamiz)
    await pending_orders_text(callback.message)

@dp.callback_query(F.data.startswith("pendSub_"))
async def pending_subcategory_click(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data: return
    
    category, subcategory = data
    
    # Ma'lumotlarni olamiz
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

    # Qizil va Sariq ajratish
    orders_df['created_at_dt'] = pd.to_datetime(orders_df['created_at'])
    now = datetime.now()
    mask_red = (now - orders_df['created_at_dt']).dt.days >= 3
    
    red_orders = orders_df[mask_red].copy()
    yellow_orders = orders_df[~mask_red].copy()

    # --- QIZIL (MUAMMO) ---
    if not red_orders.empty:
        await show_pending_group(callback.message, red_orders, "🚨 <b>DIQQAT! KECHIKKANLAR (3+ kun):</b>", "red")

    # --- SARIQ (NORMAL) ---
    if not yellow_orders.empty:
        await show_pending_group(callback.message, yellow_orders, "⏳ <b>JARAYONDA (Yo'lda):</b>", "yellow")

    # Tugatish
    kb = [[InlineKeyboardButton(text="🔄 Boshqa bo'lim", callback_data="back_to_pend_cats")]]
    await bot.send_message(callback.message.chat.id, "✅ Ro'yxat tugadi.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# Yordamchi funksiya (Kod takrorlanmasligi uchun)
async def show_pending_group(message, df, title, color_type):
    await bot.send_message(message.chat.id, title)
    grouped = df.groupby('artikul')
    
    for article, group in grouped:
        first = group.iloc[0]
        # Bekor qilish tugmasi
        kb = [[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_order:{article}")]]
        
        icon = "🔴" if color_type == "red" else "🟡"
        # Supplier nomini ham chiqaramiz (Kim olib kelayotganini bilish uchun)
        supplier_name = first.get('supplier', 'Noma\'lum')
        
        # Podkategoriyani olamiz
        subcat_val = str(first.get('subcategory', '-')).strip()
        
        caption = f"{icon} <b>{article}</b> ({supplier_name})\n<i>{subcat_val}</i>\n"

        for shop, s_group in group.groupby('shop'):
                    caption += f"\n🏪 <b>{shop}:</b>"
                    for _, row in s_group.iterrows():
                        dona_cats = ['Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье']
                        cat_name = str(first.get('category', '')).strip()
                        unit_name = "dona" if cat_name in dona_cats else "pochka"
                        
                        raw_qoldiq = row.get('hozirgi_qoldiq', 0)
                        qoldiq = int(float(raw_qoldiq)) if pd.notna(raw_qoldiq) else 0
                        
                        # 🟢 SOTUV SONINI OLISH (S) 🟢
                        raw_prodano = row.get('prodano', 0)
                        sotuv = int(float(raw_prodano)) if pd.notna(raw_prodano) else 0
                        
                        caption += f"\n  - {row.get('color','-')}: <b>{int(row.get('quantity',0))} {unit_name}</b> (Q:{qoldiq}) (S:{sotuv})"

        photo = str(first.get('photo', ''))
        try:
            if photo.startswith('http'):
                await bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            else:
                await bot.send_message(message.chat.id, caption, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        except:
            await bot.send_message(message.chat.id, caption, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await asyncio.sleep(0.2)

@dp.message(F.text == "📝 Ismni o'zgartirish")
async def change_name_text(message: types.Message, state: FSMContext):
    # 1-qadam: Mavjud bo'sh kategoriyalarni olish
    categories = db_manager.get_unassigned_categories()

    if not categories:
        await message.answer("⚠️ Hozircha bo'sh yetkazib beruvchilar yoki zakazlar yo'q.")
        return

    # Kategoriyalarni tugma qilish
    # Callback data sig'ishi uchun qisqartma ishlatamiz yoki shundayligicha (agar nomlar uzun bo'lmasa)
    kb_builder = []
    for cat in categories:
        kb_builder.append([InlineKeyboardButton(text=cat, callback_data=f"catSel_{cat}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_builder)

    await message.answer("📂 Iltimos, faoliyatingiz turini (Kategoriya) tanlang:", reply_markup=keyboard)
    await state.set_state(Registration.filter_category)
# --- ESKI CALLBACK VA SOZLAMALAR LOGIKASI ---

@dp.callback_query(Registration.choosing_name, F.data.startswith("register_"))
async def process_register(callback: CallbackQuery, state: FSMContext):
    name = callback.data.split("_", 1)[1]
    if db_manager.register_supplier(callback.from_user.id, name):
        await callback.message.delete()
        await callback.message.answer(f"✅ Xush kelibsiz, <b>{name}</b>!", reply_markup=get_supplier_keyboard())
    else:
        await callback.message.edit_text("❌ Bu nom band.")
    await state.clear()

@dp.callback_query(Registration.changing_name, F.data.startswith("change_"))
async def process_change(callback: CallbackQuery, state: FSMContext):
    new_name = callback.data.split("_", 1)[1]
    success, old_name = db_manager.update_supplier_name(callback.from_user.id, new_name)
    if success:
        await callback.message.delete()
        await callback.message.answer(
            f"🔄 Ism o'zgardi:\nEski: {old_name}\nYangi: <b>{new_name}</b>",
            reply_markup=get_supplier_keyboard()
        )
    else:
        await callback.message.edit_text("❌ Xatolik.")
    await state.clear()

# --- BEKOR QILISH TUGMASI ---
@dp.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order_handler(callback: CallbackQuery):
    artikul = callback.data.split(":")[1]
    
    # Tasdiqlash so'raymiz
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ha, Bekor qilish", callback_data=f"confirm_cancel:{artikul}"),
         InlineKeyboardButton(text="Yo'q, Qaytish", callback_data="del_msg")]
    ])
    await callback.message.answer(f"⚠️ <b>{artikul}</b> ni 'Kutilmoqda' ro'yxatidan o'chirib tashlamoqchimisiz?\n(Keyingi safar yana Yangi bo'lib chiqadi)", reply_markup=confirm_kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_cancel:"))
async def confirm_cancel_handler(callback: CallbackQuery):
    artikul = callback.data.split(":")[1]
    # supplier ni tekshirish shart emas, chunki Jarayonda bo'limi umumiy
    
    try:
        from sqlalchemy import text
        with db_manager.engine.begin() as conn:
            # --- O'ZGARISH: 'AND supplier = ...' olib tashlandi ---
            # Faqat Artikul va Status bo'yicha topib o'zgartiramiz
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


@dp.callback_query(F.data == "download_sklad_excel")
async def download_sklad_excel_handler(callback: CallbackQuery):
    # 1. Bildirishnoma yuboramiz
    await callback.message.answer("⏳ <b>Sklad uchun Excel fayl shakllantirilmoqda...</b>\nBiroz kuting.")
    
    # 2. Orqa fonda faylni yaratamiz
    excel_buf = await asyncio.to_thread(db_manager.generate_sklad_excel)

    if not excel_buf:
        await callback.message.answer("⚠️ Hozircha 'Jarayonda' turgan (Topdim) tovarlar yo'q.")
        await callback.answer()
        return

    # 3. Tayyor faylni yuboramiz
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

@dp.callback_query(F.data.startswith("feedback:"))
async def feedback_handler(callback: CallbackQuery):
    _, status, artikul = callback.data.split(":")
    
    # Agar "Topdim" tugmasi bosilgan bo'lsa
    if status == 'Topdim':
        # 1. Bazada statusni o'zgartiramiz
        if db_manager.update_order_status(artikul, 'Topdim'):
            
            # --- A) BOTDAGI XABARNI O'ZGARTIRISH ---
            new_text = f"✅ <b>{artikul}</b> qabul qilindi va 'Kutilmoqda' ro'yxatiga o'tkazildi."
            try:
                if callback.message.photo:
                    await callback.message.edit_caption(caption=new_text, reply_markup=None)
                else:
                    await callback.message.edit_text(new_text, reply_markup=None)
            except: pass

            # --- B) KANALGA TO'LIQ HISOBOT YUBORISH (YANGI KOD) ---
            try:
                # Bazadan to'liq ma'lumotni olamiz
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
                    # Umumiy pochka sonini hisoblaymiz
                    total_qty = details_df['quantity'].sum()

                    # Xabarni chiroyli yig'amiz
                    report = f"✅ <b>YUK KELYAPTI! (Tasdiqlandi)</b>\n\n"
                    report += f"📦 Artikul: <b>{artikul}</b>\n"
                    report += f"💵 Tan Narx: <b>{price_str} so'm</b>\n" 
                    report += f"🚛 Yetkazuvchi: <b>{supplier_name}</b>\n"
                    report += f"👤 Tasdiqladi: <b>{callback.from_user.full_name}</b>\n"
                    report += f"🔢 Jami miqdor: <b>{int(total_qty)} pochka</b>\n"
                    report += "━━━━━━━━━━━━━━\n"
                    report += "📋 <b>TARQATISH RO'YXATI:</b>\n"

                    # Do'konlar bo'yicha guruhlaymiz
                    for shop, group in details_df.groupby('shop'):
                        report += f"\n🏪 <b>{shop}:</b>"
                        for _, row in group.iterrows():
                            # Rang va sonini yozamiz
                            color_info = row['color']
                            qty_info = int(row['quantity'])
                            report += f"\n   — {color_info}: <b>{qty_info} pochka</b>"
                    
                    report += "\n━━━━━━━━━━━━━━\n⚠️ <i>Skladchi diqqatiga: Yuk kelganda shu ro'yxat bo'yicha qabul tarqating!</i>"

                    # Kanalga yuborish (Rasmi bo'lsa rasm bilan, bo'lmasa matn)
                    if photo_url and photo_url.startswith('http'):
                        await bot.send_photo(chat_id=config.ARCHIVE_CHANNEL_ID, photo=photo_url, caption=report)
                    else:
                        await bot.send_message(chat_id=config.ARCHIVE_CHANNEL_ID, text=report)
                else:
                    # Agar biror sabab bilan detal chiqmasa, oddiy xabar
                    await bot.send_message(chat_id=config.ARCHIVE_CHANNEL_ID, text=f"✅ Topildi: {artikul} (Tafsilotlar topilmadi)")

            except Exception as e:
                print(f"Kanalga yuborishda xato: {e}")
                # Xato bo'lsa ham bot to'xtab qolmasligi kerak
                pass
            
    else:
        # Agar "Topilmadi" bosilgan bo'lsa
        await callback.message.delete()
        await callback.answer("❌ Tushunarli, topilmadi.", show_alert=True)
# --- SOZLAMALAR CALLBACKLARI ---
@dp.callback_query(F.data.startswith("edit_rule_"))
async def edit_rule(callback: CallbackQuery, state: FSMContext):
    rule = callback.data.split("_")[-1]
    parts = {f"m{rule}_min_days": "Min kun", f"m{rule}_max_days": "Max kun", f"m{rule}_percentage": "Foiz %"}
    btns = [[InlineKeyboardButton(text=v, callback_data=f"edit_setting_{k}")] for k, v in parts.items()]
    btns.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_rules")])
    await callback.message.edit_text(f"<b>{rule}-Qoida</b>ni tahrirlash:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await state.set_state(SettingsManagement.choosing_setting)

@dp.callback_query(SettingsManagement.choosing_setting, F.data == "back_to_rules")
async def back_rules(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_settings_logic(callback.message, state) # Logic funksiyani chaqiramiz

@dp.callback_query(SettingsManagement.choosing_setting, F.data.startswith("edit_setting_"))
async def edit_val(callback: CallbackQuery, state: FSMContext):
    name = callback.data.replace("edit_setting_", "")
    await state.update_data(setting_to_edit=name)
    await callback.message.edit_text(f"<code>{name}</code> uchun yangi qiymat yozing:", reply_markup=None)
    await state.set_state(SettingsManagement.waiting_for_new_value)

@dp.message(SettingsManagement.waiting_for_new_value)
async def save_val(message: Message, state: FSMContext):
    if not message.text.replace('.', '', 1).isdigit():
        await message.answer("❌ Raqam yozing.")
        return
    data = await state.get_data()
    if db_manager.update_setting(data['setting_to_edit'], float(message.text)):
        await message.answer("✅ Saqlandi.")
    else:
        await message.answer("❌ Xatolik.")
    await state.clear()
    await show_settings_logic(message, state)

@dp.callback_query(F.data == "cancel_settings")
async def cancel_s(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()



@dp.callback_query(Registration.filter_category, F.data.contains("Cat_") | F.data.contains("catSel_"))
async def category_selected(callback: CallbackQuery, state: FSMContext):
    # Datadan kategoriyani ajratib olamiz (prefiksni olib tashlab)
    data_str = callback.data
    if "regCat_" in data_str: category = data_str.split("regCat_", 1)[1]
    elif "catSel_" in data_str: category = data_str.split("catSel_", 1)[1]
    else: category = data_str # Ehtiyot shart

    await state.update_data(selected_category=category)

    subcategories = db_manager.get_unassigned_subcategories(category)

    if not subcategories:
        await callback.message.edit_text("⚠️ Bu kategoriyada podkategoriyalar topilmadi.")
        return

    kb_builder = []
    for sub in subcategories:
        # Podkategoriya tanlanganda ham universal prefiks
        kb_builder.append([InlineKeyboardButton(text=sub, callback_data=f"uniSub_{sub}")])

    kb_builder.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_cats_uni")])

    await callback.message.edit_text(
        f"📂 <b>{category}</b> tanlandi.\nEndi aniq turini (Podkategoriya) tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_builder)
    )
    await state.set_state(Registration.filter_subcategory)

# 2. Podkategoriya tanlanganda -> Supplierlar chiqadi
@dp.callback_query(Registration.filter_subcategory, F.data.startswith("uniSub_"))
async def subcategory_selected(callback: CallbackQuery, state: FSMContext):
    subcategory = callback.data.split("uniSub_", 1)[1]
    data = await state.get_data()
    category = data.get("selected_category")

    suppliers = db_manager.get_unassigned_suppliers_by_filter(category, subcategory)

    if not suppliers:
        await callback.message.edit_text("⚠️ Afsuski, bu bo'limda bo'sh nomlar qolmadi.")
        return

    # Hozir foydalanuvchi ro'yxatdan o'tyaptimi yoki ism o'zgartiryaptimi?
    # Buni bilish uchun check_invitation yoki state holatidan foydalanamiz.
    # Lekin oddiyroq yo'li: Tugma bosilganda bazada supplier bormi yo'qmi tekshiramiz.

    kb_builder = []
    user_id = callback.from_user.id
    is_registered = db_manager.get_supplier_by_id(user_id) is not None

    for name in suppliers:
        if is_registered:
            # Ism o'zgartirish rejimi
            action = f"change_{name}"
        else:
            # Ro'yxatdan o'tish rejimi
            action = f"register_{name}"

        kb_builder.append([InlineKeyboardButton(text=name, callback_data=action)])

    kb_builder.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_subs_uni")])

    await callback.message.edit_text(
        f"✅ <b>{subcategory}</b> bo'yicha bo'sh nomlar:\nO'zingiznikini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_builder)
    )
    # Bu yerda stateni o'zgartirish shart emas, callbacklar (register_ yoki change_) o'zi hal qiladi
    # Lekin to'g'ri handler ushlab olishi uchun:
    if is_registered:
        await state.set_state(Registration.changing_name)
    else:
        await state.set_state(Registration.choosing_name)

# Orqaga qaytish logikasi
@dp.callback_query(F.data == "back_to_cats_uni")
async def back_uni_cat(callback: CallbackQuery, state: FSMContext):
    # Qayta start bergandek bo'lamiz (Admin yoki Userligiga qarab)
    await send_welcome(callback.message, state)

@dp.callback_query(F.data == "back_to_subs_uni")
async def back_uni_sub(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category = data.get("selected_category")

    # Obyektni o'zgartirish o'rniga, uning nusxasini yaratib, ma'lumotni o'zgartiramiz
    new_callback = callback.model_copy(update={'data': f"regCat_{category}"})

    await category_selected(new_callback, state)
# 2. Podkategoriya tanlanganda -> Supplierlar chiqadi
@dp.callback_query(Registration.filter_subcategory, F.data.startswith("subSel_"))
async def subcategory_selected(callback: CallbackQuery, state: FSMContext):
    subcategory = callback.data.split("_", 1)[1]
    data = await state.get_data()
    category = data.get("selected_category")

    suppliers = db_manager.get_unassigned_suppliers_by_filter(category, subcategory)

    if not suppliers:
        await callback.message.edit_text("⚠️ Afsuski, bu bo'limda bo'sh nomlar qolmadi.")
        return

    kb_builder = []
    for name in suppliers:
        # Bu yerda eski 'change_' prefiksini ishlatamiz, chunki oxirgi logika o'zgarmasin
        kb_builder.append([InlineKeyboardButton(text=name, callback_data=f"change_{name}")])

    kb_builder.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_subs")])

    await callback.message.edit_text(
        f"✅ <b>{subcategory}</b> bo'yicha bo'sh nomlar:\nO'zingiznikini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_builder)
    )
    # Bu yerdan buyog'iga eski logika (changing_name) ishlashni davom etadi
    await state.set_state(Registration.changing_name)

# --- "ORQAGA" TUGMALARI UCHUN HANDLERLAR ---

@dp.callback_query(F.data == "back_to_cats")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    await change_name_text(callback.message, state)

@dp.callback_query(F.data == "back_to_subs")
async def back_to_subcategories(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category = data.get("selected_category")

    # To'g'ri usul:
    new_callback = callback.model_copy(update={'data': f"catSel_{category}"})

    await category_selected(new_callback, state)
# --- MAIN LOOP ---
async def scheduled_update_job():
    print("⏰ Avto-yangilash...")
    await asyncio.to_thread(data_engine.run_full_update)

async def send_reminders():
    # Eslatma logikasi o'zgarishsiz qoladi, faqat asinxronlikka e'tibor bering
    pending = db_manager.get_pending_orders_for_reminder(24)
    if not pending: return
    reminders = {}
    for o in pending:
        reminders.setdefault(o['telegram_id'], []).append(f"- {o['subcategory']} ({o['artikul']})")

    for uid, items in reminders.items():
        try:
            await bot.send_message(uid, "<b>🔔 Eslatma!</b> Javob berilmagan zakazlar:\n" + "\n".join(items))
        except Exception: pass


# --- ADMIN STATISTIKA NAVIGATSIYASI ---

# 1. Kategoriya tanlanganda -> Podkategoriyalar chiqadi
@dp.callback_query(F.data.startswith("stCat_"))
async def stat_category_click(callback: CallbackQuery):
    # Kategoriya nomini olamiz
    category = callback.data.split("stCat_", 1)[1]
    
    subs = db_manager.get_stat_subcategories_global(category)
    
    kb = []
    for sub in subs:
        # --- MUHIM O'ZGARISH ---
        # Uzun nomlarni sig'dirish uchun unikal ID ishlatamiz
        unique_id = str(uuid.uuid4())[:8]  # Masalan: 'a1b2c3d4'
        
        # Ma'lumotni xotiraga saqlaymiz: ID -> (Kategoriya, Podkategoriya)
        STAT_CACHE[unique_id] = (category, sub)
        
        # Tugmaga faqat qisqa ID ni yozamiz (Xatolik bermaydi)
        kb.append([InlineKeyboardButton(text=f"🔹 {sub}", callback_data=f"stSub_{unique_id}")])
    
    # Orqaga qaytish
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stBack_root")])
    
    await callback.message.edit_text(
        f"📂 <b>{category}</b>\nIchki turlarni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

# 2. Podkategoriya tanlanganda -> Aniq son chiqadi
@dp.callback_query(F.data.startswith("stSub_"))
async def stat_subcategory_click(callback: CallbackQuery):
    # Qisqa ID ni olamiz
    unique_id = callback.data.split("stSub_", 1)[1]
    
    # Xotiradan haqiqiy nomlarni qidiramiz
    data = STAT_CACHE.get(unique_id)
    
    if not data:
        await callback.answer("⚠️ Ma'lumot eskirgan, qaytadan oching.", show_alert=True)
        return

    category, subcategory = data
    
    total_packs = db_manager.get_stat_total_packs(category, subcategory)
    
    # Qayta tanlash uchun tugma
    kb = [
        [InlineKeyboardButton(text="⬅️ Ortga qaytish", callback_data=f"stCat_{category}")]
    ]
    
    await callback.message.edit_text(
        f"📊 <b>NATIJA:</b>\n\n"
        f"📂 Kategoriya: <b>{category}</b>\n"
        f"🔹 Podkategoriya: <b>{subcategory}</b>\n\n"
        f"📦 Jami zakaz: <b>{int(total_packs)} pochka</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

# 3. "Orqaga" va "Yopish" tugmalari
@dp.callback_query(F.data == "stBack_root")
async def stat_back_root(callback: CallbackQuery):
    # Qaytadan kategoriyalarni yuklaymiz
    categories = db_manager.get_stat_categories_global()
    kb = []
    for cat in categories:
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"stCat_{cat}")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])
    
    await callback.message.edit_text(
        "📊 <b>UMUMIY STATISTIKA</b>\n\nQaysi bo'limni ko'rmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@dp.callback_query(F.data == "del_msg")
async def delete_msg(callback: CallbackQuery):
    await callback.message.delete()








# -------------------------------------------------------------------------
# --- IMPORT (KUN) TAHLILI LOGIKASI (GLOBAL KO'RISH) ---
# -------------------------------------------------------------------------

# --- bot.py ---

# 1-FUNKSIYA: MENYUGA TUGMA QO'SHISH
@dp.message(F.text == "📅 Import Tahlili")
async def import_analysis_start(message: types.Message):
    settings = db_manager.get_all_settings()
    ranges = []
    
    rule_labels = {
        4: "🔥 4-Qoida (Eng yangi)",
        3: "⚡️ 3-Qoida",
        2: "⚠️ 2-Qoida",
        1: "❄️ 1-Qoida (Eski)"
    }

    for i in [4, 3, 2, 1]:
        min_d = int(settings.get(f'm{i}_min_days', 0))
        max_d = int(settings.get(f'm{i}_max_days', 0))
        if max_d > 0:
            btn_text = f"{rule_labels[i]}: {min_d}-{max_d} kun"
            ranges.append((min_d, max_d, btn_text))
    
    kb = []
    
    # --- YANGI GURUHLANGAN TUGMALAR ---
    kb.append([
        InlineKeyboardButton(text="🧥 Ust kiyimlar", callback_data="impMix_Tops"),
        InlineKeyboardButton(text="👖 Shim/Yubka", callback_data="impMix_Bottoms")
    ])
    kb.append([
        InlineKeyboardButton(text="👟 Oyoq kiyim", callback_data="impMix_Shoes"),
        InlineKeyboardButton(text="👶 Chaqaloqlar", callback_data="impMix_Newborn")
    ])
    kb.append([
        InlineKeyboardButton(text="🧢 Boshqalar (Aksessuar/Ichki kiyim...)", callback_data="impMix_Others")
    ])
    # ------------------------------------

    for mn, mx, label in ranges:
        kb.append([InlineKeyboardButton(text=label, callback_data=f"impRange_{mn}-{mx}")])
    
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])
    
    await message.answer(
        "📅 <b>IMPORT TAHLILI</b>\n\n"
        "Bozordagi umumiy holatni ko'rish uchun yo'nalishni tanlang:", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )


@dp.callback_query(F.data.startswith("impMix_"))
async def import_mix_special_click(callback: CallbackQuery):
    group = callback.data.split("_")[1]
    
    # Kategoriyalar xaritasi (SQL uchun)
    groups_map = {
        "Tops": "('Верхняя одежда', 'Комплект', 'Плечевые одежды')",
        "Bottoms": "('Поясные одежды')",
        "Shoes": "('Обувь')",
        "Newborn": "('Новорождённый')",
        "Others": "('Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье')"
    }
    
    # Sarlavhalar
    titles_map = {
        "Tops": "🧥 UST KIYIMLAR",
        "Bottoms": "👖 SHIMLAR VA YUBKALAR",
        "Shoes": "👟 OYOQ KIYIMLAR",
        "Newborn": "👶 CHAQALOQLAR UCHUN",
        "Others": "🧢 AKSESSUAR VA BOSHQA"
    }
    
    target_cats = groups_map.get(group)
    title = titles_map.get(group)
    
    if not target_cats:
        return

    # 1. Sozlamalar va kunlar (Masalan 2,3,4 qoidalarni qamrab olamiz)
    settings = db_manager.get_all_settings()
    min_day = int(settings.get('m4_min_days', 1)) 
    max_day = int(settings.get('m2_max_days', 15))

    await callback.message.delete()
    msg = await callback.message.answer(f"⏳ <b>{title}</b>\nMa'lumotlar yuklanmoqda ({min_day}-{max_day} kunlik)...")

# 2. SQL so'rov (Xavfsiz text() formati bilan)
    query = text(f"""
    SELECT * FROM generated_orders 
    WHERE days_passed >= :min_day AND days_passed <= :max_day
    AND category IN {target_cats}
    ORDER BY supplier ASC, subcategory ASC, artikul ASC
    """)
    
    try:
        all_orders = pd.read_sql(query, db_manager.engine, params={"min_day": min_day, "max_day": max_day})
    except Exception as e:
        await msg.edit_text(f"❌ Xatolik: {e}")
        return

    if all_orders.empty:
        await msg.edit_text(f"✅ Hozircha <b>{title}</b> yo'nalishida {min_day}-{max_day} kunlik zakazlar topilmadi.")
        return

    # 3. Pagination tayyorgarligi
    unique_artikuls = all_orders['artikul'].unique()
    
    batch_id = str(uuid.uuid4())[:8]
    STAT_CACHE[batch_id] = {
        'full_df': all_orders,
        'artikuls': unique_artikuls,
        'offset': 0,
        'batch_size': 10
    }

    # Birinchi partiyani yuborish
    await send_mix_batch(callback.message.chat.id, batch_id)

@dp.callback_query(F.data.startswith("impRange_"))
async def imp_range_click(callback: CallbackQuery):
    mn, mx = map(int, callback.data.split("_")[1].split("-"))
    
    # GLOBAL qidiruv (Supplier filtrlanmaydi)
    cats = db_manager.get_stats_by_import_days(mn, mx)
    
    if not cats:
        await callback.answer("⚠️ Bu muddatda zakazlar yo'q", show_alert=True)
        return

    kb = []
    for cat in cats:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (mn, mx, cat)
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"impCat_{unique_id}")])
    
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="impBack_root")])
    
    await callback.message.edit_text(
        f"📅 <b>{mn}-{mx} kunlik tovarlar</b>\nKategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

# 2. Kategoriya tanlanganda -> Podkategoriya chiqadi
@dp.callback_query(F.data.startswith("impCat_"))
async def imp_cat_click(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data: return
    
    mn, mx, cat = data
    subs = db_manager.get_stats_by_import_days(mn, mx, category=cat)
    
    kb = []
    for sub in subs:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = (mn, mx, cat, sub)
        kb.append([InlineKeyboardButton(text=f"🔹 {sub}", callback_data=f"impSub_{unique_id}")])
    
    kb.append([InlineKeyboardButton(text="⬅️ Boshiga", callback_data="impBack_root")])
    
    await callback.message.edit_text(
        f"📂 <b>{cat}</b> ({mn}-{mx} kun)\nPodkategoriyani tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

# 3. Podkategoriya tanlanganda -> KARTOCHKALAR CHIQADI
# --- BOT.PY ---

@dp.callback_query(F.data.startswith("impSub_"))
async def imp_sub_click(callback: CallbackQuery):
    uid = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data: return
    
    mn, mx, cat, sub = data
    
    # 1. Bazadan ma'lumot olamiz (Yangi 'Kutilmoqda' lar)
    new_orders = await asyncio.to_thread(db_manager.get_import_orders_detailed, mn, mx, cat, sub)
    
    # 2. Sariq va Qizillarni olamiz ('Topdim' statusi)
    # Buning uchun alohida funksiya yozish shart emas, shu yerdan filtrlaymiz
    # Lekin get_import_orders_detailed faqat 'Kutilmoqda' ni qaytaradi.
    # Bizga 'Topdim' ham kerak. 
    # Keling, db_manager ga murojaat qilmasdan, to'g'ridan-to'g'ri SQL bilan olamiz (tezroq bo'ladi)
    

    query = text("""
    SELECT * FROM generated_orders 
    WHERE category = :cat AND subcategory = :sub
    """)
    all_orders = pd.read_sql(query, db_manager.engine, params={"cat": cat, "sub": sub})
    
    if all_orders.empty:
        await callback.answer("⚠️ Ma'lumot topilmadi.", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(f"⏳ <b>{cat} > {sub}</b>\nMa'lumotlar yuklanmoqda...")

    # --- GURUHLASH ---
    # Qizil (Topdim + 3 kun o'tgan)
    now = datetime.now()
    all_orders['created_at_dt'] = pd.to_datetime(all_orders['created_at'])
    
    # Maska (Shartlar)
    is_topdim = all_orders['status'] == 'Topdim'
    is_new = all_orders['status'] == 'Kutilmoqda'
    is_late = (now - all_orders['created_at_dt']).dt.days >= 3
    
    red_df = all_orders[is_topdim & is_late].copy()
    yellow_df = all_orders[is_topdim & ~is_late].copy()
    white_df = all_orders[is_new].copy()

    # --- 1. QIZIL (MUAMMO) ---
    if not red_df.empty:
        await message_sender(callback.message, red_df, "🚨 <b>DIQQAT! KECHIKKANLAR (3+ kun):</b>", "red")

    # --- 2. OQ (YANGI) ---
    if not white_df.empty:
        await message_sender(callback.message, white_df, "🔥 <b>YANGI EHTIYOJLAR:</b>", "white", pending_df=yellow_df)

    # --- 3. SARIQ (JARAYONDA) ---
    if not yellow_df.empty:
        await message_sender(callback.message, yellow_df, "⏳ <b>JARAYONDA (Yo'lda):</b>", "yellow")

    # Tugatish menyusi
    kb = [[InlineKeyboardButton(text="🔄 Boshqa bo'lim", callback_data="impBack_root")]]
    await bot.send_message(callback.message.chat.id, "✅ Ro'yxat tugadi.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# --- YORDAMCHI FUNKSIYA (Xabar chiqaruvchi) ---
async def message_sender(message, df, title, color_type, pending_df=None):
    await bot.send_message(message.chat.id, title)
    grouped = df.groupby('artikul')
    
    for article, group in grouped:
        first = group.iloc[0]
        price = first.get('supply_price', 0)
        try: price_str = f"{float(price):,.0f}".replace(",", " ")
        except: price_str = "0"

        # Tugmalar
        kb = []
        if color_type == "white": # Yangi
            kb.append([InlineKeyboardButton(text="✅ Topdim", callback_data=f"feedback:Topdim:{article}"),
                       InlineKeyboardButton(text="❌ Topilmadi", callback_data=f"feedback:Topilmadi:{article}")])
        elif color_type == "red" or color_type == "yellow": # Eski
            kb.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_order:{article}")])
        
        # Eslatma
        warning = ""
        if color_type == "white" and pending_df is not None:
            match = pending_df[pending_df['artikul'] == article]
            if not match.empty:
                qty = match['quantity'].sum()
                warning = f"\n⚠️ <b>Eslatma:</b> {int(qty)} ta yo'lda."

        # 🟢 MANA SHU YERDA PROBELLARDAN TOZALAB TEKSHIRAMIZ 🟢
        dona_cats = ['Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье']
        cat_name = str(first.get('category', '')).strip() # .strip() bo'sh joylarni olib tashlaydi
        unit_name = "dona" if cat_name in dona_cats else "pochka"

        # Matn
# Podkategoriyani olamiz
        subcat_val = str(first.get('subcategory', '-')).strip()

        icon = "🔴" if color_type == "red" else ("🟡" if color_type == "yellow" else "📦")
        # Artikul tagiga qiya harflar bilan podkategoriyani qo'shamiz
        caption = f"{icon} <b>{article}</b>\n<i>{subcat_val}</i>{warning}\n"
        
        if color_type == "white":
            caption += f"👤 {first.get('supplier', '-')}\n💵 {price_str} so'm\n"
        
        for shop, s_group in group.groupby('shop'):
                    caption += f"\n🏪 <b>{shop}:</b>"
                    for _, row in s_group.iterrows():
                        # Qoldiqni olish (Q)
                        raw_qoldiq = row.get('hozirgi_qoldiq', 0)
                        qoldiq = int(float(raw_qoldiq)) if pd.notna(raw_qoldiq) else 0
                        
                        # 🟢 SOTUV SONINI OLISH (S) 🟢
                        raw_prodano = row.get('prodano', 0)
                        sotuv = int(float(raw_prodano)) if pd.notna(raw_prodano) else 0
                        
                        # Yakuniy matn: 16 pochka (Q:57) (S:10)
                        caption += f"\n  - {row.get('color','-')}: <b>{int(row.get('quantity', 0))} {unit_name}</b> (Q:{qoldiq}) (S:{sotuv})"

        # Rasm
        photo = str(first.get('photo', ''))
        try:
            if photo.startswith('http'):
                await bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            else:
                await bot.send_message(message.chat.id, caption, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        except:
            await bot.send_message(message.chat.id, caption, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await asyncio.sleep(0.2)

@dp.callback_query(F.data == "impBack_root")
async def imp_back_root(callback: CallbackQuery):
    await import_analysis_start(callback.message)

# --- SUPER ADMIN BUYRUQLARI (TUZATILGAN VARIANT) ---

@dp.message(F.text.in_(["🔴 Tizimni YOPISH", "🟢 Tizimni OCHISH"]))
async def toggle_system_lock(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: return
    
    should_lock = "YOPISH" in message.text
    db_manager.set_global_lock(should_lock)
    
    await message.answer(f"✅ Bajarildi! Hozir: {'🚫 Tizim YOPIQ' if should_lock else '✅ Tizim OCHIQ'}")
    await send_welcome(message, state) 

# --- BLOKLASH QISMI ---
@dp.message(F.text == "🔒 Bloklash")
async def ask_block(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: return
    await message.answer("Bloklash kerak bo'lgan ID ni yuboring:")
    # Mana bu yer o'zgardi:
    await state.set_state(AdminStates.waiting_block_id)

@dp.message(AdminStates.waiting_block_id)  # <-- Mana bu yer ham o'zgardi
async def do_block(message: Message, state: FSMContext):
    try:
        tid = int(message.text)
        if tid == config.SUPER_ADMIN_ID:
            await message.answer("O'zingizni bloklay olmaysiz!")
        else:
            db_manager.toggle_block_user(tid, True)
            await message.answer(f"✅ {tid} bloklandi. U endi 'Hozircha zakazlar yo'q' deb javob oladi.")
    except: 
        await message.answer("❌ ID faqat raqam bo'lishi kerak.")
    await state.clear()

# --- BLOKDAN CHIQARISH QISMI ---
@dp.message(F.text == "🔓 Blokdan ochish")
async def ask_unblock(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: return
    await message.answer("Blokdan chiqarish kerak bo'lgan ID ni yuboring:")
    # Mana bu yer o'zgardi:
    await state.set_state(AdminStates.waiting_unblock_id)

@dp.message(AdminStates.waiting_unblock_id) # <-- Mana bu yer ham o'zgardi
async def do_unblock(message: Message, state: FSMContext):
    try:
        tid = int(message.text)
        if db_manager.toggle_block_user(tid, False):
            await message.answer(f"✅ {tid} blokdan chiqarildi.")
        else:
            await message.answer(f"⚠️ {tid} aslida blokda emas edi, lekin ro'yxat tozalandi.")
    except: 
        await message.answer("❌ ID faqat raqam bo'lishi kerak.")
    await state.clear()

# --- VIP (RUXSAT BERISH) QISMI ---

@dp.message(F.text == "✅ VIP Qo'shish")
async def ask_allow(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: return
    await message.answer("Tizim yopiq paytida ham kira oladigan ID ni yuboring:")
    await state.set_state(AdminStates.waiting_allow_id)

@dp.message(AdminStates.waiting_allow_id)
async def do_allow(message: Message, state: FSMContext):
    try:
        tid = int(message.text)
        db_manager.toggle_allow_user(tid, True)
        await message.answer(f"✅ {tid} ga ruxsat berildi.\nTizim yopiq bo'lsa ham u kira oladi.")
    except: await message.answer("❌ ID faqat raqam bo'lishi kerak.")
    await state.clear()

@dp.message(F.text == "❌ VIP Olish")
async def ask_disallow(message: Message, state: FSMContext):
    if message.from_user.id != config.SUPER_ADMIN_ID: return
    await message.answer("VIP ro'yxatdan o'chirish kerak bo'lgan ID ni yuboring:")
    await state.set_state(AdminStates.waiting_disallow_id)

@dp.message(AdminStates.waiting_disallow_id)
async def do_disallow(message: Message, state: FSMContext):
    try:
        tid = int(message.text)
        db_manager.toggle_allow_user(tid, False)
        await message.answer(f"❌ {tid} dan maxsus ruxsat olib tashlandi.")
    except: await message.answer("❌ ID faqat raqam bo'lishi kerak.")
    await state.clear()

async def send_mix_batch(chat_id, batch_id):
    data = STAT_CACHE.get(batch_id)
    if not data:
        await bot.send_message(chat_id, "⚠️ Ma'lumot eskirgan. Iltimos, bo'limga qaytadan kiring.")
        return

    full_df = data['full_df']
    all_artikuls = data['artikuls']
    offset = data['offset']
    limit = data['batch_size']

    # 1. Hozirgi partiyaga kerakli artikullarni kesib olamiz
    current_artikuls = all_artikuls[offset : offset + limit]
    
    if len(current_artikuls) == 0:
        await bot.send_message(chat_id, "✅ Ro'yxat to'liq tugadi.")
        return

    # Foydalanuvchiga qayerdaligini bildiramiz
    await bot.send_message(chat_id, f"🚀 <b>YUKLANMOQDA...</b>\n{offset+1} dan {offset+len(current_artikuls)} gacha (Jami: {len(all_artikuls)})")

    # 2. Shu artikullarga tegishli qatorlarni DF dan ajratib olamiz
    batch_df = full_df[full_df['artikul'].isin(current_artikuls)].copy()

    # 3. Guruhlash va Yuborish
    now = datetime.now()
    batch_df['created_at_dt'] = pd.to_datetime(batch_df['created_at'])
    
    is_topdim = batch_df['status'] == 'Topdim'
    is_late = (now - batch_df['created_at_dt']).dt.days >= 3
    
    # Tartib buzilmasligi uchun yana sort qilamiz (Supplier -> Artikul)
    batch_df = batch_df.sort_values(by=['supplier', 'artikul'])

    red_df = batch_df[is_topdim & is_late]
    yellow_df = batch_df[is_topdim & ~is_late]
    white_df = batch_df[batch_df['status'] == 'Kutilmoqda']

    # Xabar yuborish uchun soxta Message obyekti
    class DummyMsg:
        def __init__(self, cid): self.chat = type('obj', (object,), {'id': cid})
    
    dummy_msg = DummyMsg(chat_id)

    # --- QIZIL (MUAMMO) ---
    if not red_df.empty:
        # message_sender funksiyasi o'zi artikul va supplier nomini chiqaradi
        await message_sender(dummy_msg, red_df, "🚨 <b>DIQQAT! KECHIKKANLAR:</b>", "red")
    
    # --- OQ (YANGI) ---
    if not white_df.empty:
        # Sariqda borlarini eslatma qilish uchun butun df dan qidiramiz
        full_yellow = full_df[(full_df['status']=='Topdim') & ~(full_df['artikul'].isin(current_artikuls))]
        # Bu yerda message_sender 'white' rejimi uchun Narx va Supplierni chiqaradi
        await message_sender(dummy_msg, white_df, "🔥 <b>YANGI ZAKAZLAR:</b>", "white", pending_df=full_yellow)

    # --- SARIQ (JARAYONDA) ---
    if not yellow_df.empty:
        await message_sender(dummy_msg, yellow_df, "⏳ <b>JARAYONDA (Yo'lda):</b>", "yellow")

    # 4. Keyingi qadam uchun ma'lumotni yangilaymiz
    data['offset'] += limit
    
    # 5. "DAVOM ETISH" va "TO'XTATISH" Tugmalari
    if data['offset'] < len(all_artikuls):
        remains = len(all_artikuls) - data['offset']
        kb = [
            [InlineKeyboardButton(text=f"▶️ DAVOM ETISH (Yana {remains} ta)", callback_data=f"nextMix_{batch_id}")],
            [InlineKeyboardButton(text="⏹ TO'XTATISH", callback_data="del_msg")]
        ]
        await bot.send_message(chat_id, "👇 Keyingi partiyani yuklaymizmi?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        # Agar tugagan bo'lsa
        kb = [[InlineKeyboardButton(text="🔄 Menyuga qaytish", callback_data="impBack_root")]]
        await bot.send_message(chat_id, "✅ <b>BARCHASI YUBORILDI.</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("nextMix_"))
async def next_mix_batch_handler(callback: CallbackQuery):
    batch_id = callback.data.split("_")[1]
    
    # Eski "Davom etish" tugmasini o'chirib tashlaymiz (Chat toza turishi uchun)
    try:
        await callback.message.delete()
    except:
        pass
        
    # Keyingi partiyani yuboramiz
    await send_mix_batch(callback.message.chat.id, batch_id)


# --- ADMIN QOLDIQLAR TAHLILI HANDLERLARI ---


@dp.callback_query(F.data == "back_to_stock_cats")
async def back_to_stock_categories(callback: CallbackQuery):
    max_date = db_manager.get_max_stock_date_str()
    categories = db_manager.get_stock_categories_on_max_date()
    
    kb = []
    
    # Avval kategoriyalarni chiqaramiz
    for cat in categories:
        unique_id = str(uuid.uuid4())[:8]
        STAT_CACHE[unique_id] = cat
        kb.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"stqCat_{unique_id}")])
    
    # --- EXCEL TUGMASINI ENG PASTGA QO'YAMIZ ---
    kb.append([InlineKeyboardButton(text="📥 Barchasini Excelda olish", callback_data="download_stock_excel")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])
    
    await callback.message.edit_text(
        f"📦 <b>QOLDIQLAR TAHLILI</b>\n"
        f"📅 Oxirgi qoldiq sanasi: <b>{max_date}</b>\n\n"
        f"Hisobotni ko'rish uchun kategoriyani tanlang yoki Excel faylni yuklab oling:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )



# --- ADMIN QOLDIQLAR TAHLILI HANDLERLARI (7 KUNLIK KALENDAR) ---

@dp.message(IsAdmin(), F.text == "📦 Qoldiqlar")
async def show_stock_dates(message: types.Message):
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

@dp.callback_query(F.data == "back_to_stock_dates")
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

@dp.callback_query(F.data.startswith("stqDate_"))
async def stock_date_click(callback: CallbackQuery):
    target_date = callback.data.split("stqDate_", 1)[1]  # TO'G'RI
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

@dp.callback_query(F.data.startswith("stqCat_"))
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
    
    text += "🏢 <b>ASOSIY TOVARLAR (010 bo'lmagan):</b>\n"
    total_asosiy = 0
    if asosiy_summary:
        for sub, gender, qty in asosiy_summary:
            text += f" 🔹 {sub} ({gender}): <b>{int(qty)} dona</b>\n"
            total_asosiy += qty
        text += f" 📦 <b>Jami Asosiy: {int(total_asosiy)} dona</b>\n\n"
    else:
        text += " <i>Ma'lumot yo'q</i>\n\n"
        
    text += "━━━━━━━━━━━━━━\n\n"
        
    text += "🎁 <b>AKSIYA TOVARLARI (010 Artikullar):</b>\n"
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

# --- EXCEL FAYL YARATISH VA YUBORISH HANDLERI ---
@dp.callback_query(F.data.startswith("downStockEx_"))
async def download_stock_excel_handler(callback: CallbackQuery):
    target_date = callback.data.split("_")[1]  # "downStockEx_2024-01-15" → "2024" oladi!
    
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
# --- MAIN LOOP (BOTNI ISHGA TUSHIRISH MOTOR) ---
async def main():
    db_manager.init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Avtomatik vazifalar (Jadvallar)
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(scheduled_update_job, 'cron', hour=3, minute=0)
    scheduler.add_job(send_reminders, 'cron', hour=10, minute=0)
    scheduler.start()
    
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())