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
from data_normalizer import normalize_dataframe, safe_normalize, canonical_form


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
        "date": "Дата", "shop_name": "Магазин", "sold_measurement_value": "Кол-во проданных",
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
        df['Размер сетка'] = df['custom_fields'].apply(lambda x: extract_custom_field(x, 'Размер сетка'))
        df = df.drop(columns=['custom_fields'])

    required_columns = [
        "product_id", 'Бренд', 'Материал', 'Вид', 'Категория', 'Наименование', 'Магазин', 'Дата', 'Дата2',
        'Артикул', 'Баркод', 'Подкатегория', 'Акция', 'Модель', 'Кол-во проданных', 'Кол-во возвращенных',
        'Продано за вычетом возвратов', 'Крой', 'Продажи без учета скидки', 'Сумма возвратов',
        'Продажи со скидкой с учетом возвратов', 'Продажи по цене закупки', 'Валовая прибыль', 'Скидка', 'Цена продажи','Размер сетка'
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

    if 'Категория' in df_clean.columns:
        df_clean['Категория'] = df_clean['Категория'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else (x if isinstance(x, str) else None))

    if 'product_id' in df_clean.columns and 'Магазин' in df_clean.columns:
        df_clean['ProductShop_Key'] = df_clean['product_id'].astype(str) + '_' + df_clean['Магазин'].astype(str)

    # --- NORMALIZE: case/space duplikatlarni oldini olish ---
    # Категория, Подкатегория, Вид, Материал, Акция -> canonical_form (case unified)
    # Магазин, Наименование -> faqat safe_normalize
    normalize_dataframe(df_clean, columns=[
        'Категория', 'Подкатегория', 'Вид', 'Материал', 'Акция',
        'Наименование', 'Магазин',
    ])

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
        df['Размер сетка'] = df['product_custom_fields'].apply(lambda x: extract_custom_field(x, 'Размер сетка'))
        df['Дата2'] = df['product_custom_fields'].apply(lambda x: extract_custom_field(x, 'Дата'))
        df = df.drop(columns=['product_custom_fields'])

    # --- SCHEMA GUARD: jadval to'liq DROP + reload bo'lganda ham ustunlar yaratilishi shart ---
    # Agar API javobida 'product_custom_fields' yoki 'last_import' bo'lmasa,
    # bu ustunlar DataFrame'da yo'q bo'lib qoladi, va to_sql ularni jadvalga qo'shmaydi.
    # Shu sababli Дата2 hech qachon saqlanmaydi. Bu yerda ularni majburiy NULL bilan to'ldiramiz.
    for guard_col in ('Подкатегория', 'Материал', 'Вид', 'Пол', 'Размер сетка', 'Дата2', 'last_import'):
        if guard_col not in df.columns:
            df[guard_col] = None

    column_mapping = {
        'product_id': 'product_id', 'categories_path': 'Категория', 'product_name': "Наименование",
        'product_sku': 'Артикул', 'product_barcode': 'Баркод', 'shop_name': 'Магазин',
        'measurement_value': 'Кол-во',
        'supply_price': 'Цена поставки', 'retail_price': 'Цена продажи',
        'estimated_income': 'Сумма прибыли остатков', "product_brand_name": "Бренд",
        'last_import': 'last_import',
    }
    df = df.rename(columns=column_mapping)

    if 'Категория' in df.columns:
        df['Категория'] = df['Категория'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)

    required_columns = [
        'product_id', 'Бренд', 'Категория', 'Материал', 'Вид', "Наименование", 'Дата', 'Дата2', 'last_import',
        'Артикул', 'Баркод', 'Магазин', 'Кол-во', 'Цена поставки', 'Цена продажи', 'Сумма прибыли остатков',
        'Пол', 'Размер сетка',
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

    # --- NORMALIZE: case/space duplikatlarni oldini olish ---
    normalize_dataframe(df_clean, columns=[
        'Категория', 'Подкатегория', 'Вид', 'Материал', 'Пол',
        'Наименование', 'Магазин',
    ])

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
    per_page = 900  # API barqarorligi uchun 1000 dan 900 ga tushirildi
    max_retries = 5 # Qayta urinishlar soni

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
                
                # --- SIZNING LOGIKANGIZ: Agar API 'null' qaytarsa, uni bo'sh ro'yxatga aylantiramiz ---
                raw_data = response.json().get("products")
                items = raw_data if raw_data is not None else []
                
                success = True
                break # Muvaffaqiyatli bo'lsa, retry tsiklidan chiqamiz
            
            except Exception as e:
                print(f"⚠️ Katalog yuklashda xato (Sahifa {page}, Urinish {attempt+1}/{max_retries}): {e}")
                time.sleep(5) # Xato bo'lsa 5 soniya kutamiz
        
        # Agar barcha 5 marta urinishdan keyin ham o'xshamasa
        if not success:
            print(f"❌ Sahifa {page} yuklanmadi. Mavjud ({len(all_products)} ta) ma'lumot bilan davom etamiz.")
            break 

        # Agar serverdan bo'sh ro'yxat kelsa (oxirgi sahifaga yetganda)
        if not items and success:
            break
            
        all_products.extend(items)
        print(f"📄 Sahifa {page}: {len(items)} ta mahsulot yuklandi. (Jami: {len(all_products)})")
        
        # Agar kelgan ma'lumot limitdan kam bo'lsa, demak bu eng oxirgi sahifa
        if len(items) < per_page:
            break
            
        page += 1

    if not all_products:
        print("⚠️ Katalog bo'sh yoki API dan ma'lumot umuman kelmadi.")
        return

    processed_data = []
    
    # --- SIZNING LOGIKANGIZ: Maxsus maydonlarni aniq tozalash ---
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

    _shops_set = set(s.strip() for s in (config.ALL_SHOPS_IDS or '').split(',') if s.strip())

    for p in all_products:
        shop_prices = p.get('shop_prices', [])
        first_shop = shop_prices[0] if shop_prices else {}

        # Bizning do'konlardagi max promo_price (aksiya narxi)
        promo_prices = [
            sp.get('promo_price') or 0
            for sp in shop_prices
            if sp.get('shop_id') in _shops_set
        ]
        promo_price_val = max(promo_prices) if promo_prices else (first_shop.get('promo_price') or 0)
        
        # --- SIZ YOZGAN BARCODE TOZALASH (Matn sifatida) ---
        raw_barcode = str(p.get('barcode', '') or '')
        if raw_barcode.endswith('.0'):
            raw_barcode = raw_barcode[:-2]
        cat_val = (p.get('categories') or [{}])[0].get('name', '') if p.get('categories') else ''
        cat_val = str(cat_val).strip()
        if not cat_val:
            cat_val = 'Boshqa'

        # Podkategoriya bo'sh bo'lsa "Boshqa" deb belgilash
        subcat_val = get_field(p.get('custom_fields'), 'Подкатегория')
        subcat_val = str(subcat_val).strip()
        if not subcat_val:
            subcat_val = 'Boshqa'
   
        rec = {
                    'product_id': str(p.get('id', '')).strip().lower(),
                    'Артикул': p.get('sku', ''), 
                    'Баркод': raw_barcode,
                    'Наименование': p.get('name', ''), 
                    'Бренд': p.get('brand_name', ''),
                    'Категория': (p.get('categories') or [{}])[0].get('name', '') if p.get('categories') else '',
                    'Фото': p.get('main_image_url_full', p.get('main_image_url', '')),
                    'Материал': get_field(p.get('custom_fields'), 'Материал'),
                    'Вид': get_field(p.get('custom_fields'), 'Вид'),
                    'Подкатегория': get_field(p.get('custom_fields'), 'Подкатегория'),
                    'Акция': get_field(p.get('custom_fields'), 'Акция'),
                    'Модель': get_field(p.get('custom_fields'), 'Модель'),
                    'Крой': get_field(p.get('custom_fields'), 'Крой'),
                    'Дата1': get_field(p.get('custom_fields'), 'Дата'),
                    'import_date': get_field(p.get('custom_fields'), 'import_date'),
                    'Цвет': get_field(p.get('custom_fields'), 'Цвет'),
                    'Поставщик': get_supplier_name(p.get("suppliers")),
                    'Цена продажи': first_shop.get('retail_price', 0),
                    'supply_price': first_shop.get('supply_price', 0),
                    'promo_price':  promo_price_val,
                    
                    # 🟢 YANGI QO'SHILGAN USTUNLAR 🟢
                    'Пол': get_field(p.get('custom_fields'), 'Пол'),
                    'Сезон': get_field(p.get('custom_fields'), 'Сезон'),
                    'Размер': get_field(p.get('custom_fields'), 'Размер'),
                    'Размер сетка': get_field(p.get('custom_fields'), 'Размер сетка'),
                    'Описание': p.get('description', ''),
                    'Группа_закупок': get_field(p.get('custom_fields'), 'Группа закупок') # Yoki Billzda qanday nomlangan bo'lsa
                }
        processed_data.append(rec)

    if processed_data:
        d_mahsulotlar = pd.DataFrame(processed_data)
        
        # --- SIZNING LOGIKANGIZ: Barcode larni qat'iy matnga o'tkazish ---
        if 'Баркод' in d_mahsulotlar.columns:
            d_mahsulotlar['Баркод'] = d_mahsulotlar['Баркод'].astype(str)
            d_mahsulotlar['Баркод'] = d_mahsulotlar['Баркод'].replace(['nan', 'None', '<NA>', ''], pd.NA).fillna("")
        
        # Takroriylarni ID bo'yicha olib tashlash
        d_mahsulotlar.drop_duplicates(subset=['product_id'], keep='first', inplace=True)

        # --- NORMALIZE: katalog ustunlarini standartlashtirish ---
        # Kategoriya tipidagi ustunlar canonical formga keladi (case unified),
        # Цвет/Поставщик/Наименование faqat trim/NBSP tozalanadi.
        normalize_dataframe(d_mahsulotlar, columns=[
            'Категория', 'Подкатегория', 'Вид', 'Материал', 'Акция',
            'Пол', 'Сезон',
            'Цвет', 'Поставщик', 'Наименование', 'Бренд',
        ])

        # SQLite ga yozish
        d_mahsulotlar.to_sql("d_mahsulotlar", engine, if_exists="replace", index=False)
        print(f"✅ 'd_mahsulotlar' jadvali {len(d_mahsulotlar)} ta UNIKAL tovar bilan yangilandi.")

        # to_sql(replace) jadval sxemasini qayta yaratadi — qo'shimcha ustunlar qo'shilsin
        for _col_stmt in [
            'ALTER TABLE d_mahsulotlar ADD COLUMN promo_price REAL DEFAULT 0',
        ]:
            try:
                with engine.begin() as conn:
                    conn.execute(text(_col_stmt))
            except Exception:
                pass

        # --- API 500 FALLBACK: tushib qolgan mahsulotlarni avtomatik tiklash ---
        try:
            with engine.connect() as conn:
                missing_count = conn.execute(text("""
                    SELECT COUNT(DISTINCT product_id) FROM (
                        SELECT product_id FROM f_sotuvlar WHERE product_id IS NOT NULL
                        UNION
                        SELECT product_id FROM f_qoldiqlar WHERE product_id IS NOT NULL
                    ) fact
                    WHERE product_id NOT IN (SELECT product_id FROM d_mahsulotlar WHERE product_id IS NOT NULL)
                """)).scalar() or 0
            if missing_count > 0:
                print(f"⚠️ API 500 fallback: {missing_count} ta mahsulot katalogdan tushdi — sync_missing_products ishga tushadi...")
                sync_missing_products(engine)
        except Exception as _fe:
            print(f"⚠️ API fallback tekshirishda xatolik: {_fe}")


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
                    # Oxirgi 2 kunni qayta yuklaymiz (kecha + bugun)
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
                        "limit": 900, "shop_ids": config.ALL_SHOPS_IDS,
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
                print(f"ℹ️ {day_str} uchun API dan ma'lumot kelmadi (Hali yopilmagan).")
                break

            day_chunks.append(process_and_clean_sales_chunk(records))
            if len(records) < 900:
                break
            page += 1

        if day_chunks:
            daily_df = pd.concat(day_chunks, ignore_index=True)
            try:
                with engine.begin() as conn:
                    conn.execute(text(f'''DELETE FROM f_sotuvlar WHERE "Дата" >= '{day_str} 00:00:00' AND "Дата" <= '{day_str} 23:59:59' '''))
            except: pass
            
            try:
                with engine.begin() as conn:
                    daily_df.to_sql("f_sotuvlar", conn, if_exists="append", index=False)
                print(f"✅ {day_str} muvaffaqiyatli yangilandi. ({len(daily_df)} qator)")
            except Exception as e:
                print(f"❌ {day_str} yozish xatosi: {e}")
        else:
            print(f"ℹ️ {day_str} uchun sotuv yo'q.")

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
                    params = {"report_date": day_str, "page": page, "limit": 900, "shop_ids": config.ALL_SHOPS_IDS, "currency": "UZS"}
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
            if len(records) < 900:
                break
            page += 1
        
        if day_chunks:
            daily_df = pd.concat(day_chunks, ignore_index=True)
            try:
                with engine.begin() as conn:
                    # ✅ YANGI KOD:
                    conn.execute(text(f'''DELETE FROM f_qoldiqlar WHERE "Дата" >= '{day_str} 00:00:00' AND "Дата" <= '{day_str} 23:59:59' '''))
            except Exception:
                pass
        
            try:
                with engine.begin() as conn:
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
                CREATE TABLE IF NOT EXISTS "d_Magazinlar" AS 
                SELECT DISTINCT "Магазин" FROM f_qoldiqlar
            """))
            conn.execute(text("""
                INSERT INTO "d_Magazinlar" ("Магазин")
                SELECT DISTINCT "Магазин" FROM f_qoldiqlar
                EXCEPT
                SELECT "Магазин" FROM "d_Magazinlar"
            """))
        print("✅ d_Magazinlar tayyor.")
    except Exception as e:
        print(f"⚠️ d_Magazinlar yangilashda xatolik: {e}")


def sync_missing_products(engine):
    print("\n--- 3.5-QADAM: YETISHMAYOTGAN MAHSULOTLARNI TIKLASH (Missing Products) ---")
    try:
        with engine.connect() as conn:
            d_mahsulotlar = pd.read_sql("SELECT * FROM d_mahsulotlar", conn)
            f_sotuvlar    = pd.read_sql("SELECT * FROM f_sotuvlar", conn)
            f_qoldiqlar   = pd.read_sql("SELECT * FROM f_qoldiqlar", conn)

        def clean_product_id(df):
            if "product_id" in df.columns:
                df["product_id"] = df["product_id"].astype(str).str.strip().str.lower()
            return df

        f_sotuvlar = clean_product_id(f_sotuvlar)
        f_qoldiqlar = clean_product_id(f_qoldiqlar)
        d_mahsulotlar = clean_product_id(d_mahsulotlar)

        # Дата2 (I-05.06.2026) → import_date (DD.MM.YYYY) konvertatsiya
        def dата2_to_import_date(val):
            if not val or not isinstance(val, str):
                return None
            val = val.strip()
            # Harf prefix ni kesib tashlaymiz: "I-05.06.2026" → "05.06.2026"
            date_part = val.split('-', 1)[-1].strip() if '-' in val else val
            if len(date_part) == 10 and date_part[2] == '.' and date_part[5] == '.':
                return date_part
            return None

        # product_id → import_date xaritasini tuzamiz (qoldiq + sotuv)
        def build_import_map(df, date_col='Дата2'):
            if date_col not in df.columns:
                return {}
            sub = df[['product_id', date_col]].dropna(subset=[date_col]).copy()
            sub['_imp'] = sub[date_col].apply(dата2_to_import_date)
            sub = sub.dropna(subset=['_imp']).drop_duplicates(subset=['product_id'], keep='first')
            return dict(zip(sub['product_id'], sub['_imp']))

        # Manba 1: qoldiq Дата2
        id_to_import = build_import_map(f_qoldiqlar)
        # Manba 2: sotuv Дата2
        for pid, imp in build_import_map(f_sotuvlar).items():
            if pid not in id_to_import:
                id_to_import[pid] = imp
        # Manba 3: d_mahsulotlar.Дата1 (API 500 fallback — katalogdan tushib qolganlar uchun)
        for pid, imp in build_import_map(d_mahsulotlar, date_col='Дата1').items():
            if pid not in id_to_import:
                id_to_import[pid] = imp
        # Manba 4: mavjud import_date larni ham xaritaga qo'shamiz (NULL bo'lmaganlar)
        if 'import_date' in d_mahsulotlar.columns:
            existing = d_mahsulotlar[['product_id', 'import_date']].dropna(subset=['import_date']).copy()
            existing = existing[existing['import_date'].astype(str).str.strip().isin(['', 'None', 'nan']) == False]
            for pid, imp in zip(existing['product_id'], existing['import_date']):
                if pid not in id_to_import:
                    id_to_import[pid] = str(imp).strip()

        print(f"📅 Jami import_date manbalar: {len(id_to_import)} ta (qoldiq+sotuv Дата2 + Дата1)")

        fixed_count = 0

        # --- 1) Mavjud NULL import_date larni tuzatish ---
        # Agar import_date ustuni umuman yo'q bo'lsa, uni yaratamiz
        if 'import_date' not in d_mahsulotlar.columns:
            d_mahsulotlar['import_date'] = None

        # NULL/bo'sh import_date qatorlarini topamiz (NaN, None, 'nan', 'None', '' barchasini hisobga olamiz)
        imp_str = d_mahsulotlar['import_date'].astype(str).str.strip().str.lower()
        null_mask = (
            d_mahsulotlar['import_date'].isna() |
            imp_str.isin(['', 'none', 'nan', 'nat', '<na>'])
        )

        # Vektorizatsiyalangan tuzatish (tezroq va aniqroq)
        if null_mask.any() and id_to_import:
            # Faqat NULL bo'lgan va id_to_import xaritasida mavjud bo'lgan qatorlarni tuzatamiz
            has_mapping = d_mahsulotlar['product_id'].isin(id_to_import.keys())
            update_mask = null_mask & has_mapping
            if update_mask.any():
                d_mahsulotlar.loc[update_mask, 'import_date'] = (
                    d_mahsulotlar.loc[update_mask, 'product_id'].map(id_to_import)
                )
                fixed_count = int(update_mask.sum())
                print(f"✅ {fixed_count} ta NULL import_date Дата2 orqali tuzatildi")

        # --- 2) Yetishmayotgan product_id larni qo'shish ---
        sotuv_ids = set(f_sotuvlar["product_id"].dropna())
        qoldiq_ids = set(f_qoldiqlar["product_id"].dropna())
        fact_all_ids = sotuv_ids.union(qoldiq_ids)
        existing_ids = set(d_mahsulotlar["product_id"].dropna())
        missing_ids = list(fact_all_ids - existing_ids)
        print(f"❌ Katalogdan tushib qolgan mahsulotlar: {len(missing_ids)} ta")

        if missing_ids:
            sotuv_missing = f_sotuvlar[f_sotuvlar["product_id"].isin(missing_ids)].copy()
            qoldiq_missing = f_qoldiqlar[f_qoldiqlar["product_id"].isin(missing_ids)].copy()
            combined_missing = pd.concat([sotuv_missing, qoldiq_missing], ignore_index=True)

            missing_rows = pd.DataFrame()
            for col in d_mahsulotlar.columns:
                if col in combined_missing.columns:
                    missing_rows[col] = combined_missing[col]
                else:
                    missing_rows[col] = None

            missing_rows["product_id"] = combined_missing["product_id"]

            # import_date ni Дата2 dan to'g'ridan-to'g'ri o'rnatamiz
            missing_rows['import_date'] = missing_rows['product_id'].map(id_to_import)

            missing_rows = missing_rows.drop_duplicates(subset=["product_id"], keep="first")
            d_mahsulotlar = pd.concat([d_mahsulotlar, missing_rows], ignore_index=True)
            d_mahsulotlar = d_mahsulotlar.drop_duplicates(subset=["product_id"], keep="first")

            d_mahsulotlar.to_sql("d_mahsulotlar", engine, if_exists="replace", index=False)
            print(f"✅ {len(missing_rows)} ta mahsulot Sotuv/Qoldiqdan olinib tiklandi!")

        elif 'import_date' in d_mahsulotlar.columns and fixed_count > 0:
            d_mahsulotlar.to_sql("d_mahsulotlar", engine, if_exists="replace", index=False)
            print(f"✅ d_mahsulotlar yangilandi ({fixed_count} ta import_date tuzatildi).")

        else:
            print("✅ Barcha mahsulotlar joyida, tiklashga hojat yo'q.")

    except Exception as e:
        print(f"⚠️ Tiklashda xatolik: {e}")

def analyze_and_generate_orders(engine):
    print("\n--- 4-QADAM: TAHLIL VA AQLLI GENERATSIYA (Svetofor: Artikul+Rang+Shop) ---")

    try:
        # 1. Jadvallarni o'qish (Eski kod bilan bir xil)
        qoldiq_query = """
        SELECT t1.product_id, t1."Магазин", t1."Кол-во"
        FROM f_qoldiqlar t1
        INNER JOIN (
            SELECT "Магазин", MAX("Дата") as max_date
            FROM f_qoldiqlar
            GROUP BY "Магазин"
        ) t2 ON t1."Магазин" = t2."Магазин" AND t1."Дата" = t2.max_date
        """
        with engine.connect() as conn:
            d_mahsulotlar = pd.read_sql("SELECT * FROM d_mahsulotlar", conn)
            f_sotuvlar    = pd.read_sql('SELECT product_id, "Магазин", "Продано за вычетом возвратов", "Дата" FROM f_sotuvlar', conn)
            f_qoldiqlar   = pd.read_sql(qoldiq_query, conn)

        # Formatlash
        f_sotuvlar['Магазин'] = f_sotuvlar['Магазин'].astype(str).str.strip()
        f_qoldiqlar['Магазин'] = f_qoldiqlar['Магазин'].astype(str).str.strip()
        d_mahsulotlar['product_id'] = d_mahsulotlar['product_id'].astype(str)
        f_sotuvlar['product_id'] = f_sotuvlar['product_id'].astype(str)
        f_qoldiqlar['product_id'] = f_qoldiqlar['product_id'].astype(str)
        f_sotuvlar['sotuv_sanasi'] = pd.to_datetime(f_sotuvlar['Дата'], errors='coerce')
        d_mahsulotlar['Артикул'] = d_mahsulotlar['Артикул'].astype(str).str.strip()
        d_mahsulotlar = d_mahsulotlar[~d_mahsulotlar['Артикул'].str.startswith(('010', '011'))]

        
        date_col = 'import_date' if 'import_date' in d_mahsulotlar.columns else 'Дата1'
        d_mahsulotlar['import_sana_dt'] = pd.to_datetime(d_mahsulotlar[date_col], errors='coerce', dayfirst=True)

        # --- NULL import_date MUAMMOSI ---
        # Ilgari: .fillna(datetime.now()) -> days_passed=0 -> hech qaysi OBR sharti (m1-m4)
        # bajarilmaydi -> zakaz generatsiya bo'lmaydi va hech qanday log yo'q.
        # Yangi yondashuv: NULL import_date — bu "sanasi noma'lum, eski tovar" degani.
        # Shu sababli ularni 3 yil oldingi sentinel sana bilan to'ldiramiz — bu days_passed ni
        # katta qiladi va m1 sharti (kun >= 15) bajariladi, ya'ni tovar zakaz hisobiga kiradi.
        # Qaysi product_id/Артикул NULL bo'lganini diagnostika uchun log qilamiz.
        null_import_mask = d_mahsulotlar['import_sana_dt'].isna()
        null_import_count = int(null_import_mask.sum())
        if null_import_count > 0:
            sentinel_date = datetime.now() - timedelta(days=3 * 365)
            missing = d_mahsulotlar.loc[null_import_mask, ['product_id', 'Артикул']]
            print(f"⚠️ {null_import_count} ta mahsulotda import_date NULL — eski tovar deb sentinel sana ({sentinel_date.strftime('%d.%m.%Y')}) qo'yildi:")
            for _pid, _art in zip(missing['product_id'].tolist()[:50], missing['Артикул'].tolist()[:50]):
                print(f"    NULL import_date: product_id={_pid} | Артикул={_art}")
            if null_import_count > 50:
                print(f"    ... va yana {null_import_count - 50} ta (jami {null_import_count} ta)")
            d_mahsulotlar.loc[null_import_mask, 'import_sana_dt'] = sentinel_date

        d_mahsulotlar['Цвет'] = d_mahsulotlar['Цвет'].fillna('No Color')
        
        settings = db_manager.get_all_settings()

    except Exception as e:
        print(f"❌ Xatolik (O'qishda): {e}")
        return

    # ---------------------------------------------------------
    # 🟢 1-BOSQICH: "YASHIL" REJIM (Avtomatik Tozalash)
    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # 🟢 1-BOSQICH: "YASHIL" REJIM (Artikul + Rang + Magazin)
    # ---------------------------------------------------------
 # ---------------------------------------------------------
    # 🟢 1-BOSQICH: "YASHIL" REJIM (Podkategoriya + Artikul + Rang + Magazin)
    # ---------------------------------------------------------
    try:
        with engine.connect() as conn:
            pending_orders = pd.read_sql("SELECT * FROM generated_orders WHERE status = 'Topdim'", conn)
            conn.close()
        
        if not pending_orders.empty:
            # Hozirgi qoldiqni olish (Endi Podkategoriyani ham qo'shib birlashtiramiz)
            qoldiq_merged = pd.merge(f_qoldiqlar, d_mahsulotlar[['product_id', 'Артикул', 'Цвет', 'Подкатегория']], on='product_id', how='left')
            qoldiq_merged['Цвет'] = qoldiq_merged['Цвет'].fillna('No Color')
            qoldiq_merged['Подкатегория'] = qoldiq_merged['Подкатегория'].fillna('Boshqa').astype(str).str.strip()
            
            ids_to_delete = []
            
            for _, order in pending_orders.iterrows():
                art = str(order['artikul'])
                shop = str(order['shop'])
                sub = str(order['subcategory']).strip()  # Podkategoriyani olamiz
                
                # Rangni tozalash (Sana qismi bo'lsa olib tashlaymiz)
                raw_color = str(order['color'])
                if "(" in raw_color:
                    clean_color = raw_color.split("(")[0].strip()
                else:
                    clean_color = raw_color.strip()

                # Filtrlash: Podkategoriya + Artikul + Shop + Rang bo'yicha moslik
                curr_stock = qoldiq_merged[
                    (qoldiq_merged['Артикул'] == art) & 
                    (qoldiq_merged['Магазин'] == shop) &
                    (qoldiq_merged['Цвет'] == clean_color) &
                    (qoldiq_merged['Подкатегория'] == sub)
                ]['Кол-во'].sum()
                
                init_stock = order['initial_stock'] if order['initial_stock'] is not None else 0
                
                # Agar qoldiq oshgan bo'lsa
                if curr_stock > init_stock:
                    ids_to_delete.append(order['id'])
                    # Logga rangni ham chiqaramiz
                    print(f"✅ KELDI: {art} | {clean_color} | {shop} ({init_stock} -> {curr_stock})")

            if ids_to_delete:
                id_tuple = tuple(ids_to_delete)
                if len(ids_to_delete) == 1:
                    delete_query = text(f"DELETE FROM generated_orders WHERE id = {ids_to_delete[0]}")
                else:
                    delete_query = text(f"DELETE FROM generated_orders WHERE id IN {id_tuple}")
                
                with engine.begin() as conn:
                    conn.execute(delete_query)
                print(f"🗑 {len(ids_to_delete)} ta yetib kelgan zakaz (Rang bo'yicha) o'chirildi.")

    except Exception as e:
        print(f"⚠️ Avto-tozalashda xatolik: {e}")

    # ---------------------------------------------------------
    # 2-BOSQICH: HISOB-KITOB (ESKI KOD 100% O'ZGARISHSIZ)
    # ---------------------------------------------------------
    
    qoldiq_merged = pd.merge(f_qoldiqlar, d_mahsulotlar, on='product_id', how='left')
    qoldiq_merged.dropna(subset=['Артикул'], inplace=True)

    reference_dates = qoldiq_merged.groupby(['Артикул', 'Магазин', 'Цвет'], as_index=False)['import_sana_dt'].max()
    reference_dates.rename(columns={'import_sana_dt': 'max_import_date'}, inplace=True)

    sotuv_merged = pd.merge(f_sotuvlar, d_mahsulotlar[['product_id', 'Артикул', 'Цвет']], on='product_id', how='left')
    sotuv_merged.dropna(subset=['Артикул'], inplace=True)

    sotuv_final = pd.merge(sotuv_merged, reference_dates, on=['Артикул', 'Магазин', 'Цвет'], how='left')
    sotuv_final.dropna(subset=['max_import_date'], inplace=True)
    
    sotuv_filtered = sotuv_final[sotuv_final['sotuv_sanasi'] >= sotuv_final['max_import_date']].copy()
    
    sotuv_grp = sotuv_filtered.groupby(['Артикул', 'Магазин', 'Цвет'], as_index=False)['Продано за вычетом возвратов'].sum()
    sotuv_grp.rename(columns={'Продано за вычетом возвратов': 'Prodano'}, inplace=True)

    agg_rules_qoldiq = {
        'Кол-во': 'sum',
        'import_sana_dt': 'max',
        'supply_price': 'max',
        'Поставщик': 'first',
        'Категория': 'first',
        'Подкатегория': 'first',
        'Фото': 'first'
    }
    
    qoldiq_grp = qoldiq_merged.groupby(['Артикул', 'Магазин', 'Цвет'], as_index=False).agg(agg_rules_qoldiq)
    qoldiq_grp.rename(columns={'Кол-во': 'Hozirgi_Qoldiq'}, inplace=True)

    final_df = pd.merge(qoldiq_grp, sotuv_grp, on=['Артикул', 'Магазин', 'Цвет'], how='left')
    final_df['Prodano'] = final_df['Prodano'].fillna(0)

    max_sana_kalendar = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
    final_df['days_passed'] = (max_sana_kalendar - final_df['import_sana_dt']).dt.days
    final_df['days_passed'] = final_df['days_passed'].clip(lower=0)

    final_df['avg_sales'] = final_df.apply(
        lambda row: row['Prodano'] / (row['days_passed'] if row['days_passed'] > 0 else 1), axis=1
    )

    def calculate_order(row):
        kun = row['days_passed']
        sotuv = row['Prodano']
        qoldiq = row['Hozirgi_Qoldiq']
        avg = row['avg_sales']
        import_soni = sotuv + qoldiq
        if import_soni == 0: return 0
        foiz = (sotuv / import_soni) * 100
        
        if settings.get('m4_min_days', 1) <= kun <= settings.get('m4_max_days', 5):
            if foiz >= settings.get('m4_percentage', 50): return sotuv * 1.0
        if settings.get('m3_min_days', 6) <= kun <= settings.get('m3_max_days', 9):
            if foiz >= settings.get('m3_percentage', 70): return avg * 7 
        if settings.get('m2_min_days', 10) <= kun <= settings.get('m2_max_days', 14):
            if foiz >= settings.get('m2_percentage', 85): return avg * 7
        if settings.get('m1_min_days', 15) <= kun <= settings.get('m1_max_days', 1000):
            if foiz >= settings.get('m1_percentage', 99): return avg * 7
        return 0

    final_df['final_order'] = final_df.apply(calculate_order, axis=1)




    def calculate_smart_quantity(row):
            dona = float(row['final_order'])
            cat = str(row['Категория'])
            
            # Dona hisobida olinadigan kategoriyalar
            dona_cats = ['Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье']
            
            if cat in dona_cats:
                # Agar mayda tovar bo'lsa (Masalan 3.4 chiqsa, 4 dona deb oladi)
                if dona < 1: 
                    return 0 # Juda kichik bo'lsa omaydi
                return math.ceil(dona)
            else:
                # Kiyimlar uchun eski (pochka) logika
                if dona <= 2: return 0      
                if dona <= 5: return 1      
                if dona <= 10: return 2     
                if dona <= 15: return 3     
                if dona <= 20: return 4     
                if dona <= 25: return 5     
                return math.ceil(dona / 5)

    orders = final_df[final_df['final_order'] > 0].copy()
    if orders.empty:
        print("✅ Yangi hisob bo'yicha zakaz yo'q.")
        return

    # Yangi aqlli hisoblash funksiyasini qo'llaymiz
    orders['quantity'] = orders.apply(calculate_smart_quantity, axis=1).astype(int)
    orders = orders[orders['quantity'] > 0].copy()

    orders['sana_str'] = orders['import_sana_dt'].dt.strftime('%d.%m.%Y')
    orders['color'] = orders['Цвет'].astype(str) + " (" + orders['sana_str'] + ")"
    orders['tovar_holati'] = "Shart Bajarildi"

    # ---------------------------------------------------------
    # 🟡 3-BOSQICH: SVETOFOR FILTER (Eski Mantiq bilan)
    # ---------------------------------------------------------
    
    # Bazadagi 'Topdim' statusli zakazlarni olamiz
    with engine.connect() as conn:
        active_orders = pd.read_sql("SELECT * FROM generated_orders WHERE status = 'Topdim'", conn)
    
    rename_map = {
        'Артикул': 'zakaz_id',
        'Поставщик': 'supplier', 'Категория': 'category',
        'Подкатегория': 'subcategory', 'Магазин': 'shop', 'Фото': 'photo',
        'import_sana_dt': 'import_date', 'Hozirgi_Qoldiq': 'hozirgi_qoldiq',
        'Prodano': 'prodano', 'days_passed': 'days_passed',
        'avg_sales': 'ortacha_sotuv', 'final_order': 'kutilyotgan_sotuv',
        'supply_price': 'supply_price'
    }
    
    orders_db = orders.rename(columns=rename_map)
    orders_db['artikul'] = orders_db['zakaz_id']
    orders_db['status'] = 'Kutilmoqda'
    orders_db['created_at'] = datetime.now(TASHKENT_TZ).replace(tzinfo=None).date()
    orders_db['import_date'] = pd.to_datetime(orders_db['import_date']).dt.date
    orders_db['initial_stock'] = orders_db['hozirgi_qoldiq']

    cols = [
        'zakaz_id', 'supplier', 'artikul', 'category', 'subcategory', 'shop', 'color', 'photo',
        'quantity', 'supply_price', 'hozirgi_qoldiq', 'prodano', 'days_passed', 
        'ortacha_sotuv', 'kutilyotgan_sotuv', 'tovar_holati', 'import_date', 'created_at', 'status', 'initial_stock'
    ]
    orders_db = orders_db[[c for c in cols if c in orders_db.columns]]

    orders_to_insert = []
    
    for _, new_row in orders_db.iterrows():
        # Match: Podkategoriya + Artikul + Shop + Color
        match = active_orders[
            (active_orders['artikul'] == new_row['artikul']) & 
            (active_orders['shop'] == new_row['shop']) &
            (active_orders['color'] == new_row['color']) &
            (active_orders['subcategory'].astype(str).str.strip() == str(new_row['subcategory']).strip())
        ]
        
        if not match.empty:
            old_qty = match.iloc[0]['quantity']
            new_qty = new_row['quantity']
            
            # Agar ehtiyoj OSHGAN bo'lsa -> YANGI ZAKAZ
            if new_qty > old_qty:
                orders_to_insert.append(new_row)
            else:
                # Ehtiyoj o'zgarmadi -> BLOK (Sariq qoladi)
                pass
        else:
            # Bazada yo'q -> Yangi Zakaz
            orders_to_insert.append(new_row)

    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM generated_orders WHERE status = 'Kutilmoqda'"))
            
            if orders_to_insert:
                df_to_write = pd.DataFrame(orders_to_insert)
                df_to_write.to_sql("generated_orders", conn, if_exists="append", index=False)
                print(f"✅ BAZA YANGILANDI: {len(df_to_write)} ta yangi zakaz (Filtrlangan).")
            else:
                print("✅ Yangi zakaz yo'q (Hammasi jarayonda).")
                
    except Exception as e:
        print(f"❌ Yozishda xatolik: {e}")

def run_full_update():
    """
    Barcha ma'lumotlarni yangilash jarayonini boshqaradi.
    To'liq PostgreSQL va 'Smart Update' (kunma-kun) rejimida ishlaydi.
    """
    start_time = time.time()
    print(f"\n--- 🚀 MA'LUMOTLARNI TO'LIQ YANGILASH BOSHLANDI: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

    access_token = get_billz_access_token()
    if not access_token:
        print("❌ Yangilash to'xtatildi: Access token olinmadi.")
        return

    try:
        engine = db_manager.engine

        update_catalog(access_token, engine)

        new_token = get_billz_access_token()
        if new_token:
            access_token = new_token
            print("🔑 Token yangilandi (sotuv oldidan).")

        update_sales(access_token, engine)

        new_token = get_billz_access_token()
        if new_token:
            access_token = new_token
            print("🔑 Token yangilandi (qoldiq oldidan).")

        update_stock(access_token, engine)

        # ALTER TABLE'lar update_stock'dan KEYIN ishlashi shart, chunki to'liq DROP'dan keyin
        # jadvallar faqat to_sql() chaqirig'idan keyin yaratiladi. Aks holda "no such table"
        # xatosi yuz beradi va ustunlar qo'shilmaydi. Agar ustun allaqachon mavjud bo'lsa
        # (process_and_clean_stock_chunk schema guard tufayli), ALTER TABLE xato beradi va
        # except bloki uni yutib yuboradi — bu bezarar.
        try:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE f_sotuvlar ADD COLUMN "Размер сетка" TEXT'))
        except Exception: pass
        try:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE f_qoldiqlar ADD COLUMN "Размер сетка" TEXT'))
        except Exception: pass
        try:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE f_qoldiqlar ADD COLUMN "Дата2" TEXT'))
        except Exception: pass
        try:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE f_qoldiqlar ADD COLUMN "last_import" TEXT'))
        except Exception: pass
        
        # MANA SHU QATOR QO'SHILISHI SHART! (Qolib ketgan tovarlarni tiklash uchun)
        sync_missing_products(engine)

        analyze_and_generate_orders(engine)

    except Exception as e:
        print(f"🔥🔥🔥 YANGILASH JARAYONIDA JIDDIY XATOLIK YUZ BERDI: {e}")

    end_time = time.time()
    duration_minutes = (end_time - start_time) / 60
    print(f"\n🏁 --- JARAYON YAKUNLANDI. Umumiy vaqt: {duration_minutes:.2f} daqiqa ---")
    try:
        db_manager.engine.dispose()
    except Exception:
        pass
