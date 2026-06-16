import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from dotenv import load_dotenv

import config
import src.database.db_manager as db_manager
from src.utils.helpers import classify_imported_product

load_dotenv()

BILLZ_COOKIE       = os.getenv("BILLZ_COOKIE")
BILLZ_PLATFORM_ID  = os.getenv("BILLZ_PLATFORM_ID")

# ============================================================
# 2. BAZADA f_importlar JADVALINI TAYYORLASH
# ============================================================
def init_import_db(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS f_importlar (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                import_id    TEXT,
                import_date  TEXT,
                shop_id      TEXT,
                artikul      TEXT,
                name         TEXT,
                category     TEXT,
                subcategory  TEXT,
                color        TEXT,
                quantity     REAL,
                supply_price REAL,
                retail_price REAL,
                pol          TEXT,
                dax_group    TEXT
            )
        """))
        try:
            conn.execute(text('ALTER TABLE f_importlar ADD COLUMN pol TEXT'))
        except Exception:
            pass


# ============================================================
# 3. SINXRONIZATSIYA — KUNMA-KUN SO'ROV
# ============================================================
def sync_imports_by_dates(access_token, engine, start_date_str: str, end_date_str: str):
    init_import_db(engine)

    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM f_importlar
            WHERE date(import_date) >= :start AND date(import_date) <= :end
        """), {"start": start_date_str, "end": end_date_str})

    if not access_token or not BILLZ_PLATFORM_ID:
        print("❌ access_token yoki BILLZ_PLATFORM_ID topilmadi!")
        return "empty", None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Cookie": BILLZ_COOKIE or "",
        "platform-id": BILLZ_PLATFORM_ID,
        "accept": "application/json, text/plain, */*",
        "accept-language": "en",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        # KUNMA-KUN SO'ROV (API max 20 ta hujjat qaytaradi, kunlik ajratish xavfsizroq)
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt   = datetime.strptime(end_date_str,   "%Y-%m-%d")

        all_docs = []
        current  = start_dt
        while current <= end_dt:
            date_str = current.strftime("%Y-%m-%d")
            # Legacy base URL: https://kinder-kids-integro.billz.ai/api/v2/import
            # Current might be different, let's use the legacy one as it's known to work
            r = requests.get(
                "https://kinder-kids-integro.billz.ai/api/v2/import",
                headers=headers,
                params={"limit": 20, "start_date": date_str, "end_date": date_str},
                timeout=30
            )
            r.raise_for_status()
            docs = r.json().get("imports", [])
            qty  = sum(d.get("total_arrived_measurement_value", 0) for d in docs)
            warn = " ⚠️ LIMIT!" if len(docs) >= 20 else " ✅"
            print(f"  {date_str} → {len(docs):2d} ta hujjat | {qty:.0f} dona{warn}")
            all_docs.extend(docs)
            current += timedelta(days=1)

        if not all_docs:
            print("ℹ️ Tanlangan sanalarda import topilmadi.")
            return "empty", None

        print(f"\n✅ Jami {len(all_docs)} ta hujjat topildi, tovarlar o'qilmoqda...")

        records_to_insert = []

        for doc in all_docs:
            imp_id = doc.get("id")
            if not imp_id:
                continue

            raw_date          = doc.get("created_at") or start_date_str
            import_date_clean = raw_date.split(" ")[0]
            shop_id           = doc.get("shop_id", "")

            detail_page = 1
            while True:
                try:
                    det_resp = requests.get(
                        f"https://kinder-kids-integro.billz.ai/api/v2/import-search/{imp_id}",
                        headers=headers,
                        params={"limit": 500, "page": detail_page},
                        timeout=20
                    )
                    det_resp.raise_for_status()
                    items = det_resp.json().get("items", [])
                    if not items:
                        break

                    for item in items:
                        qty = float(item.get("measurement_value") or 0)
                        if qty <= 0:
                            continue

                        retail_p = float(item.get("retail_price") or 0)
                        supply_p = float(item.get("supply_price") or 0)
                        name_raw = item.get("product_name") or ""
                        sku      = item.get("product_sku") or ""

                        cf_dict = {
                            cf.get("name", ""): cf.get("value", "")
                            for cf in (item.get("product_custom_fields") or [])
                        }
                        subcat   = cf_dict.get("Подкатегория", "Boshqa tovarlar")
                        color    = cf_dict.get("Цвет", "No Color")
                        pol      = cf_dict.get("Пол", "Универсал")

                        p_cats   = item.get("product_categories") or []
                        category = p_cats[0].get("name", "Boshqa") if p_cats else "Boshqa"

                        dax_grp  = classify_imported_product(subcat, retail_p)

                        records_to_insert.append({
                            "import_id":    imp_id,
                            "import_date":  import_date_clean,
                            "shop_id":      shop_id,
                            "artikul":      sku,
                            "name":         name_raw,
                            "category":     category,
                            "subcategory":  subcat,
                            "color":        color,
                            "quantity":     qty,
                            "supply_price": supply_p,
                            "retail_price": retail_p,
                            "pol":          pol,
                            "dax_group":    dax_grp,
                        })

                    if len(items) < 500:
                        break
                    detail_page += 1

                except Exception as ex:
                    print(f"⚠️ {imp_id} hujjati o'qishda xato: {ex}")
                    break

        if records_to_insert:
            df_insert = pd.DataFrame(records_to_insert)
            df_insert.to_sql("f_importlar", engine, if_exists="append", index=False)
            print(f"✅ Jami {len(df_insert)} ta tovar bazaga yozildi!")
            return "dax", None

        return "empty", None

    except Exception as e:
        print(f"❌ Xatolik: {e}")
        return "empty", None


# ============================================================
# 4. KUNLIK BREAKDOWN
# ============================================================
def get_imported_daily_breakdown(engine, start_date_str: str, end_date_str: str) -> list:
    """
    Har bir kun uchun: nechta hujjat va nechta tovar kelgani.
    """
    try:
        query = text("""
            SELECT
                date(import_date)          AS kun,
                COUNT(DISTINCT import_id)  AS hujjat_soni,
                SUM(quantity)              AS tovar_soni
            FROM f_importlar
            WHERE date(import_date) >= :start
              AND date(import_date) <= :end
            GROUP BY date(import_date)
            ORDER BY date(import_date)
        """)
        with engine.connect() as conn:
            rows = conn.execute(query, {"start": start_date_str, "end": end_date_str}).fetchall()
        return [(str(r[0]), int(r[1]), float(r[2])) for r in rows]
    except Exception as e:
        print(f"❌ Kunlik breakdown xatolik: {e}")
        return []


# ============================================================
# 5. ASOSIY HISOBOT — AKSIYA VA ODDIY AJRATILGAN
# ============================================================

def get_imported_summary_by_dax(engine, start_date_str: str, end_date_str: str) -> str:
    try:
        query = text("""
            SELECT artikul, pol, dax_group, SUM(quantity) AS qty
            FROM f_importlar
            WHERE date(import_date) >= :start
              AND date(import_date) <= :end
            GROUP BY artikul, pol, dax_group
            ORDER BY pol, qty DESC
        """)
        with engine.connect() as conn:
            rows = conn.execute(query, {"start": start_date_str, "end": end_date_str}).fetchall()

        def pol_uz(pol_name):
            p = str(pol_name or "Универсал").strip()
            if p == "Мальчики": return "👦 O'g'il bolalar"
            if p == "Девочки":  return "👧 Qiz bolalar"
            if p == "Малыши":   return "👶 Chaqaloqlar"
            return f"✨ {p}"

        oddiy  = {}
        aksiya = {}

        for artikul, pol, dax_grp, qty in rows:
            art    = str(artikul or "").strip()
            is_aks = art.startswith("010") or art.startswith("011")
            bucket = aksiya if is_aks else oddiy
            key    = pol_uz(pol)
            bucket.setdefault(key, {})
            bucket[key][dax_grp] = bucket[key].get(dax_grp, 0) + float(qty)

        # Har bir pol ichida miqdor bo'yicha tartiblash
        for d in (oddiy, aksiya):
            for k in d:
                d[k] = dict(sorted(d[k].items(), key=lambda x: x[1], reverse=True))

        # Kunlik breakdown
        daily = get_imported_daily_breakdown(engine, start_date_str, end_date_str)

        # ── Xabar yig'amiz ──
        msg  = "📥 <b>KELGAN TOVARLAR TAHLILI</b>\n"
        msg += f"📅 <b>{start_date_str} — {end_date_str}</b>\n"

        jami_oddiy  = 0
        jami_aksiya = 0

        # ── ASOSIY TOVARLAR ──
        if oddiy:
            msg += "\n━━━━━━━━━━━━━━━━\n"
            msg += "🏢 <b>ASOSIY TOVARLAR</b>\n"
            for pol_k, items in sorted(oddiy.items()):
                jami = sum(items.values())
                jami_oddiy += jami
                msg += f"\n<b>{pol_k}</b> — jami: <b>{int(jami)} dona</b>\n"
                msg += "<pre>"
                for dax, qty in items.items():
                    dax_short = dax[:28] if len(dax) > 28 else dax
                    msg += f"  {dax_short:<28} {int(qty):>5} dona\n"
                msg += "</pre>"

        # ── AKSIYA TOVARLAR ──
        if aksiya:
            msg += "\n━━━━━━━━━━━━━━━━\n"
            msg += "🎁 <b>AKSIYA TOVARLAR (010/011)</b>\n"
            for pol_k, items in sorted(aksiya.items()):
                jami = sum(items.values())
                jami_aksiya += jami
                msg += f"\n<b>{pol_k}</b> — jami: <b>{int(jami)} dona</b>\n"
                msg += "<pre>"
                for dax, qty in items.items():
                    dax_short = dax[:28] if len(dax) > 28 else dax
                    msg += f"  {dax_short:<28} {int(qty):>5} dona\n"
                msg += "</pre>"
        else:
            msg += "\n━━━━━━━━━━━━━━━━\n"
            msg += "🎁 <b>AKSIYA TOVARLAR:</b> mavjud emas\n"

        # ── KUNLIK TAQSIMOT ──
        if daily:
            msg += "\n━━━━━━━━━━━━━━━━\n"
            msg += "📊 <b>KUNLIK TAQSIMOT</b>\n<pre>"
            for kun, hujjat, tovar in daily:
                warn = "⚠️" if hujjat >= 20 else "✅"
                msg += f"  {kun}  {hujjat:2d} hujjat  {int(tovar):4d} dona  {warn}\n"
            msg += "</pre>"

        # ── YAKUNIY JAMI ──
        msg += "\n━━━━━━━━━━━━━━━━\n"
        msg += f"🏢 Asosiy : <b>{int(jami_oddiy)} dona</b>\n"
        msg += f"🎁 Aksiya  : <b>{int(jami_aksiya)} dona</b>\n"
        msg += f"🚛 <b>JAMI IMPORT: {int(jami_oddiy + jami_aksiya)} dona</b>"

        return msg

    except Exception as e:
        print(f"❌ Hisobot xatolik: {e}")
        return "❌ Hisobot chiqarishda xatolik yuz berdi."
