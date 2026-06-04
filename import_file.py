import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from dotenv import load_dotenv

import config
import db_manager

load_dotenv()  # .env faylidagi o'zgaruvchilarni yuklaydi

BILLZ_LOGIN    = os.getenv("BILLZ_LOGIN")
BILLZ_PASSWORD = os.getenv("BILLZ_PASSWORD")
SHOP_ID        = os.getenv("SHOP_ID", "Store-1")


# ============================================================
# 1. DAX SEGMENTATSIYASI
# ============================================================
def classify_imported_product(subcategory: str, retail_price: float) -> str:
    if not subcategory:
        return "Boshqa tovarlar"

    sub = str(subcategory).strip()
    price = float(retail_price or 0)

    # ============ ДВОЙКА ============
    if sub == "Двойка":
        if price <= 59900:  return "1. Dvoyka Arzon (60k gacha)"
        if price <= 99900:  return "2. Dvoyka O'rta (100k gacha)"
        if price <= 149900: return "3. Dvoyka Ommabop (150k gacha)"
        return "4. Dvoyka Premium (150k dan yuqori)"

    # ============ ТРОЙКА ============
    elif sub == "Тройка":
        if price <= 99900:  return "1. Troyka Arzon (100k gacha)"
        if price <= 149900: return "2. Troyka O'rta (150k gacha)"
        if price <= 199900: return "3. Troyka Ommabop (200k gacha)"
        return "4. Troyka Premium (200k dan yuqori)"

    # ============ ФИНКА ============
    elif sub == "Финка":
        if price <= 49900: return "1. Finka Arzon (50k gacha)"
        if price <= 79900: return "2. Finka O'rta (80k gacha)"
        return "3. Finka Premium (80k dan yuqori)"

    # ============ ФИНКА С КР/Р ============
    elif sub == "Финка с кр/р":
        if price <= 159900: return "1. Finka kr/r Arzon (160k gacha)"
        if price <= 219900: return "2. Finka kr/r Ommabop (220k gacha)"
        return "3. Finka kr/r Premium (220k dan yuqori)"

    # ============ ФУДБОЛКА / ФУТБОЛКА ============
    elif sub == "Фудболка":
        if price <= 29900: return "1. Fudbolka Arzon (30k gacha)"
        if price <= 44900: return "2. Fudbolka O'rta (45k gacha)"
        return "3. Fudbolka Premium (45k dan yuqori)"
    elif sub == "Футболка":
        if price <= 9900: return "1. Futbolka Arzon (10k gacha)"
        return "2. Futbolka O'rta (10k dan yuqori)"

    # ============ БАСАНОЖКА ============
    elif sub == "Басаножка":
        if price <= 99900:  return "1. Basanojka Arzon (100k gacha)"
        if price <= 134900: return "2. Basanojka O'rta (135k gacha)"
        return "3. Basanojka Premium (135k dan yuqori)"

    # ============ ТАПОЧКА ============
    elif sub == "Тапочка":
        if price <= 39900: return "1. Tapochka Arzon (40k gacha)"
        if price <= 54900: return "2. Tapochka O'rta (55k gacha)"
        return "3. Tapochka Premium (55k dan yuqori)"

    # ============ ШОРТЫ / ШОРТИК ============
    elif sub == "Шорты":
        if price <= 39900: return "1. Shorts Arzon (40k gacha)"
        if price <= 69900: return "2. Shorts O'rta (70k gacha)"
        return "3. Shorts Premium (70k dan yuqori)"
    elif sub == "Шорtik":
        if price <= 19900: return "1. Shortik Arzon (20k gacha)"
        if price <= 34900: return "2. Shortik O'rta (35k gacha)"
        return "3. Shortik Premium (35k dan yuqori)"

    # ============ ПЛАТЬЕ / ПЛАТЬЕ КР/Р ============
    elif sub == "Платье":
        if price <= 69900:  return "1. Platye Arzon (70k gacha)"
        if price <= 119900: return "2. Platye O'rta (120k gacha)"
        return "3. Platye Premium (120k dan yuqori)"
    elif sub == "Платье кр/р":
        if price <= 99900: return "1. Platye kr/r Arzon (100k gacha)"
        return "2. Platye kr/r Premium (100k dan yuqori)"

    # ============ ПИЖАМА ============
    elif sub == "Пижама":
        if price <= 49900: return "1. Pijama Arzon (50k gacha)"
        return "2. Pijama Ommabop (50k dan yuqori)"

    # ============ НАБОР ============
    elif sub == "Набор":
        if price <= 29900: return "1. Nabor Arzon (30k gacha)"
        if price <= 69900: return "2. Nabor O'rta (70k gacha)"
        return "3. Nabor Premium (70k dan yuqori)"

    # ============ РУБАШКА С ДЛ/Р / КР/Р ============
    elif sub == "Рубашка с дл/р":
        if price <= 219900: return "2. Rubashka dl/r O'rta (220k gacha)"
        if price <= 249900: return "3. Rubashka dl/r Sifatli (250k gacha)"
        return "4. Rubashka dl/r Premium (250k dan yuqori)"
    elif sub == "Рубашка с кр/р":
        if price <= 49900: return "1. Rubashka kr/r Arzon (50k gacha)"
        return "2. Rubashka kr/r Premium (50k dan yuqori)"

    # ============ НОСКИ ============
    elif sub == "Носки":
        if price <= 9900: return "1. Noski Arzon (10k gacha)"
        return "2. Noski Ommabop (10k dan yuqori)"

    # ============ КОМБИНЕЗОН ============
    elif sub == "Комбинезон":
        if price <= 39900: return "1. Kombinezon Arzon (40k gacha)"
        if price <= 69900: return "2. Kombinezon O'rta (70k gacha)"
        return "3. Kombinezon Premium (70k dan yuqori)"

    # ============ МАЙКА ============
    elif sub == "Майка":
        if price <= 19900: return "1. Mayka Arzon (20k gacha)"
        return "2. Mayka Premium (20k dan yuqori)"

    # ============ КЕПКА ============
    elif sub == "Кепка":
        if price <= 34900: return "1. Kepka Arzon (35k gacha)"
        return "2. Kepka Premium (35k dan yuqori)"

    # ============ БРЮКИ НА РЕЗИНКЕ / БРЮКИ ============
    elif sub == "Брюки на резинке":
        if price <= 99900:  return "1. Bryuki Arzon (100k gacha)"
        if price <= 119900: return "2. Bryuki O'rta (120k gacha)"
        return "3. Bryuki Premium (120k dan yuqori)"
    elif sub == "Брюки":
        if price <= 84900: return "1. Bryuki Arzon (85k gacha)"
        return "2. Bryuki Premium (85k dan yuqori)"

    # ============ ПАМПЕРС ============
    elif sub == "Памперс":
        if price <= 19900: return "1. Pampers Arzon (20k gacha)"
        if price <= 99900: return "2. Pampers O'rta (100k gacha)"
        return "3. Pampers Premium (100k dan yuqori)"

    # ============ ПОЛЗУНКИ ============
    elif sub == "Ползунки":
        if price <= 9900: return "1. Polzunki Arzon (10k gacha)"
        return "2. Polzunki Ommabop (10k dan yuqori)"

    # ============ СУМКА ============
    elif sub == "Сумка":
        if price <= 49900: return "1. Sumka Arzon (50k gacha)"
        if price <= 99900: return "2. Sumka O'rta (100k gacha)"
        return "3. Sumka Premium (100k dan yuqori)"

    # ============ ШТАН ============
    elif sub == "Штан":
        if price <= 39900: return "1. Shtan Arzon (40k gacha)"
        return "2. Shtan Premium (40k dan yuqori)"

    # ============ КОФТА ============
    elif sub == "Кофта":
        if price <= 44900: return "1. Kofta Arzon (45k gacha)"
        return "2. Kofta Premium (45k dan yuqori)"

    # ============ СКЕЧЕРС ============
    elif sub == "Скечерс":
        if price <= 99900: return "1. Skechers Arzon (100k gacha)"
        return "2. Skechers Premium (100k dan yuqori)"

    # ============ ТУФЛИ ============
    elif sub == "ТУФЛИ":
        if price <= 99900: return "1. Tufli Arzon (100k gacha)"
        return "2. Tufli Premium (100k dan yuqori)"

    # ============ ЮБКА ============
    elif sub == "Юбка":
        if price <= 84900: return "1. Yubka Arzon (85k gacha)"
        return "2. Yubka Premium (85k dan yuqori)"

    # ============ САРАФАН ============
    elif sub == "Сарафан":
        if price <= 134900: return "1. Sarafan Arzon (135k gacha)"
        return "2. Sarafan Premium (135k dan yuqori)"

    # ============ ТРИКО ============
    elif sub == "Трико":
        if price <= 84900: return "1. Triko Arzon (85k gacha)"
        return "2. Triko Premium (85k dan yuqori)"

    # ============ ВКЛАДЫШИ ============
    elif sub == "Вкладыши":
        if price <= 19900: return "1. Vkladyshi Arzon (20k gacha)"
        return "2. Vkladyshi Premium (20k dan yuqori)"

    # ============ САЛФЕТКА ============
    elif sub == "Салфетка":
        if price <= 9900: return "1. Salfetka Arzon (10k gacha)"
        return "2. Salfetka Ommabop (10k dan yuqori)"

    # ============ СЛЮНЯВЧИК ============
    elif sub == "Слюнявчик":
        if price <= 14900: return "1. Slyunyavchik Arzon (15k gacha)"
        return "2. Slyunyavchik Premium (15k dan yuqori)"

    # ============ ПИНЕТКИ ============
    elif sub == "Пинетки":
        if price <= 74900: return "1. Pinetki Arzon (75k gacha)"
        return "2. Pinetki Premium (75k dan yuqori)"

    # ============ BITTA NARXLI TOVARLAR ============
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
    elif sub == "Пlenka":       return "Plenka (24900)"
    elif sub == "Плёнка":       return "Plyonka (30-55k)"
    elif sub == "Пашахона":     return "Pashaxona (59900)"
    elif sub == "Бантик":       return "Bantik (15-25k)"
    elif sub == "Заколка":      return "Zakolka (9900)"
    elif sub == "Подушка":      return "Podushka (25-35k)"
    elif sub == "Расчетный":    return "Raschetny (19900)"
    elif sub == "Обоdok":       return "Obodok (9900)"

    return "Boshqa tovarlar"


# ============================================================
# 2. BAZADA f_importlar JADVALINI TAYYORLASH
# ============================================================
def init_import_db(engine):
    """Import tovarlar keshini saqlash uchun jadval yaratadi."""
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
                dax_group    TEXT
            )
        """))


# ============================================================
# 3. DIRECT API BILAN SINXRONIZATSIYA (Selenium-siz, Tezkor!)
# ============================================================
def sync_imports_by_dates(access_token, engine, start_date_str: str, end_date_str: str):
    """
    Billz API'dan importlarni to'g'ridan-to'g'ri requests orqali tortadi va
    har bir import detallarini product_id bo'yicha katalog bilan solishtiradi.
    """
    init_import_db(engine)
    
    # Tanlangan kunlar oralig'idagi eski kesh ma'lumotlarni o'chiramiz
    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM f_importlar 
            WHERE date(import_date) >= :start AND date(import_date) <= :end
        """), {"start": start_date_str, "end": end_date_str})

    headers = {"Authorization": f"Bearer {access_token}", "accept": "application/json"}
    shops_val = ",".join(config.ALL_SHOPS_IDS) if isinstance(config.ALL_SHOPS_IDS, list) else config.ALL_SHOPS_IDS

    # 1. Importlar ro'yxatini olamiz
    url = "https://api-admin.billz.ai/v2/import"
    params = {
        "limit": 100,
        "page": 1,
        "shops": shops_val,
        "start_date": start_date_str,
        "end_date": end_date_str
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        
        import_list = response.json().get("imports", []) or response.json().get("data", []) or response.json().get("rows", [])
        
        if not import_list:
            print("ℹ️ Ushbu sanalarda importlar topilmadi.")
            return "empty", None

        # 🟢 2. KATALOGNI product_id BO'YICHA TEZKOR QIDIRISH DICT'i 🟢
        cat_df = pd.read_sql('SELECT "product_id", "Подкатегория", "Цвет", "Категория", "Наименование" FROM d_mahsulotlar', engine)
        cat_df['product_id'] = cat_df['product_id'].astype(str).str.strip().str.lower()
        catalog_dict = cat_df.set_index('product_id').to_dict(orient='index')

        records_to_insert = []
        details_blocked = False

        for imp in import_list:
            import_id = imp.get("id") or imp.get("import_id")
            raw_date = imp.get("created_at") or imp.get("import_date") or start_date_str
            import_date_clean = raw_date.split(" ")[0] if raw_date else start_date_str

            # 🟢 3. HAR BIR IMPORT DETALLARINI API ORQALI TORTAMIZ (Ruxsat ochilgani uchun 200 OK qaytadi!) 🟢
            detail_url = f"https://api-admin.billz.ai/v2/import/{import_id}"
            print(f"⏳ {import_id} import detallari API orqali yuklanmoqda...")
            
            try:
                detail_resp = requests.get(detail_url, headers=headers, timeout=30)
                detail_resp.raise_for_status()
                
                detail_data = detail_resp.json()
                imp_detail = detail_data.get("data") or detail_data
                
                # Ichki tovarlarni qidiramiz
                products = imp_detail.get("import_items") or imp_detail.get("products") or imp_detail.get("items") or []
                
                if not products:
                    print(f"⚠️ {import_id} ichida tovarlar topilmadi.")
                    continue
                    
                for p in products:
                    sku = p.get("product_sku") or p.get("sku")
                    p_id = str(p.get("id") or p.get("product_id") or "").strip().lower()
                    
                    qty = float(p.get("measurement_value") or p.get("quantity") or p.get("total_measurement_value") or 0)
                    if qty <= 0:
                        continue
                        
                    retail_p = float(p.get("retail_price") or p.get("price") or 0)
                    supply_p = float(p.get("supply_price") or 0)

                    # product_id orqali d_mahsulotlar dan ma'lumotlarni solishtiramiz [6]
                    cat_info = catalog_dict.get(p_id, {})
                    
                    if cat_info:
                        name     = cat_info.get("Наименование", p.get("name", ""))
                        subcat   = cat_info.get("Подкатегория", "Boshqa tovarlar")
                        color    = cat_info.get("Цвет", "No Color")
                        category = cat_info.get("Категория", "Boshqa")
                    else:
                        name     = p.get("product_name") or p.get("name", "")
                        subcat   = "Boshqa tovarlar"
                        color    = "No Color"
                        category = "Boshqa"

                    # DAX SEGMENTATSIYASI
                    dax_grp = classify_imported_product(subcat, retail_p)

                    records_to_insert.append({
                        "import_id":    import_id,
                        "import_date":  import_date_clean,
                        "shop_id":      SHOP_ID,
                        "artikul":      sku,
                        "name":         name,
                        "category":     category,
                        "subcategory":  subcat,
                        "color":        color,
                        "quantity":     qty,
                        "supply_price": supply_p,
                        "retail_price": retail_p,
                        "dax_group":    dax_grp,
                    })
            except Exception as ex:
                details_blocked = True
                print(f"❌ {import_id} detallarini yuklashda xatolik: {ex}")
                continue

        if records_to_insert:
            df_insert = pd.DataFrame(records_to_insert)
            df_insert.to_sql("f_importlar", engine, if_exists="append", index=False)
            print(f"✅ API orqali {len(df_insert)} ta import qilingan satr f_importlar jadvaliga yozildi!")
            return "dax", None
            
        if import_list and details_blocked:
            return "summary", import_list

        return "empty", None

    except Exception as e:
        print(f"❌ API dan ma'lumot olishda xatolik: {e}")
        return "empty", None


# ============================================================
# 4. DAX GURUHLAR BO'YICHA HISOBOT
# ============================================================
def get_imported_summary_by_dax(engine, start_date_str: str, end_date_str: str) -> dict:
    """
    f_importlar bazasidan tanlangan kunlardagi tovarlarni
    category va dax_group bo'yicha jamlab qaytaradi.
    """
    try:
        query = text("""
            SELECT category, dax_group, SUM(quantity) AS total_qty
            FROM f_importlar
            WHERE date(import_date) >= :start
              AND date(import_date) <= :end
            GROUP BY category, dax_group
            ORDER BY category, total_qty DESC
        """)

        with engine.connect() as conn:
            rows = conn.execute(query, {"start": start_date_str, "end": end_date_str}).fetchall()

        summary = {}
        for cat, dax_grp, qty in rows:
            summary.setdefault(cat, []).append((dax_grp, float(qty)))

        return summary

    except Exception as e:
        print(f"❌ Import xulosasini guruhlashda xatolik: {e}")
        return {}