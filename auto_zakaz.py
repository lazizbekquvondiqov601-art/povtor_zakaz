import math
import numpy as np
import pandas as pd
from datetime import datetime

def classify_imported_product(subcategory: str, retail_price: float) -> str:
    if not subcategory: return "Boshqa tovarlar"
    sub = str(subcategory).strip()
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
    elif sub == "Кlenka":       return "Klenka (10-15k)"
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
    elif sub == "Обоdok":       return "Obodok (9900)"

    return "Boshqa tovarlar"


def calculate_auto_zakaz(engine) -> pd.DataFrame:
    try:
        d_mahsulotlar = pd.read_sql(
            '''SELECT "product_id", "Артикул", "Наименование", "Категория", "Подкатегория",
                    "Материал", "Вид", "Цена продажи", "Размер сетка", "Пол"
            FROM d_mahsulotlar''',
            engine
        )
        f_sotuvlar  = pd.read_sql('SELECT "product_id", "Магазин", "Продано за вычетом возвратов", "Дата" FROM f_sotuvlar', engine)
        f_qoldiqlar = pd.read_sql('SELECT "product_id", "Магазин", "Кол-во", "Дата" FROM f_qoldiqlar', engine)

        for df in [d_mahsulotlar, f_sotuvlar, f_qoldiqlar]:
            df['product_id'] = df['product_id'].astype(str).str.strip().str.lower()

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
        d_mahsulotlar = d_mahsulotlar[d_mahsulotlar['Real_Sotuv_Segmenti'] != "Boshqa tovarlar"]

        d_mahsulotlar['Материал2'] = d_mahsulotlar['Материал'].apply(
            lambda m: str(m).strip().lower().replace('/', '-') if pd.notna(m) else ''
        )
        d_mahsulotlar['Вид2'] = d_mahsulotlar['Вид'].apply(
            lambda v: 'полоска' if str(v).strip().lower() in ['в полоску', 'полоска']
            else (str(v).strip().lower() if pd.notna(v) else '')
        )

        GROUP_KEYS = ['Категория', 'Подкатегория', 'Наименование', 'Real_Sotuv_Segmenti',
                      'Размер сетка', 'Материал2', 'Вид2', 'Пол']

        for col in GROUP_KEYS:
            d_mahsulotlar[col] = d_mahsulotlar[col].fillna('').astype(str).str.strip()

        prod_lookup = d_mahsulotlar[['product_id'] + GROUP_KEYS].drop_duplicates('product_id')

        sotuv     = pd.merge(f_sotuvlar,  prod_lookup, on='product_id', how='inner')
        sotuv_agg = sotuv.groupby(GROUP_KEYS).agg(
            Продано=('Продано за вычетом возвратов', 'sum'),
            Sotuv_kunlari=('Дата', 'nunique')
        ).reset_index()

        max_date_per_shop = f_qoldiqlar.groupby('Магазин')['Дата'].transform('max')
        hoz_q     = f_qoldiqlar[f_qoldiqlar['Дата'] == max_date_per_shop]
        hoz_q     = pd.merge(hoz_q, prod_lookup, on='product_id', how='inner')
        hoz_q_agg = hoz_q.groupby(GROUP_KEYS).agg(
            Hozirgi_Qoldiq=('Кол-во', 'sum')
        ).reset_index()

        oylik_qoldiqlar = f_qoldiqlar[f_qoldiqlar['Дата'] >= oy_boshi]
        all_q    = pd.merge(oylik_qoldiqlar, prod_lookup, on='product_id', how='inner')
        daily_q  = all_q.groupby(GROUP_KEYS + ['Дата']).agg(daily_sum=('Кол-во', 'sum')).reset_index()
        ort_q_agg = daily_q.groupby(GROUP_KEYS).agg(
            Ortacha_Qoldiq=('daily_sum', 'mean')
        ).reset_index()

        seg_df = prod_lookup[GROUP_KEYS].drop_duplicates()
        seg_df = pd.merge(seg_df, sotuv_agg,  on=GROUP_KEYS, how='left')
        seg_df = pd.merge(seg_df, hoz_q_agg,  on=GROUP_KEYS, how='left')
        seg_df = pd.merge(seg_df, ort_q_agg,  on=GROUP_KEYS, how='left')
        seg_df.fillna(0, inplace=True)

        # --- VECTORIZED apply_dax (apply() o'rniga) ---
        bugun       = datetime.now()
        oy_boshi_dt = bugun.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        otgan_kunlar = max((bugun - oy_boshi_dt).days, 1)

        prodano = seg_df['Продано'].astype(float).values
        hoz_q_v = seg_df['Hozirgi_Qoldiq'].astype(float).values
        ort_q_v = seg_df['Ortacha_Qoldiq'].astype(float).values

        kunlik = prodano / otgan_kunlar
        obr    = np.where(ort_q_v > 0, prodano / ort_q_v, 0.0)

        conditions = [
            obr >= 2.0,
            obr >= 1.5,
            obr >= 1.2,
            obr >= 1.0,
            obr >= 0.7,
            obr >= 0.5,
            obr >= 0.3,
            obr >  0.0,
        ]
        target_days_vals = [25, 22, 18, 18, 14, 14,  7,  7]
        modifier_vals    = [1.50, 1.35, 1.20, 1.10, 1.00, 0.90, 0.75, 0.60]

        target_days = np.select(conditions, target_days_vals, default=0).astype(float)
        modifier    = np.select(conditions, modifier_vals,    default=0.60)

        kerakli_qoldiq = kunlik * target_days * modifier
        xom_zakaz      = kerakli_qoldiq - hoz_q_v
        stock_days     = np.where(kunlik > 0, hoz_q_v / kunlik, 999.0)

        should_zero = (kunlik == 0) | (stock_days >= target_days) | (xom_zakaz <= 0)
        raw_zakaz   = np.where(should_zero, 0.0, xom_zakaz)

        seg_df['Zakaz'] = (np.round(raw_zakaz / 10) * 10).astype(int)
        seg_df['OBR %'] = (np.round(obr * 100)).astype(int).astype(str) + '%'
        # --- VECTORIZED tugadi ---

        cols = [
            'Категория', 'Подкатегория', 'Наименование', 'Real_Sotuv_Segmenti',
            'Размер сетка', 'Материал2', 'Вид2', 'Пол',
            'Zakaz', 'Hozirgi_Qoldiq', 'Продано', 'OBR %', 'Ortacha_Qoldiq'
        ]
        result_df = seg_df[cols].copy()

        result_df['Zakaz']          = result_df['Zakaz'].astype(int)
        result_df['Hozirgi_Qoldiq'] = result_df['Hozirgi_Qoldiq'].astype(int)
        result_df['Продано']        = result_df['Продано'].astype(int)

        result_df['Размер сетка'] = result_df['Размер сетка'].astype(str).fillna('').str.strip()
        result_df['Размер_sort_key'] = result_df['Размер сетка'].apply(
            lambda x: int(x.split('-')[0]) if '-' in x and x.split('-')[0].isdigit()
            else (int(x) if x.isdigit() else 9999)
        )
        result_df = result_df.sort_values(
            by=['Категория', 'Подкатегория', 'Наименование', 'Real_Sotuv_Segmenti', 'Размер_sort_key'],
            ascending=True
        ).reset_index(drop=True)
        result_df = result_df.drop(columns=['Размер_sort_key'])

        return result_df

    except Exception as e:
        print(f"❌ Auto_Zakaz tahlilida xatolik: {e}")
        return pd.DataFrame()