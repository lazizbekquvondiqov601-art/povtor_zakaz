import math
import numpy as np
import pandas as pd
from datetime import datetime
from src.utils.helpers import classify_imported_product, format_money

def calculate_auto_zakaz(engine) -> pd.DataFrame:
    """Avtomatik zakaz miqdorini hisoblaydi."""
    try:
        d_mahsulotlar = pd.read_sql(
            '''SELECT "product_id", "Артикул", "Наименование", "Категория", "Подкатегория",
                    "Материал", "Вид", "Цена продажи", "Размер сетка", "Пол", "Поставщик"
            FROM d_mahsulotlar''',
            engine
        )
        f_sotuvlar  = pd.read_sql('SELECT "product_id", "Магазин", "Продано za vychetom vozvratov" as sold, "Дата" FROM f_sotuvlar', engine)
        f_qoldiqlar = pd.read_sql('SELECT "product_id", "Магазин", "Кол-во" as qty, "Дата" FROM f_qoldiqlar', engine)

        for df in [d_mahsulotlar, f_sotuvlar, f_qoldiqlar]:
            df['product_id'] = df['product_id'].astype(str).str.strip().str.lower()

        # Aksiya tovarlarini olib tashlash
        d_mahsulotlar['Артикул'] = d_mahsulotlar['Артикул'].astype(str).str.strip()
        d_mahsulotlar = d_mahsulotlar[~d_mahsulotlar['Артикул'].str.startswith(('010', '011'))]

        f_sotuvlar['Дата']  = pd.to_datetime(f_sotuvlar['Дата'],  errors='coerce')
        f_qoldiqlar['Дата'] = pd.to_datetime(f_qoldiqlar['Дата'], errors='coerce')

        oy_boshi = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        f_sotuvlar  = f_sotuvlar[f_sotuvlar['Дата']   >= oy_boshi]
        f_qoldiqlar = f_qoldiqlar[f_qoldiqlar['Дата'] >= oy_boshi]

        d_mahsulotlar['Цена продажи'] = pd.to_numeric(d_mahsulotlar['Цена продажи'], errors='coerce').fillna(0)
        d_mahsulotlar['Real_Sotuv_Segmenti'] = d_mahsulotlar.apply(
            lambda row: classify_imported_product(row['Подкатегория'], row['Цена продажи']), axis=1
        )

        d_mahsulotlar['Материал2'] = d_mahsulotlar['Материал'].apply(
            lambda m: str(m).strip().lower().replace('/', '-') if pd.notna(m) else ''
        )
        d_mahsulotlar['Вид2'] = d_mahsulotlar['Вид'].apply(
            lambda v: 'polo' if str(v).strip().lower() in ['в полоску', 'полоска']
            else (str(v).strip().lower() if pd.notna(v) else '')
        )

        GROUP_KEYS = [
            'Категория', 'Подкатегория', 'Наименование', 'Real_Sotuv_Segmenti',
            'Размер сетка', 'Материал2', 'Вид2', 'Пол'
        ]

        for col in GROUP_KEYS:
            d_mahsulotlar[col] = d_mahsulotlar[col].fillna('').astype(str).str.strip()
            if col in ['Категория', 'Подкатегория']:
                d_mahsulotlar[col] = d_mahsulotlar[col].replace('', 'Boshqa')
        
        d_mahsulotlar['Пол'] = d_mahsulotlar['Пол'].replace({
            '': 'Универсал',
            'Девочек': 'Девочки', 
            'Мальчик': 'Мальчики',
        })
        
        prod_lookup = d_mahsulotlar[['product_id', 'Артикул', 'Поставщик'] + GROUP_KEYS].drop_duplicates('product_id')

        sotuv = pd.merge(f_sotuvlar, prod_lookup, on='product_id', how='inner')
        sotuv_agg = sotuv.groupby(GROUP_KEYS).agg(
            Продано=('sold', 'sum'),
            Sotuv_kunlari=('Дата', 'nunique')
        ).reset_index()

        max_date_per_shop = f_qoldiqlar.groupby('Магазин')['Дата'].transform('max')
        hoz_q     = f_qoldiqlar[f_qoldiqlar['Дата'] == max_date_per_shop]
        hoz_q     = pd.merge(hoz_q, prod_lookup, on='product_id', how='inner')
        hoz_q_agg = hoz_q.groupby(GROUP_KEYS).agg(
            Hozirgi_Qoldiq=('qty', 'sum')
        ).reset_index()

        all_q = pd.merge(f_qoldiqlar, prod_lookup, on='product_id', how='inner')
        all_q = all_q[~all_q['Артикул'].astype(str).str.startswith(('010', '011'))]

        daily_q = all_q.groupby(GROUP_KEYS + ['Дата']).agg(daily_sum=('qty', 'sum')).reset_index()
        daily_q_nonzero = daily_q[daily_q['daily_sum'] > 0]

        ort_q_agg = daily_q_nonzero.groupby(GROUP_KEYS).agg(
            Ortacha_Qoldiq=('daily_sum', 'mean')
        ).reset_index()

        seg_df = pd.concat([sotuv_agg[GROUP_KEYS], hoz_q_agg[GROUP_KEYS]]).drop_duplicates().reset_index(drop=True)

        seg_df = pd.merge(seg_df, prod_lookup[GROUP_KEYS + ['Поставщик']].drop_duplicates(subset=GROUP_KEYS), on=GROUP_KEYS, how='left')
        seg_df = pd.merge(seg_df, sotuv_agg,  on=GROUP_KEYS, how='left')
        seg_df = pd.merge(seg_df, hoz_q_agg,  on=GROUP_KEYS, how='left')
        seg_df = pd.merge(seg_df, ort_q_agg,  on=GROUP_KEYS, how='left')

        numeric_cols = ['Продано', 'Sotuv_kunlari', 'Hozirgi_Qoldiq', 'Ortacha_Qoldiq']
        for col in numeric_cols:
            if col in seg_df.columns:
                seg_df[col] = seg_df[col].fillna(0)
        seg_df['Поставщик'] = seg_df['Поставщик'].fillna('')

        # --- Vectorized Calculation ---
        bugun = datetime.now()
        otgan_kunlar = max((bugun - oy_boshi).days, 1)

        prodano = seg_df['Продано'].values
        hoz_q_v = seg_df['Hozirgi_Qoldiq'].values
        ort_q_v = seg_df['Ortacha_Qoldiq'].values

        kunlik = prodano / otgan_kunlar
        obr    = np.where(ort_q_v > 0, prodano / ort_q_v, 0.0)

        conditions = [obr >= 2.0, obr >= 1.5, obr >= 1.2, obr >= 1.0, obr >= 0.7, obr >= 0.5, obr >= 0.3, obr > 0.0]
        target_days_vals = [15, 15, 12, 12, 10, 10, 5, 5]
        modifier_vals = [1.1, 1.0, 1.0, 0.9, 0.8, 0.75, 0.6, 0.5]

        target_days = np.select(conditions, target_days_vals, default=0).astype(float)
        modifier = np.select(conditions, modifier_vals, default=0.6)

        kerakli_qoldiq = kunlik * target_days * modifier
        xom_zakaz = kerakli_qoldiq - hoz_q_v
        stock_days = np.where(kunlik > 0, hoz_q_v / kunlik, 999.0)

        should_zero = (kunlik == 0) | (stock_days >= target_days) | (xom_zakaz <= 0)
        raw_zakaz = np.where(should_zero, 0.0, xom_zakaz)

        seg_df['Zakaz'] = (np.ceil(raw_zakaz / 5) * 5).astype(int)
        seg_df['OBR %'] = (np.round(obr * 100)).astype(int).astype(str) + '%'

        cols = ['Категория', 'Подкатегория', 'Наименование', 'Real_Sotuv_Segmenti', 'Размер сетка', 'Материал2', 'Вид2', 'Пол', 'Поставщик', 'Zakaz', 'Hozirgi_Qoldiq', 'Продано', 'OBR %', 'Ortacha_Qoldiq']
        result_df = seg_df[cols].copy()

        # Sorting logic
        result_df['Разmer_sort'] = result_df['Размер сетка'].apply(lambda x: int(str(x).split('-')[0]) if '-' in str(x) and str(x).split('-')[0].isdigit() else (int(x) if str(x).isdigit() else 9999))
        result_df = result_df.sort_values(by=['Категория', 'Подкатегория', 'Наименование', 'Real_Sotuv_Segmenti', 'Разmer_sort']).reset_index(drop=True)
        return result_df.drop(columns=['Разmer_sort'])

    except Exception as e:
        print(f"❌ Auto_Zakaz tahlilida xatolik: {e}")
        return pd.DataFrame()
