import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import src.database.db_manager as db_manager

# Kategoriya guruhlari — tugma filterlari uchun
GROUPS_MAP = {
    'Tops':    ('Верхняя одежда', 'Комплект', 'Плечевые одежды'),
    'Bottoms': ('Поясные одежды',),
    'Shoes':   ('Обувь',),
    'Newborn': ('Новорождённый',),
    'Others':  ('Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье'),
}
# Tugma yozuvlari — o'zbekcha label
GROUPS_LABELS = {
    'Tops':    'Ust kiyimlar',
    'Bottoms': 'Shim/Yubka',
    'Shoes':   'Oyoq kiyim',
    'Newborn': 'Chaqaloqlar',
    'Others':  'Boshqalar',
}
# "Dona" da o'lchanadigan kategoriyalar (qolganlari "pochka")
DONA_CATS = {'Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье'}


def _get_settings():
    """settings jadvalidan barcha qoidalarni dict ko'rinishida olib keladi."""
    session = db_manager.Session()
    try:
        rows = session.execute(text("SELECT rule_name, rule_value FROM settings")).fetchall()
        return {r[0]: float(r[1] or 0) for r in rows}
    except Exception:
        return {}
    finally:
        session.close()


def _classify(status, days):
    """Status va kunlar soniga qarab kartochka rangini aniqlaydi."""
    if status == 'Topdim' and days >= 3:
        return 'red'      # Kechikkan — 3 kundan ortiq yo'lda
    if status == 'Topdim':
        return 'yellow'   # Yo'lda — yangi topilgan
    if status == 'Kutilmoqda':
        return 'white'    # Yangi — hali kutilyapti
    return 'other'


@login_required
def import_tahlil_main(request):
    """Import Tahlili — buyurtma tahlili sahifasi."""
    settings = _get_settings()

    # Qoida diapazoni — filter tugmalari uchun
    rules = []
    for i in [4, 3, 2, 1]:
        mn = int(settings.get(f'm{i}_min_days', 0))
        mx = int(settings.get(f'm{i}_max_days', 0))
        if mx > 0:
            rules.append({'num': i, 'min': mn, 'max': mx})

    # GET parametrlarni o'qiymiz
    group        = request.GET.get('group', '')
    min_day      = request.GET.get('min_day', '')
    max_day      = request.GET.get('max_day', '')
    status_filter = request.GET.get('status', '')

    # WHERE sharti — faqat "Kutilmoqda" va "Topdim" statusli buyurtmalar
    where_parts = ["status IN ('Kutilmoqda', 'Topdim')"]
    params = {}

    # Kategoriya guruhi bo'yicha filter
    if group and group in GROUPS_MAP:
        placeholders = ', '.join(f':gc{i}' for i in range(len(GROUPS_MAP[group])))
        where_parts.append(f"category IN ({placeholders})")
        for i, v in enumerate(GROUPS_MAP[group]):
            params[f'gc{i}'] = v

    # Kunlar diapazoni bo'yicha filter
    if min_day and max_day:
        where_parts.append("CAST(days_passed AS INTEGER) >= :mn AND CAST(days_passed AS INTEGER) <= :mx")
        params['mn'] = int(min_day)
        params['mx'] = int(max_day)

    # Yakuniy SQL — supplier, subcategory, artikul tartibida
    sql = text(
        "SELECT * FROM generated_orders WHERE "
        + ' AND '.join(where_parts)
        + " ORDER BY supplier, subcategory, artikul"
    )

    try:
        df = pd.read_sql(sql, db_manager.engine, params=params)
    except Exception as e:
        # Xatolikni konsolga chiqaramiz, sahifa bo'sh ko'rinadi
        print(f"[import_tahlil] query error: {e}")
        df = pd.DataFrame()

    artikuls = []
    if not df.empty:
        # Har bir satrga status klassini qo'shamiz
        df['_status_class'] = df.apply(
            lambda r: _classify(str(r.get('status', '')), int(r.get('days_passed', 0) or 0)),
            axis=1
        )
        # Status filter — agar tanlangan bo'lsa
        if status_filter in ('red', 'yellow', 'white'):
            df = df[df['_status_class'] == status_filter]

        # Artikul bo'yicha guruhlash: bitta artikul — bitta karta
        for (supplier, subcat, art), gdf in df.groupby(['supplier', 'subcategory', 'artikul']):
            first = gdf.iloc[0]
            cat   = str(first.get('category', '') or '')
            unit  = 'dona' if cat.strip() in DONA_CATS else 'pochka'
            sc    = str(first.get('_status_class', 'white'))
            days  = int(first.get('days_passed', 0) or 0)

            # Narxni chiroyli formatlash: 12 345
            price = first.get('supply_price', 0)
            try:    price_str = f"{float(price):,.0f}".replace(',', ' ')
            except: price_str = '0'

            # Shop bo'yicha ichki guruhlash + rang bo'yicha yig'indi
            shops = []
            for shop, sdf in gdf.groupby('shop'):
                agg = (
                    sdf.groupby('color', as_index=False)
                    .agg(quantity=('quantity', 'sum'),
                         hozirgi_qoldiq=('hozirgi_qoldiq', 'sum'),
                         prodano=('prodano', 'sum'))
                )
                colors = [
                    {
                        'color':  row['color'],
                        'qty':    int(row['quantity']),
                        'qoldiq': int(float(row.get('hozirgi_qoldiq', 0) or 0)),
                        'sotuv':  int(float(row.get('prodano', 0) or 0)),
                        'unit':   unit,
                    }
                    for _, row in agg.iterrows()
                ]
                shops.append({'shop': shop, 'colors': colors})

            total_qty = int(gdf['quantity'].sum())

            artikuls.append({
                'artikul':    art,
                'subcategory': subcat,
                'supplier':   supplier,
                'category':   cat,
                'status':     sc,
                'days':       days,
                'photo':      str(first.get('photo', '') or ''),
                'price_str':  price_str,
                'total_qty':  total_qty,
                'unit':       unit,
                'shops':      shops,
            })

    # Statistika — yuqori panel uchun
    stats = {
        'total':  len(artikuls),
        'red':    sum(1 for a in artikuls if a['status'] == 'red'),
        'yellow': sum(1 for a in artikuls if a['status'] == 'yellow'),
        'white':  sum(1 for a in artikuls if a['status'] == 'white'),
    }

    return render(request, 'import_tahlil/main.html', {
        'artikuls':       artikuls,
        'rules':          rules,
        'groups_labels':  GROUPS_LABELS,
        'selected_group': group,
        'selected_min':   min_day,
        'selected_max':   max_day,
        'selected_status': status_filter,
        'stats':          stats,
    })
