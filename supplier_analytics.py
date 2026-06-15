# supplier_analytics.py
import uuid
import asyncio
import io
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from datetime import datetime, timedelta, timezone
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot, Router, F

import src.database.db_manager as db_manager
import auto_zakaz

router = Router()
TASHKENT_TZ = timezone(timedelta(hours=5))

class SupplierSearch(StatesGroup):
    waiting_query = State()

def search_suppliers_by_name(query: str) -> list[str]:
    from sqlalchemy import text
    try:
        session = db_manager.Session()
        try:
            all_suppliers = session.execute(text(
                "SELECT DISTINCT \"Поставщик\" FROM d_mahsulotlar WHERE \"Поставщик\" IS NOT NULL AND TRIM(\"Поставщик\") != ''"
            )).fetchall()

            query_clean = query.strip().lower()
            results = []

            for (name,) in all_suppliers:
                if not name: continue
                name_clean = name.strip().lower()
                if query_clean in name_clean:
                    results.append((0, name))
                    continue
                for word in name_clean.split():
                    if word.startswith(query_clean[:3]):
                        results.append((1, name))
                        break

            results.sort(key=lambda x: x[0])
            seen = set()
            unique = []
            for _, name in results:
                if name not in seen:
                    seen.add(name)
                    unique.append(name)
            return unique

        finally:
            session.close()
    except Exception as e:
        print(f"❌ Supplier qidiruvda xatolik: {e}")
        return []

def get_supplier_sales_report(supplier_name: str) -> tuple:
    """Oy boshidan hisoblaydi"""
    from sqlalchemy import text
    try:
        session = db_manager.Session()
        try:
            now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d")
            end_date   = now.strftime("%Y-%m-%d")

            like_pattern = f"%{supplier_name}%"
            params = {"supplier": like_pattern, "start_date": start_date, "end_date": end_date}

            query_sotuv = text('''
                SELECT 
                    COALESCE(NULLIF(TRIM(s."Категория"), ''), 'Boshqa') as kat,
                    SUM(s."Продано за выchetom vozvratov") as total_sold,
                    SUM(s."Валовая прибыль") as total_profit
                FROM f_sotuvlar s
                JOIN d_mahsulotlar d ON s.product_id = d.product_id
                WHERE d."Поставщик" LIKE :supplier
                  AND date(s."Дата") >= :start_date
                  AND date(s."Дата") <= :end_date
                  AND s."Артикул" NOT LIKE '010%'
                  AND s."Артикул" NOT LIKE '011%'
                  AND s."Наименование" NOT LIKE 'Пакет%'
                GROUP BY kat
                ORDER BY total_profit DESC
            ''')

            query_qoldiq = text('''
                SELECT 
                    COALESCE(NULLIF(TRIM(q."Категория"), ''), 'Boshqa') as kat,
                    SUM(q."Кол-во") as total_qty
                FROM f_qoldiqlar q
                JOIN d_mahsulotlar d ON q.product_id = d.product_id
                WHERE d."Поставщик" LIKE :supplier
                  AND date(q."Дата") = (SELECT MAX(date("Дата")) FROM f_qoldiqlar)
                  AND q."Артикул" NOT LIKE '010%'
                  AND q."Артикул" NOT LIKE '011%'
                  AND q."Категория" IS NOT NULL
                  AND TRIM(q."Категория") != ''
                GROUP BY kat
                HAVING SUM(q."Кол-во") > 0
            ''')

            sotuv_rows  = session.execute(query_sotuv,  params).fetchall()
            qoldiq_rows = session.execute(query_qoldiq, params).fetchall()

            sotuv  = {kat: {"qty": float(q or 0), "profit": float(p or 0)} for kat, q, p in sotuv_rows}
            qoldiq = {kat: float(q or 0) for kat, q in qoldiq_rows}

            return sotuv, qoldiq, start_date, end_date
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Supplier hisobotida xatolik: {e}")
        return {}, {}, "", ""

def generate_supplier_table_image(supplier_name: str, sotuv: dict, qoldiq: dict, start_date: str, end_date: str):
    def fmt_money(val):
        return f"{int(val):,}".replace(",", " ")

    all_cats = sorted(sotuv.keys())
    rows = []
    total_qoldiq = total_sotuv = total_foyda = 0

    for cat in all_cats:
        s = sotuv.get(cat, {})
        q = qoldiq.get(cat, 0)
        sotuv_qty  = int(s.get('qty', 0))
        sotuv_prof = int(s.get('profit', 0))
        qoldiq_qty = int(q)
        total_sotuv  += sotuv_qty
        total_foyda  += sotuv_prof
        total_qoldiq += qoldiq_qty
        total_stock = sotuv_qty + qoldiq_qty
        obr = int(sotuv_qty / total_stock * 100) if total_stock > 0 else 0
        rows.append([cat[:18], f"{qoldiq_qty}", f"{sotuv_qty}", fmt_money(sotuv_prof), f"{obr}%"])

    total_stock_all = total_sotuv + total_qoldiq
    total_obr = int(total_sotuv / total_stock_all * 100) if total_stock_all > 0 else 0
    rows.append(["JAMI", f"{total_qoldiq}", f"{total_sotuv}", fmt_money(total_foyda), f"{total_obr}%"])

    col_labels = ["Kategoriya", "Qoldiq", "Sotildi", "Foyda", "OBR%"]
    n_rows = len(rows)
    fig_h  = 0.42 * (n_rows + 1) + 1.4
    fig, ax = plt.subplots(figsize=(8, fig_h))
    ax.axis('off')
    fig.text(0.03, 0.98, f"👤  {supplier_name}", fontsize=12, fontweight='bold', va='top', color='#1a1a1a')
    fig.text(0.03, 0.93, f"📅  Oy boshidan: {start_date} — {end_date}", fontsize=10, va='top', color='#555555')

    table = ax.table(cellText=rows, colLabels=col_labels, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 1.6)

    col_widths = [0.30, 0.14, 0.14, 0.24, 0.12]
    for j, w in enumerate(col_widths):
        for i in range(n_rows + 1):
            table[i, j].set_width(w)

    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#dddddd'); cell.set_linewidth(0.5)
        if r == 0:
            cell.set_facecolor('#2C3E50'); cell.set_text_props(color='white', fontweight='bold', fontsize=9)
        elif r == n_rows:
            cell.set_facecolor('#ECF0F1'); cell.set_text_props(fontweight='bold')
        else:
            bg = '#ffffff' if r % 2 == 1 else '#f9f9f9'
            if c == 1:
                try:
                    val = int(rows[r-1][1])
                    if val == 0: cell.set_facecolor('#ffebee'); cell.set_text_props(color='#b71c1c', fontweight='bold')
                    elif val < 50: cell.set_facecolor('#fff3e0'); cell.set_text_props(color='#e65100')
                    else: cell.set_facecolor('#e3f2fd'); cell.set_text_props(color='#0d47a1')
                except: cell.set_facecolor(bg)
            elif c == 3: cell.set_facecolor('#e8f5e9' if r % 2 == 1 else '#f1f8e9'); cell.set_text_props(color='#1b5e20')
            elif c == 4:
                try:
                    obr_val = int(rows[r-1][4].replace('%', ''))
                    if obr_val >= 20: cell.set_facecolor('#d4edda'); cell.set_text_props(color='#155724', fontweight='bold')
                    elif obr_val >= 10: cell.set_facecolor('#fff3cd'); cell.set_text_props(color='#856404', fontweight='bold')
                    else: cell.set_facecolor('#f8d7da'); cell.set_text_props(color='#721c24', fontweight='bold')
                except: cell.set_facecolor(bg)
            else: cell.set_facecolor(bg)

    plt.tight_layout(rect=[0, 0, 1, 0.90])
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf

# --- HANDLERS ---

def register_handlers(dp, bot_instance: Bot, STAT_CACHE_OBJ, OBR_CACHE_OBJ):
    global bot, STAT_CACHE, OBR_CACHE
    bot = bot_instance
    STAT_CACHE = STAT_CACHE_OBJ
    OBR_CACHE = OBR_CACHE_OBJ
    dp.include_router(router)

@router.message(lambda m: m.text == "🔍 Supplier Tahlil" and m.from_user.id == db_manager.config.SUPER_ADMIN_ID)
async def supplier_search_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔍 <b>Supplier qidirish</b>\n\n"
        "Yetkazib beruvchi ismini yozing:"
    )
    await state.set_state(SupplierSearch.waiting_query)

# Menyu tugmalari ro'yxati
ADMIN_BUTTONS = [
    "🔄 Majburiy Yangilash", "📊 Hisobot", "📈 Statistika", "📦 Qoldiqlar", 
    "📅 Import Tahlili", "📊 Asosiy Zakaz (OBR)", "📥 Kelgan Tovar", 
    "🔍 Supplier Tahlil", "⚙️ Sozlamalar", "🟢 Tizimni OCHISH", "🔴 Tizimni YOPISH",
    "✅ VIP Qo'shish", "❌ VIP Olish", "🔒 Bloklash", "🔓 Blokdan ochish"
]

@router.message(SupplierSearch.waiting_query, ~F.text.startswith("/"), ~F.text.in_(ADMIN_BUTTONS))
async def supplier_search_result(message: Message, state: FSMContext):
    query = message.text.strip()
    results = search_suppliers_by_name(query)

    if not results:
        await message.answer("❌ Topilmadi. Boshqa so'z bilan qidiring.\n\nBekor qilish uchun /start bosing.")
        return

    kb = []
    for name in results[:10]:
        uid = str(uuid.uuid4())[:8]
        STAT_CACHE[uid] = ("supplier_name", name)
        kb.append([InlineKeyboardButton(text=f"👤 {name}", callback_data=f"supSel_{uid}")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])

    await message.answer(
        f"🔍 <b>'{query}'</b> bo'yicha {len(results)} ta topildi:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.clear()

@router.callback_query(F.data.startswith("supSel_"))
async def supplier_selected(callback: CallbackQuery, state: FSMContext):
    uid  = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data:
        await callback.answer("⚠️ Eskirgan.", show_alert=True)
        return
    _, supplier_name = data
    msg = await callback.message.edit_text(f"⏳ <b>{supplier_name}</b> yuklanmoqda...")
    sotuv, qoldiq, start_date, end_date = await asyncio.to_thread(get_supplier_sales_report, supplier_name)

    obr_uid = str(uuid.uuid4())[:8]
    STAT_CACHE[obr_uid] = ("sup_obr", supplier_name)
    kb = [
        [InlineKeyboardButton(text="📊 OBR Zakaz tahlili", callback_data=f"supOBR_{obr_uid}")],
        [InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")]
    ]
    if not sotuv and not qoldiq:
        await msg.edit_text(f"⚠️ <b>{supplier_name}</b> uchun sotuv ma'lumoti topilmadi.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return

    chart_buf = await asyncio.to_thread(generate_supplier_table_image, supplier_name, sotuv, qoldiq, start_date, end_date)
    if chart_buf:
        photo = BufferedInputFile(chart_buf.getvalue(), filename="supplier.png")
        await msg.delete()
        await bot.send_photo(chat_id=callback.message.chat.id, photo=photo, caption=f"👤 <b>{supplier_name}</b>\n📅 Oy boshidan: <b>{start_date} — {end_date}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await msg.edit_text(f"❌ Jadval yaratishda xatolik.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("supOBR_"))
async def supplier_obr_click(callback: CallbackQuery):
    uid  = callback.data.split("_")[1]
    data = STAT_CACHE.get(uid)
    if not data:
        await callback.answer("⏳ Eskirgan.", show_alert=True)
        return
    _, supplier_name = data
    await callback.answer()
    msg = await bot.send_message(callback.message.chat.id, f"⏳ <b>{supplier_name}</b> — OBR hisoblanmoqda...\n10-20 soniya kuting.")
    df = await asyncio.to_thread(auto_zakaz.calculate_auto_zakaz, db_manager.engine)
    if df.empty:
        await msg.edit_text("❌ OBR ma'lumoti topilmadi.")
        return
    if 'Поставщик' not in df.columns:
        await msg.edit_text("❌ 'Поставщик' ustuni topilmadi.")
        return
    sup_df = df[df['Поставщик'] == supplier_name].copy()
    if sup_df.empty:
        await msg.edit_text(f"⚠️ <b>{supplier_name}</b> uchun OBR zakaz topilmadi.")
        return
    session_id = str(uuid.uuid4())[:8]
    OBR_CACHE[session_id] = sup_df
    cats = sorted(sup_df['Категория'].unique().tolist())
    kb = []
    for c in cats:
        if not c: continue
        cat_id = str(uuid.uuid4())[:8]
        OBR_CACHE[f"cat_{cat_id}"] = c
        kb.append([InlineKeyboardButton(text=f"📁 {c}", callback_data=f"obrCat_{session_id}_{cat_id}")])
    kb.append([InlineKeyboardButton(text="❌ Yopish", callback_data="del_msg")])
    await msg.edit_text(f"📊 <b>{supplier_name} — OBR ZAKAZ</b>\n\nKategoriyani tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
