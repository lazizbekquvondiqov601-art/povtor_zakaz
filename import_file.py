import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from dotenv import load_dotenv

import config
import db_manager

load_dotenv()

BILLZ_BEARER_TOKEN = os.getenv("BILLZ_BEARER_TOKEN")
BILLZ_COOKIE       = os.getenv("BILLZ_COOKIE")
BILLZ_PLATFORM_ID  = os.getenv("BILLZ_PLATFORM_ID")
SHOP_ID            = os.getenv("SHOP_ID", "d81fe35f-e626-491e-bbc1-9d2949324db2")

# ============================================================
# 1. DAX SEGMENTATSIYASI
# ============================================================
def classify_imported_product(subcategory: str, retail_price: float) -> str:
    if not subcategory:
        return "Boshqa tovarlar"

    sub   = str(subcategory).strip()
    price = float(retail_price or 0)

    if sub == "Двойка":
        if price <= 59900:  return "1. Dvoyka Arzon (60k gacha)"
        if price <= 99900:  return "2. Dvoyka O'rta (100k gacha)"
        if price <= 149900: return "3. Dvoyka Ommabop (150k gacha)"
        return "4. Dvoyka Premium (150k dan yuqori)"
    elif sub == "Тройка":
        if price <= 99900:  return "1. Troyka Arzon (100k gacha)"
        if price <= 149900: return "2. Troyka O'rta (150k gacha)"
        if price <= 199900: return "3. Troyka Ommabop (200k gacha)"
        return "4. Troyka Premium (200k dan yuqori)"
    elif sub == "Финка":
        if price <= 49900: return "1. Finka Arzon (50k gacha)"
        if price <= 79900: return "2. Finka O'rta (80k gacha)"
        return "3. Finka Premium (80k dan yuqori)"
    elif sub == "Финка с кр/р":
        if price <= 159900: return "1. Finka kr/r Arzon (160k gacha)"
        if price <= 219900: return "2. Finka kr/r Ommabop (220k gacha)"
        return "3. Finka kr/r Premium (220k dan yuqori)"
    elif sub == "Фудболка":
        if price <= 29900: return "1. Fudbolka Arzon (30k gacha)"
        if price <= 44900: return "2. Fudbolka O'rta (45k gacha)"
        return "3. Fudbolka Premium (45k dan yuqori)"
    elif sub == "Футболка":
        if price <= 9900: return "1. Futbolka Arzon (10k gacha)"
        return "2. Futbolka O'rta (10k dan yuqori)"
    elif sub == "Басаножка":
        if price <= 99900:  return "1. Basanojka Arzon (100k gacha)"
        if price <= 134900: return "2. Basanojka O'rta (135k gacha)"
        return "3. Basanojka Premium (135k dan yuqori)"
    elif sub == "Тапочка":
        if price <= 39900: return "1. Tapochka Arzon (40k gacha)"
        if price <= 54900: return "2. Tapochka O'rta (55k gacha)"
        return "3. Tapochka Premium (55k dan yuqori)"
    elif sub == "Шорты":
        if price <= 39900: return "1. Shorts Arzon (40k gacha)"
        if price <= 69900: return "2. Shorts O'rta (70k gacha)"
        return "3. Shorts Premium (70k dan yuqori)"
    elif sub == "Шортик":
        if price <= 19900: return "1. Shortik Arzon (20k gacha)"
        if price <= 34900: return "2. Shortik O'rta (35k gacha)"
        return "3. Shortik Premium (35k dan yuqori)"
    elif sub == "Платье":
        if price <= 69900:  return "1. Platye Arzon (70k gacha)"
        if price <= 119900: return "2. Platye O'rta (120k gacha)"
        return "3. Platye Premium (120k dan yuqori)"
    elif sub == "Платье кр/р":
        if price <= 99900: return "1. Platye kr/r Arzon (100k gacha)"
        return "2. Platye kr/r Premium (100k dan yuqori)"
    elif sub == "Пижама":
        if price <= 49900: return "1. Pijama Arzon (50k gacha)"
        return "2. Pijama Ommabop (50k dan yuqori)"
    elif sub == "Набор":
        if price <= 29900: return "1. Nabor Arzon (30k gacha)"
        if price <= 69900: return "2. Nabor O'rta (70k gacha)"
        return "3. Nabor Premium (70k dan yuqori)"
    elif sub == "Рубашка с дл/р":
        if price <= 219900: return "2. Rubashka dl/r O'rta (220k gacha)"
        if price <= 249900: return "3. Rubashka dl/r Sifatli (250k gacha)"
        return "4. Rubashka dl/r Premium (250k dan yuqori)"
    elif sub == "Рубашка с кр/р":
        if price <= 49900: return "1. Rubashka kr/r Arzon (50k gacha)"
        return "2. Rubashka kr/r Premium (50k dan yuqori)"
    elif sub == "Носки":
        if price <= 9900: return "1. Noski Arzon (10k gacha)"
        return "2. Noski Ommabop (10k dan yuqori)"
    elif sub == "Комбинезон":
        if price <= 39900: return "1. Kombinezon Arzon (40k gacha)"
        if price <= 69900: return "2. Kombinezon O'rta (70k gacha)"
        return "3. Kombinezon Premium (70k dan yuqori)"
    elif sub == "Майка":
        if price <= 19900: return "1. Mayka Arzon (20k gacha)"
        return "2. Mayka Premium (20k dan yuqori)"
    elif sub == "Кепка":
        if price <= 34900: return "1. Kepka Arzon (35k gacha)"
        return "2. Kepka Premium (35k dan yuqori)"
    elif sub == "Брюки на резинке":
        if price <= 99900:  return "1. Bryuki Arzon (100k gacha)"
        if price <= 119900: return "2. Bryuki O'rta (120k gacha)"
        return "3. Bryuki Premium (120k dan yuqori)"
    elif sub == "Брюки":
        if price <= 84900: return "1. Bryuki Arzon (85k gacha)"
        return "2. Bryuki Premium (85k dan yuqori)"
    elif sub == "Памперс":
        if price <= 19900: return "1. Pampers Arzon (20k gacha)"
        if price <= 99900: return "2. Pampers O'rta (100k gacha)"
        return "3. Pampers Premium (100k dan yuqori)"
    elif sub == "Ползунки":
        if price <= 9900: return "1. Polzunki Arzon (10k gacha)"
        return "2. Polzunki Ommabop (10k dan yuqori)"
    elif sub == "Сумка":
        if price <= 49900: return "1. Sumka Arzon (50k gacha)"
        if price <= 99900: return "2. Sumka O'rta (100k gacha)"
        return "3. Sumka Premium (100k dan yuqori)"
    elif sub == "Штан":
        if price <= 39900: return "1. Shtan Arzon (40k gacha)"
        return "2. Shtan Premium (40k dan yuqori)"
    elif sub == "Кофта":
        if price <= 44900: return "1. Kofta Arzon (45k gacha)"
        return "2. Kofta Premium (45k dan yuqori)"
    elif sub == "Скечерс":
        if price <= 99900: return "1. Skechers Arzon (100k gacha)"
        return "2. Skechers Premium (100k dan yuqori)"
    elif sub == "Туфли":
        if price <= 99900: return "1. Tufli Arzon (100k gacha)"
        return "2. Tufli Premium (100k dan yuqori)"
    elif sub == "ЮБКА":
        if price <= 84900: return "1. Yubka Arzon (85k gacha)"
        return "2. Yubka Premium (85k dan yuqori)"
    elif sub == "Сарафан":
        if price <= 134900: return "1. Sarafan Arzon (135k gacha)"
        return "2. Sarafan Premium (135k dan yuqori)"
    elif sub == "Трико":
        if price <= 84900: return "1. Triko Arzon (85k gacha)"
        return "2. Triko Premium (85k dan yuqori)"
    elif sub == "Вкладыши":
        if price <= 19900: return "1. Vkladyshi Arzon (20k gacha)"
        return "2. Vkladyshi Premium (20k dan yuqori)"
    elif sub == "Салфетка":
        if price <= 9900: return "1. Salfetka Arzon (10k gacha)"
        return "2. Salfetka Ommabop (10k dan yuqori)"
    elif sub == "Слюнявчик":
        if price <= 14900: return "1. Slyunyavchik Arzon (15k gacha)"
        return "2. Slyunyavchik Premium (15k dan yuqori)"
    elif sub == "Пинетки":
        if price <= 74900: return "1. Pinetki Arzon (75k gacha)"
        return "2. Pinetki Premium (75k dan yuqori)"
    elif sub == "Боди с кр/р":  return "Bodi kr/r (14900)"
    elif sub == "Трусы":        return "Trusy (10000)"
    elif sub == "Ласина":       return "Lasina (19900)"
    elif sub == "Шляпа":        return "Shlyapa (19900)"
    elif sub == "Панама":       return "Panama (35-40k)"
    elif sub == "Распашонка":   return "Raspashonka (9900)"
    elif sub == "Чепчик":       return "Chepchik (4900)"
    elif sub == "Очки":         return "Oki (14900)"
    elif sub == "Плед":         return "Pled (69900)"
    elif sub == "Кленка":       return "Klenka (10-15k)"
    elif sub == "Банданка":     return "Bandanka (14900)"
    elif sub == "Мыло":         return "Mylo (4900)"
    elif sub == "Шампун":       return "Shampun (9900)"
    elif sub == "Пленка":       return "Plenka (24900)"
    elif sub == "Плёнка":       return "Plyonka (30-55k)"
    elif sub == "Пашахона":     return "Pashaxona (59900)"
    elif sub == "Бантик":       return "Bantik (15-25k)"
    elif sub == "Заколка":      return "Zakolka (9900)"
    elif sub == "Подушка":      return "Podushka (25-35k)"
    elif sub == "Расчетный":    return "Raschetny (19900)"
    elif sub == "Ободок":       return "Obodok (9900)"

    return "Boshqa tovarlar"


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
def sync_imports_by_dates(access_token_not_used, engine, start_date_str: str, end_date_str: str):
    init_import_db(engine)

    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM f_importlar
            WHERE date(import_date) >= :start AND date(import_date) <= :end
        """), {"start": start_date_str, "end": end_date_str})

    if not BILLZ_BEARER_TOKEN or not BILLZ_PLATFORM_ID:
        print("❌ .env faylida BILLZ_BEARER_TOKEN yoki BILLZ_PLATFORM_ID topilmadi!")
        return "empty", None

    headers = {
        "Authorization": f"Bearer {BILLZ_BEARER_TOKEN}",
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