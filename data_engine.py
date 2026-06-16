# data_engine.py
import math

from datetime import datetime, timedelta, timezone
from sqlalchemy import inspect,text

import time
import pandas as pd
import requests
import json
import os
import time
import warnings
import src.database.db_manager as db_manager

import config


TASHKENT_TZ = timezone(timedelta(hours=5))
# Pandas'ning keraksiz ogohlantirishlarini o'chirish
warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)


# --- 1-QISM: YORDAMCHI FUNKSIYALAR: MA'LUMOTLARNI TOZALASH ---

def process_and_clean_sales_chunk(chunk_of_records):
    """Sotuvlar haqidagi xom ma'lumotlar qismini tozalab, tayyor DataFrame qaytaradi."""
    if not chunk_of_records:
        return pd.DataFrame()

    df = pd.DataFrame(chunk_of_records)

    rename_cols = {
        "product_id": "product_id", "product_sku": "Артикул", "product_name": "Наименование",
        "categories_path": "Категория", "product_brand_name": "Бренд", "product_barcode": "Баркод",
        "date": "Дата", "shop_name": "Магазин", "sold_measurement_value": "Кол-во проdanных",
        "returned_measurement_value": "Кол-во возвращенных", "net_sold_measurement_value": "Продано за вычетом возвратов",
        "gross_sales": "Продажи без учета скидки", "returned_sales_sum": "Сумма возвратов",
        "net_sales": "Продажи со скидкой с учетом возвратов", "sold_supply_sum": "Продажи по цене закупки",
        "net_profit": "Валовая прибыль", "discount": "Скидка", "sold_with_discount": "Цена продажи"
    }
    df = df.rename(columns=rename_cols)

    def extract_custom_field(custom_fields_list, field_name):
        if isinstance(custom_fields_list, list):
            for field in custom_fields_list:
                if isinstance(field, dict) and field.get('custom_field_name') == field_name:
                    return field.get('custom_field_value')
        return None

    if 'custom_fields' in df.columns:
        df['Материал'] = df['custom_fields'].apply(lambda x: extract_custom_field(x, 'Материал'))
        df['Вид'] = df['custom_fields'].apply(lambda x: extract_custom_field(x, 'Вид'))
        df['Крой'] = df['custom_fields'].apply(lambda x: extract_custom_field(x, 'Крой'))
        df['Дата2'] = df['custom_fields'].apply(lambda x: extract_custom_field(x, 'Дата'))
        df['Акция'] = df['custom_fields'].apply(lambda x: extract_custom_field(x, 'Акция'))
        df['Подкатегория'] = df['custom_fields'].apply(lambda x: extract_custom_field(x, 'Подкатегория'))
        df['Модель'] = df['custom_fields'].apply(lambda x: extract_custom_field(x, 'Модель'))
        df['Размер сетka'] = df['custom_fields'].apply(lambda x: extract_custom_field(x, 'Размер сетка'))
        df = df.drop(columns=['custom_fields'])

    required_columns = [
        "product_id", 'Бренд', 'Материал', 'Вид', 'Категория', 'Наименование', 'Магазин', 'Дата', 'Дата2',
        'Артикул', 'Баркод', 'Подкатегория', 'Акция', 'Модель', 'Кол-во проdanных', 'Кол-во возвращенных',
        'Продано за вычетом возвратов', 'Крой', 'Продажи bez ucheta skidki', 'Сумма возвратов',
        'Продажи so skidkoy s uchetom vozvratov', 'Продажи po tsene zakupki', 'Валовая прибыль', 'Скидка', 'Цена продажи','Размер сетка'
    ]

    existing_columns = [col for col in required_columns if col in df.columns]
    df_clean = df[existing_columns].copy()

    # Bo'sh (blank) qiymatlarni "Boshqa"ga o'tkazish
    if 'Категория' in df_clean.columns:
        df_clean['Категория'] = df_clean['Категория'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else (x if isinstance(x, str) else None))
        df_clean['Категория'] = df_clean['Категория'].fillna('Boshqa').astype(str).str.strip().replace('', 'Boshqa')
    if 'Подкатегория' in df_clean.columns:
        df_clean['Подкатегория'] = df_clean['Подкатегория'].fillna('Boshqa').astype(str).str.strip().replace('', 'Boshqa')

    if 'Дата' in df_clean.columns:
        df_clean['Дата'] = pd.to_datetime(df_clean['Дата'], errors='coerce')

    if 'product_id' in df_clean.columns and 'Магазин' in df_clean.columns:
        df_clean['ProductShop_Key'] = df_clean['product_id'].astype(str) + '_' + df_clean['Магазин'].astype(str)

    return df_clean

def process_and_clean_stock_chunk(chunk_of_records, report_date_str):
    if not chunk_of_records:
        return pd.DataFrame()

    df = pd.DataFrame(chunk_of_records)
    df['Дата'] = pd.to_datetime(report_date_str)

    def extract_custom_field(custom_fields, field_name):
        if isinstance(custom_fields, list):
            for field in custom_fields:
                if isinstance(field, dict) and field.get('custom_field_name') == field_name:
                    return field.get('custom_field_value')
        return None

    if 'product_custom_fields' in df.columns:
        df['Подкатегория'] = df['product_custom_fields'].apply(lambda x: extract_custom_field(x, 'Подкатегория'))
        df['Материал'] = df['product_custom_fields'].apply(lambda x: extract_custom_field(x, 'Материал'))
        df['Вид'] = df['product_custom_fields'].apply(lambda x: extract_custom_field(x, 'Вид'))
        df['Пол'] = df['product_custom_fields'].apply(lambda x: extract_custom_field(x, 'Пол'))
        df['Размер сетka'] = df['product_custom_fields'].apply(lambda x: extract_custom_field(x, 'Размер сетka'))
        df = df.drop(columns=['product_custom_fields'])

    column_mapping = {
        'product_id': 'product_id', 'categories_path': 'Категория', 'product_name': "Наименование",
        'product_sku': 'Артикул', 'product_barcode': 'Баркод', 'shop_name': 'Магазин',
        'measurement_value': 'Кол-во', 
        'supply_price': 'Цена postavki', 'retail_price': 'Цена продажи',
        'estimated_income': 'Сумма pribyli ostatkov', "product_brand_name": "Бренд"
    }
    df = df.rename(columns=column_mapping)

    if 'Категория' in df.columns:
        df['Категория'] = df['Категория'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)

    required_columns = [
        'product_id', 'Бренд', 'Категория', 'Материал', 'Вид', "Наименование", 'Дата', 'Артикул', 'Подкатегория',
        'Баркод', 'Магазин', 'Кол-во', 'Цена postavki', 'Цена продажи', 'Сумма pribyli ostatkov', 'Пол','Размер сетка'
    ]
    existing_columns = [col for col in required_columns if col in df.columns]
    df_clean = df[existing_columns].copy()

    # Bo'sh (blank) qiymatlarni "Boshqa"ga o'tkazish
    if 'Категория' in df_clean.columns:
        df_clean['Категория'] = df_clean['Категория'].fillna('Boshqa').astype(str).str.strip().replace('', 'Boshqa')
    if 'Подкатегория' in df_clean.columns:
        df_clean['Подкатегория'] = df_clean['Подкатегория'].fillna('Boshqa').astype(str).str.strip().replace('', 'Boshqa')

    if 'product_id' in df_clean.columns and 'Магазин' in df_clean.columns:
        df_clean['ProductShop_Key'] = df_clean['product_id'].astype(str) + '_' + df_clean['Магазин'].astype(str)

    return df_clean

def get_billz_access_token():
    url = "https://api-admin.billz.ai/v1/auth/login"
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json={"secret_token": config.BILLZ_SECRET_KEY}, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        print("✅ Billz API uchun yangi access_token olindi.")
        return data["data"]["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"❌ XATOLIK: Billz API tokenini olishda muammo: {e}")
        return None

def update_catalog(access_token, engine):
    print("\n--- 1-QADAM: MAHSULOTLAR KATALOGI TO'LIQ YANGILANMOQDA (FULL RELOAD) ---")
    all_products = []
    page = 1
    per_page = 900
    max_retries = 5

    print("⏳ Billz API dan barcha mahsulotlar yuklanmoqda...")

    while True:
        params = {"limit": per_page, "page": page}
        success = False
        items = []
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    "https://api-admin.billz.ai/v2/products",
                    params=params, 
                    headers={"authorization": f"Bearer {access_token}"}, 
                    timeout=60
                )
                response.raise_for_status()
                raw_data = response.json().get("products")
                items = raw_data if raw_data is not None else []
                success = True
                break
            except Exception as e:
                print(f"⚠️ Katalog yuklashda xato (Sahifa {page}, Urinish {attempt+1}/{max_retries}): {e}")
                time.sleep(5)
        
        if not success:
            print(f"❌ Sahifa {page} yuklanmadi. Mavjud ({len(all_products)} ta) ma'lumot bilan davom etamiz.")
            break 

        if not items and success:
            break
            
        all_products.extend(items)
        print(f"📄 Sahifa {page}: {len(items)} ta mahsulot yuklandi. (Jami: {len(all_products)})")
        
        if len(items) < per_page:
            break
        page += 1

    if not all_products:
        print("⚠️ Katalog bo'sh yoki API dan ma'lumot umuman kelmadi.")
        return

    processed_data = []
    
    def get_field(custom_fields, name):
        for f in custom_fields or []:
            cf_name = f.get('custom_field_name')
            if name == 'import_date' and cf_name == 'Дата':
                value = f.get('custom_field_value', '')
                if isinstance(value, str) and '-' in value:
                    return value.split('-')[-1].strip()
                return value
            if cf_name == name:
                return f.get('custom_field_value', '')
        return ''

    def get_supplier_name(suppliers):
        return suppliers[0].get("name", "") if suppliers else ""

    for p in all_products:
        shop_prices = p.get('shop_prices', [])
        first_shop = shop_prices[0] if shop_prices else {}
        raw_barcode = str(p.get('barcode', '') or '')
        if raw_barcode.endswith('.0'):
            raw_barcode = raw_barcode[:-2]
            
        cat_val = (p.get('categories') or [{}])[0].get('name', '') if p.get('categories') else ''
        cat_val = str(cat_val).strip() or 'Boshqa'

        subcat_val = get_field(p.get('custom_fields'), 'Подкатегория')
        subcat_val = str(subcat_val).strip() or 'Boshqa'
   
        rec = {
            'product_id': str(p.get('id', '')).strip().lower(),
            'Артикул': p.get('sku', ''), 
            'Баркод': raw_barcode,
            'Наименование': p.get('name', ''), 
            'Бренд': p.get('brand_name', ''),
            'Категория': cat_val,
            'Фото': p.get('main_image_url_full', p.get('main_image_url', '')),
            'Материал': get_field(p.get('custom_fields'), 'Материал'),
            'Вид': get_field(p.get('custom_fields'), 'Вид'),
            'Подкатегория': subcat_val,
            'Акция': get_field(p.get('custom_fields'), 'Акция'),
            'Модель': get_field(p.get('custom_fields'), 'Модель'),
            'Крой': get_field(p.get('custom_fields'), 'Крой'),
            'Дата1': get_field(p.get('custom_fields'), 'Дата'),
            'import_date': get_field(p.get('custom_fields'), 'import_date'),
            'Цвет': get_field(p.get('custom_fields'), 'Цвет'),
            'Поставщик': get_supplier_name(p.get("suppliers")),
            'Цена продажи': first_shop.get('retail_price', 0), 
            'supply_price': first_shop.get('supply_price', 0),
            'Пол': get_field(p.get('custom_fields'), 'Пол'),
            'Сезон': get_field(p.get('custom_fields'), 'Сезон'),
            'Размер': get_field(p.get('custom_fields'), 'Размер'),
            'Размер сетка': get_field(p.get('custom_fields'), 'Размер сетка'),
            'Описание': p.get('description', ''),
            'Группа_закупок': get_field(p.get('custom_fields'), 'Группа закупок')
        }
        processed_data.append(rec)

    if processed_data:
        d_mahsulotlar = pd.DataFrame(processed_data)
        if 'Баркод' in d_mahsulotlar.columns:
            d_mahsulotlar['Баркод'] = d_mahsulotlar['Баркод'].astype(str).replace(['nan', 'None', '<NA>', ''], pd.NA).fillna("")
        
        d_mahsulotlar.drop_duplicates(subset=['product_id'], keep='first', inplace=True)
        d_mahsulotlar.to_sql("d_mahsulotlar", engine, if_exists="replace", index=False)
        print(f"✅ 'd_mahsulotlar' jadvali {len(d_mahsulotlar)} ta UNIKAL tovar bilan yangilandi.")


def update_sales(access_token, engine):
    print("\n--- 2-QADAM: SOTUVLARNI YANGILASH (KUNMA-KUN) ---")
    end_date = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
    start_date = end_date - timedelta(days=30)

    try:
        with engine.connect() as conn:
            has_table = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='f_sotuvlar'")).scalar() is not None
            if has_table:
                result = conn.execute(text('SELECT MAX("Дата") FROM f_sotuvlar')).scalar()
                if result:
                    last_date_in_db = pd.to_datetime(result).normalize()
                    print(f"📅 Bazadagi oxirgi sana: {last_date_in_db.strftime('%Y-%m-%d')}")
                    start_date = last_date_in_db - timedelta(days=1)
    except Exception as e:
        print(f"⚠️ Sanani aniqlashda xatolik: {e}. Standart 30 kun olinadi.")

    current_process_date = start_date

    while current_process_date <= end_date:
        day_str = current_process_date.strftime("%Y-%m-%d")
        print(f"⏳ {day_str} uchun ma'lumot olinmoqda...")
        page = 1
        day_chunks = []

        while True:
            success = False
            for attempt in range(5):
                try:
                    params = {
                        "start_date": day_str, "end_date": day_str, "page": page,
                        "limit": 1000, "shop_ids": config.ALL_SHOPS_IDS,
                        "currency": "UZS", "detalization_by_position": "true"
                    }
                    response = requests.get(
                        "https://api-admin.billz.ai/v1/product-general-table",
                        headers={"Authorization": f"Bearer {access_token}"}, params=params, timeout=60
                    )
                    response.raise_for_status()
                    records = response.json().get('products_stats_by_date', [])
                    success = True
                    break
                except Exception as e:
                    print(f"⚠️ Sotuv yuklash xatosi ({day_str}, urinish {attempt+1}/5): {e}")
                    time.sleep(5)
            
            if not success:
                print(f"❌ {day_str} sotuvlari 5 urinishda ham olinmadi.")
                break
            if not records:
                break

            day_chunks.append(process_and_clean_sales_chunk(records))
            if len(records) < 1000:
                break
            page += 1

        if day_chunks:
            daily_df = pd.concat(day_chunks, ignore_index=True)
            try:
                with engine.begin() as conn:
                    conn.execute(text(f'''DELETE FROM f_sotuvlar WHERE "Дата" >= '{day_str} 00:00:00' AND "Дата" <= '{day_str} 23:59:59' '''))
                    daily_df.to_sql("f_sotuvlar", conn, if_exists="append", index=False)
                print(f"✅ {day_str} muvaffaqiyatli yangilandi. ({len(daily_df)} qator)")
            except Exception as e:
                print(f"❌ {day_str} yozish xatosi: {e}")
        current_process_date += timedelta(days=1)

    cutoff_date = (end_date - timedelta(days=31)).strftime("%Y-%m-%d")
    try:
        with engine.begin() as conn:
            conn.execute(text(f'DELETE FROM f_sotuvlar WHERE "Дата" < \'{cutoff_date}\''))
        print(f"🗑 {cutoff_date} dan oldingi eski arxiv tozalandi.")
    except Exception:
        pass
    
def update_stock(access_token, engine):
    print("\n--- 3-QADAM: QOLDIQLARNI YANGILASH (KUNMA-KUN) ---")
    end_date = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
    start_date = end_date - timedelta(days=30)
    
    try:
        with engine.connect() as conn:
            has_table = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='f_qoldiqlar'")).scalar() is not None
            if has_table:
                result = conn.execute(text('SELECT MAX("Дата") FROM f_qoldiqlar')).scalar()
                if result:
                    last_date_in_db = pd.to_datetime(result)
                    print(f"📅 Bazadagi oxirgi qoldiq sanasi: {last_date_in_db.strftime('%Y-%m-%d')}")
                    start_date = last_date_in_db
    except Exception as e:
        pass

    current_process_date = start_date
    
    while current_process_date <= end_date:
        day_str = current_process_date.strftime("%Y-%m-%d")
        print(f"⏳ {day_str} qoldiqlari olinmoqda...")
        day_chunks = []
        page = 1

        while True:
            success = False
            for attempt in range(5):
                try:
                    params = {"report_date": day_str, "page": page, "limit": 1000, "shop_ids": config.ALL_SHOPS_IDS, "currency": "UZS"}
                    response = requests.get(
                        "https://api-admin.billz.ai/v1/stock-report-table",
                        headers={"Authorization": f"Bearer {access_token}"}, params=params, timeout=60
                    )
                    response.raise_for_status()
                    records = response.json().get("rows", [])
                    success = True
                    break
                except Exception as e:
                    print(f"⚠️ Qoldiq yuklash xatosi ({day_str}, urinish {attempt+1}/5): {e}")
                    time.sleep(5)
            
            if not success:
                print(f"❌ {day_str} qoldiqlari 5 urinishda ham olinmadi.")
                break
            if not records:
                break
            
            day_chunks.append(process_and_clean_stock_chunk(records, day_str))
            if len(records) < 1000:
                break
            page += 1
        
        if day_chunks:
            daily_df = pd.concat(day_chunks, ignore_index=True)
            try:
                with engine.begin() as conn:
                    conn.execute(text(f'''DELETE FROM f_qoldiqlar WHERE "Дата" >= '{day_str} 00:00:00' AND "Дата" <= '{day_str} 23:59:59' '''))
                    daily_df.to_sql("f_qoldiqlar", conn, if_exists="append", index=False)
                print(f"✅ {day_str} qoldiq yozildi.")
            except Exception as e:
                print(f"❌ {day_str} qoldiqni bazaga yozishda xatolik: {e}")

        current_process_date += timedelta(days=1)

    cutoff_date = (end_date - timedelta(days=31)).strftime("%Y-%m-%d")
    try:
        with engine.begin() as conn:
            conn.execute(text(f'DELETE FROM f_qoldiqlar WHERE "Дата" < \'{cutoff_date}\''))
        print(f"🗑 {cutoff_date} dan eski qoldiqlar tozalandi.")
    except Exception:
        pass

    try:
        print("🏪 d_Magazinlar jadvali yangilanmoqda...")
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS "d_Magazinlar" ("Магазин" TEXT UNIQUE)
            """))
            conn.execute(text("""
                INSERT OR IGNORE INTO "d_Magazinlar" ("Магазин")
                SELECT DISTINCT "Магазин" FROM f_qoldiqlar
            """))
        print("✅ d_Magazinlar tayyor.")
    except Exception as e:
        print(f"⚠️ d_Magazinlar yangilashda xatolik: {e}")


def sync_missing_products(engine):
    print("\n--- 3.5-QADAM: YETISHMAYOTGAN MAHSULOTLARNI TIKLASH (Missing Products) ---")
    try:
        d_mahsulotlar = pd.read_sql("SELECT * FROM d_mahsulotlar", engine)
        f_sotuvlar = pd.read_sql("SELECT * FROM f_sotuvlar", engine)
        f_qoldiqlar = pd.read_sql("SELECT * FROM f_qoldiqlar", engine)

        def clean_id(df):
            if "product_id" in df.columns:
                df["product_id"] = df["product_id"].astype(str).str.strip().str.lower()
            return df

        f_sotuvlar, f_qoldiqlar, d_mahsulotlar = clean_id(f_sotuvlar), clean_id(f_qoldiqlar), clean_id(d_mahsulotlar)

        fact_ids = set(f_sotuvlar["product_id"].dropna()).union(set(f_qoldiqlar["product_id"].dropna()))
        missing_ids = list(fact_ids - set(d_mahsulotlar["product_id"].dropna()))
        print(f"❌ API xatosi sababli katalogdan tushib qolgan mahsulotlar: {len(missing_ids)} ta")

        if missing_ids:
            combined = pd.concat([f_sotuvlar[f_sotuvlar["product_id"].isin(missing_ids)], f_qoldiqlar[f_qoldiqlar["product_id"].isin(missing_ids)]], ignore_index=True)
            missing_rows = pd.DataFrame(columns=d_mahsulotlar.columns)
            for col in d_mahsulotlar.columns:
                if col in combined.columns: missing_rows[col] = combined[col]
            
            missing_rows = missing_rows.drop_duplicates(subset=["product_id"], keep="first")
            d_mahsulotlar = pd.concat([d_mahsulotlar, missing_rows], ignore_index=True).drop_duplicates(subset=["product_id"], keep="first")
            d_mahsulotlar.to_sql("d_mahsulotlar", engine, if_exists="replace", index=False)
            print(f"✅ {len(missing_rows)} ta mahsulot tiklandi!")
            
    except Exception as e:
        print(f"⚠️ Tiklashda xatolik: {e}")

def analyze_and_generate_orders(engine):
    print("\n--- 4-QADAM: TAHLIL VA AQLLI GENERATSIYA (Svetofor: Artikul+Rang+Shop) ---")
    try:
        d_mahsulotlar = pd.read_sql("SELECT * FROM d_mahsulotlar", engine)
        f_sotuvlar = pd.read_sql('SELECT product_id, "Магазин", "Продано за вычетом возвратов", "Дата" FROM f_sotuvlar', engine)
        qoldiq_query = """
        SELECT t1.product_id, t1."Магазин", t1."Кол-во"
        FROM f_qoldiqlar t1
        INNER JOIN (
            SELECT "Магазин", MAX("Дата") as max_date FROM f_qoldiqlar GROUP BY "Магазин"
        ) t2 ON t1."Магазин" = t2."Магазин" AND t1."Дата" = t2.max_date
        """
        f_qoldiqlar = pd.read_sql(qoldiq_query, engine)

        for df in [f_sotuvlar, f_qoldiqlar, d_mahsulotlar]:
            df['product_id'] = df['product_id'].astype(str).str.strip().lower()
            if 'Магазин' in df.columns: df['Магазин'] = df['Магазин'].astype(str).str.strip()

        d_mahsulotlar = d_mahsulotlar[~d_mahsulotlar['Артикул'].astype(str).str.strip().str.startswith(('010', '011'))]
        
        date_col = 'import_date' if 'import_date' in d_mahsulotlar.columns else 'Дата1'
        d_mahsulotlar['import_sana_dt'] = pd.to_datetime(d_mahsulotlar[date_col], errors='coerce', dayfirst=True).fillna(datetime.now())
        d_mahsulotlar['Цвет'] = d_mahsulotlar['Цвет'].fillna('No Color')
        settings = db_manager.get_all_settings()

    except Exception as e:
        print(f"❌ Xatolik (O'qishda): {e}"); return

    # 🟢 1-BOSQICH: "YASHIL" REJIM
    try:
        pending = pd.read_sql("SELECT * FROM generated_orders WHERE status = 'Topdim'", engine)
        if not pending.empty:
            q_merged = pd.merge(f_qoldiqlar, d_mahsulotlar[['product_id', 'Артикул', 'Цвет', 'Подкатегория']], on='product_id', how='left')
            q_merged['Цвет'] = q_merged['Цвет'].fillna('No Color')
            ids_to_del = []
            for _, order in pending.iterrows():
                curr_stock = q_merged[(q_merged['Артикул'] == str(order['artikul'])) & (q_merged['Магазин'] == str(order['shop'])) & (q_merged['Цвет'] == str(order['color']).split("(")[0].strip()) & (q_merged['Подкатегория'] == str(order['subcategory']))]['Кол-во'].sum()
                if curr_stock > (order['initial_stock'] or 0):
                    ids_to_del.append(order['id'])
            if ids_to_del:
                with engine.begin() as conn:
                    conn.execute(text(f"DELETE FROM generated_orders WHERE id IN {tuple(ids_to_del) if len(ids_to_del)>1 else '('+str(ids_to_del[0])+')'}"))
                print(f"🗑 {len(ids_to_del)} ta kelgan zakaz o'chirildi.")
    except Exception as e: print(f"⚠️ Avto-tozalash xatosi: {e}")

    # 2-BOSQICH: HISOB-KITOB
    q_m = pd.merge(f_qoldiqlar, d_mahsulotlar, on='product_id', how='left').dropna(subset=['Артикул'])
    ref_dates = q_m.groupby(['Артикул', 'Магазин', 'Цвет'], as_index=False)['import_sana_dt'].max().rename(columns={'import_sana_dt': 'max_import_date'})
    s_m = pd.merge(f_sotuvlar, d_mahsulotlar[['product_id', 'Артикул', 'Цвет']], on='product_id', how='left').dropna(subset=['Артикул'])
    s_f = pd.merge(s_m, ref_dates, on=['Артикул', 'Магазин', 'Цвет'], how='left').dropna(subset=['max_import_date'])
    s_f['sotuv_sanasi'] = pd.to_datetime(s_f['Дата'], errors='coerce')
    s_filtered = s_f[s_f['sotuv_sanasi'] >= s_f['max_import_date']].copy()
    s_grp = s_filtered.groupby(['Артикул', 'Магазин', 'Цвет'], as_index=False)['Продано за вычетом возвратов'].sum().rename(columns={'Продано за vychetom vozvratov': 'Prodano'})
    
    q_grp = q_m.groupby(['Артикул', 'Магазин', 'Цвет'], as_index=False).agg({'Кол-во': 'sum', 'import_sana_dt': 'max', 'supply_price': 'max', 'Поставщик': 'first', 'Категория': 'first', 'Подкатегория': 'first', 'Фото': 'first'}).rename(columns={'Кол-во': 'Hozirgi_Qoldiq'})
    
    final_df = pd.merge(q_grp, s_grp, on=['Артикул', 'Магазин', 'Цвет'], how='left').fillna({'Prodano': 0})
    otgan_kunlar = max((datetime.now(TASHKENT_TZ).replace(tzinfo=None) - datetime.now(TASHKENT_TZ).replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)).days, 1)
    final_df['days_passed'] = (datetime.now(TASHKENT_TZ).replace(tzinfo=None) - final_df['import_sana_dt']).dt.days.clip(lower=0)
    final_df['avg_sales'] = final_df['Prodano'] / final_df['days_passed'].replace(0, 1)

    def calc_order(row):
        kun, sotuv, qoldiq, avg = row['days_passed'], row['Prodano'], row['Hozirgi_Qoldiq'], row['avg_sales']
        total = sotuv + qoldiq
        if total == 0: return 0
        p = (sotuv / total) * 100
        if settings.get('m4_min_days', 1) <= kun <= settings.get('m4_max_days', 5) and p >= settings.get('m4_percentage', 50): return sotuv
        if settings.get('m3_min_days', 6) <= kun <= settings.get('m3_max_days', 9) and p >= settings.get('m3_percentage', 70): return avg * 7
        if settings.get('m2_min_days', 10) <= kun <= settings.get('m2_max_days', 14) and p >= settings.get('m2_percentage', 85): return avg * 7
        if settings.get('m1_min_days', 15) <= kun <= settings.get('m1_max_days', 1000) and p >= settings.get('m1_percentage', 99): return avg * 7
        return 0

    final_df['final_order'] = final_df.apply(calc_order, axis=1)

    def smart_qty(row):
        d, cat = float(row['final_order']), str(row['Категория'])
        if cat in ['Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье']: return math.ceil(d) if d >= 1 else 0
        if d <= 2: return 0
        if d <= 5: return 1
        if d <= 10: return 2
        if d <= 15: return 3
        if d <= 20: return 4
        if d <= 25: return 5
        return math.ceil(d / 5)

    orders = final_df[final_df['final_order'] > 0].copy()
    if orders.empty: print("✅ Zakaz yo'q."); return
    orders['quantity'] = orders.apply(smart_qty, axis=1).astype(int)
    orders = orders[orders['quantity'] > 0].copy()
    orders['color'] = orders['Цвет'].astype(str) + " (" + orders['import_sana_dt'].dt.strftime('%d.%m.%Y') + ")"
    orders['status'] = 'Kutilmoqda'
    orders['created_at'] = datetime.now(TASHKENT_TZ).replace(tzinfo=None).date()
    
    # 🟡 3-BOSQICH: SVETOFOR FILTER
    active = pd.read_sql("SELECT * FROM generated_orders WHERE status = 'Topdim'", engine)
    orders_to_ins = []
    for _, r in orders.iterrows():
        match = active[(active['artikul'] == str(r['Артикул'])) & (active['shop'] == str(r['Магазин'])) & (active['color'] == str(r['color'])) & (active['subcategory'] == str(r['Подкатегория']))]
        if match.empty or r['quantity'] > match.iloc[0]['quantity']:
            orders_to_ins.append({'zakaz_id': r['Артикул'], 'supplier': r['Поставщик'], 'artikul': r['Артикул'], 'category': r['Категория'], 'subcategory': r['Подкатегория'], 'shop': r['Магазин'], 'color': r['color'], 'photo': r['Фото'], 'quantity': r['quantity'], 'supply_price': r['supply_price'], 'hozirgi_qoldiq': r['Hozirgi_Qoldiq'], 'prodano': r['Prodano'], 'days_passed': r['days_passed'], 'ortacha_sotuv': r['avg_sales'], 'kutilyotgan_sotuv': r['final_order'], 'tovar_holati': 'Shart Bajarildi', 'import_date': r['import_sana_dt'].date(), 'created_at': r['created_at'], 'status': 'Kutilmoqda', 'initial_stock': r['Hozirgi_Qoldiq']})

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM generated_orders WHERE status = 'Kutilmoqda'"))
        if orders_to_ins: pd.DataFrame(orders_to_ins).to_sql("generated_orders", conn, if_exists="append", index=False); print(f"✅ {len(orders_to_ins)} ta zakaz qo'shildi.")
        else: print("✅ Yangi zakaz yo'q.")

def run_full_update():
    start_time = time.time()
    print(f"\n--- 🚀 YANGILASH BOSHLANDI: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    token = get_billz_access_token()
    if not token: return
    try:
        engine = db_manager.engine
        for t in ['f_sotuvlar', 'f_qoldiqlar']:
            try:
                with engine.begin() as conn: conn.execute(text(f'ALTER TABLE {t} ADD COLUMN "Размер сетка" TEXT'))
            except: pass
        update_catalog(token, engine); update_sales(token, engine); update_stock(token, engine); sync_missing_products(engine); analyze_and_generate_orders(engine)
    except Exception as e: print(f"🔥🔥🔥 XATOLIK: {e}")
    print(f"\n🏁 JARAYON YAKUNLANDI. Vaqt: {(time.time()-start_time)/60:.2f} daqiqa")
