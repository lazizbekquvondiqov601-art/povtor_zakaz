import pandas as pd
from datetime import datetime
import config

def classify_imported_product(subcategory: str, retail_price: float) -> str:
    """Mahsulotni podkategoriya va narxi bo'yicha segmentlarga ajratadi."""
    if not subcategory: 
        return "Boshqa tovarlar"
    
    sub = str(subcategory).strip()
    price = float(retail_price or 0)

    # Segmentatsiya qoidalari
    rules = {
        "Двойка": [(59900, "1. Dvoyka Arzon (60k gacha)"), 
                   (99900, "2. Dvoyka O'rta (100k gacha)"), 
                   (149900, "3. Dvoyka Ommabop (150k gacha)"), 
                   (float('inf'), "4. Dvoyka Premium (150k dan yuqori)")],
        "Тройка": [(99900, "1. Troyka Arzon (100k gacha)"), 
                   (149900, "2. Troyka O'rta (150k gacha)"), 
                   (199900, "3. Troyka Ommabop (200k gacha)"), 
                   (float('inf'), "4. Troyka Premium (200k dan yuqori)")],
        "Финка": [(49900, "1. Finka Arzon (50k gacha)"), 
                  (79900, "2. Finka O'rta (80k gacha)"), 
                  (float('inf'), "3. Finka Premium (80k dan yuqori)")],
        "Финка с кр/р": [(159900, "1. Finka kr/r Arzon (160k gacha)"), 
                         (219900, "2. Finka kr/r Ommabop (220k gacha)"), 
                         (float('inf'), "3. Finka kr/r Premium (220k dan yuqori)")],
        "Фудболка": [(29900, "1. Fudbolka Arzon (30k gacha)"), 
                     (44900, "2. Fudbolka O'rta (45k gacha)"), 
                     (float('inf'), "3. Fudbolka Premium (45k dan yuqori)")],
        "Футболка": [(9900, "1. Futbolka Arzon (10k gacha)"), 
                     (float('inf'), "2. Futbolka O'rta (10k dan yuqori)")],
        "Басаножка": [(99900, "1. Basanojka Arzon (100k gacha)"), 
                      (134900, "2. Basanojka O'rta (135k gacha)"), 
                      (float('inf'), "3. Basanojka Premium (135k dan yuqori)")],
        "Тапочка": [(39900, "1. Tapochka Arzon (40k gacha)"), 
                    (54900, "2. Tapochka O'rta (55k gacha)"), 
                    (float('inf'), "3. Tapochka Premium (55k dan yuqori)")],
        "Шорты": [(39900, "1. Shorts Arzon (40k gacha)"), 
                  (69900, "2. Shorts O'rta (70k gacha)"), 
                  (float('inf'), "3. Shorts Premium (70k dan yuqori)")],
        "Шortik": [(19900, "1. Shortik Arzon (20k gacha)"), 
                   (34900, "2. Shortik O'rta (35k gacha)"), 
                   (float('inf'), "3. Shortik Premium (35k dan yuqori)")],
        "Платье": [(69900, "1. Platye Arzon (70k gacha)"), 
                   (119900, "2. Platye O'rta (120k gacha)"), 
                   (float('inf'), "3. Platye Premium (120k dan yuqori)")],
        "Платье кр/р": [(99900, "1. Platye kr/r Arzon (100k gacha)"), 
                        (float('inf'), "2. Platye kr/r Premium (100k dan yuqori)")],
        "Пижама": [(49900, "1. Pijama Arzon (50k gacha)"), 
                   (float('inf'), "2. Pijama Ommabop (50k dan yuqori)")],
        "Набор": [(29900, "1. Nabor Arzon (30k gacha)"), 
                  (69900, "2. Nabor O'rta (70k gacha)"), 
                  (float('inf'), "3. Nabor Premium (70k dan yuqori)")],
        "Рубашка с дл/р": [(219900, "2. Rubashka dl/r O'rta (220k gacha)"), 
                           (249900, "3. Rubashka dl/r Sifatli (250k gacha)"), 
                           (float('inf'), "4. Rubashka dl/r Premium (250k dan yuqori)")],
        "Рубашка с кр/р": [(49900, "1. Rubashka kr/r Arzon (50k gacha)"), 
                           (float('inf'), "2. Rubashka kr/r Premium (50k dan yuqori)")],
        "Носки": [(9900, "1. Noski Arzon (10k gacha)"), 
                  (float('inf'), "2. Noski Ommabop (10k dan yuqori)")],
        "Комбинезон": [(39900, "1. Kombinezon Arzon (40k gacha)"), 
                       (69900, "2. Kombinezon O'rta (70k gacha)"), 
                       (float('inf'), "3. Kombinezon Premium (70k dan yuqori)")],
        "Майка": [(19900, "1. Mayka Arzon (20k gacha)"), 
                  (float('inf'), "2. Mayka Premium (20k dan yuqori)")],
        "Кепка": [(34900, "1. Kepka Arzon (35k gacha)"), 
                  (float('inf'), "2. Kepka Premium (35k dan yuqori)")],
        "Брюки на резинке": [(99900, "1. Bryuki Arzon (100k gacha)"), 
                             (119900, "2. Bryuki O'rta (120k gacha)"), 
                             (float('inf'), "3. Bryuki Premium (120k dan yuqori)")],
        "Брюки": [(84900, "1. Bryuki Arzon (85k gacha)"), 
                  (float('inf'), "2. Bryuki Premium (85k dan yuqori)")],
        "Памперс": [(19900, "1. Pampers Arzon (20k gacha)"), 
                    (99900, "2. Pampers O'rta (100k gacha)"), 
                    (float('inf'), "3. Pampers Premium (100k dan yuqori)")],
        "Ползунки": [(9900, "1. Polzunki Arzon (10k gacha)"), 
                     (float('inf'), "2. Polzunki Ommabop (10k dan yuqori)")],
        "Сумка": [(99900, "1. Sumka Arzon (100k gacha)"), 
                  (float('inf'), "2. Sumka Premium (100k dan yuqori)")],
        "Krasovka": [(99900, "1. Krasovka Arzon (100k gacha)"), 
                     (149900, "2. Krasovka O'rta (150k gacha)"), 
                     (float('inf'), "3. Krasovka Premium (150k dan yuqori)")],
        "Tufli": [(99900, "1. Tufli Arzon (100k gacha)"), 
                  (float('inf'), "2. Tufli Premium (100k dan yuqori)")],
        "Shortik djin": [(69900, "1. Shortik djin Arzon (70k gacha)"), 
                         (float('inf'), "2. Shortik djin Premium (70k dan yuqori)")],
        "Kapaklik fud": [(44900, "1. Kapaklik fud Arzon (45k gacha)"), 
                         (float('inf'), "2. Kapaklik fud Premium (45k dan yuqori)")],
        "Yubka": [(49900, "1. Yubka Arzon (50k gacha)"), 
                  (float('inf'), "2. Yubka Premium (50k dan yuqori)")],
        "Jilet": [(119900, "1. Jilet Arzon (120k gacha)"), 
                  (float('inf'), "2. Jilet Premium (120k dan yuqori)")],
        "Jaket": [(119900, "1. Jaket Arzon (120k gacha)"), 
                  (float('inf'), "2. Jaket Premium (120k dan yuqori)")],
        "Sandal": [(99900, "1. Sandal Arzon (100k gacha)"), 
                   (float('inf'), "2. Sandal Premium (100k dan yuqori)")],
    }

    if sub in rules:
        for threshold, label in rules[sub]:
            if price <= threshold:
                return label
    
    return f"Boshqa: {sub}"

def format_money(val: float) -> str:
    """Pul miqdorini chiroyli formatda qaytaradi (masalan: 1 000 000)."""
    try:
        return f"{int(val):,}".replace(",", " ")
    except (ValueError, TypeError):
        return "0"

def clean_supplier_name(name: str) -> str:
    """Supplier nomidagi ortiqcha belgilarni tozalaydi."""
    if not name: return ""
    return str(name).replace('\u00A0', ' ').strip()

def is_dona_category(category: str) -> bool:
    """Kategoriya 'dona' (pochka emas) ekanligini tekshiradi."""
    return str(category).strip() in config.DONA_CATEGORIES

def jins_sort_key(v):
    """Jins bo'yicha tartiblash kaliti."""
    JINS_ORDER = ['Девочки', 'Мальчики', 'Универсал']
    try:
        return JINS_ORDER.index(str(v).strip())
    except:
        return len(JINS_ORDER)

def build_caption(article, group, first, color_type, pending_df=None):
    """Zakaz kartochkasi uchun caption yaratadi."""
    icon = {'white': '📦', 'yellow': '🟡', 'red': '🔴'}.get(color_type, '📦')
    subcat = str(first.get('subcategory', '-')).strip()
    
    # Kategoriya bo'yicha birlikni aniqlash
    cat = str(first.get('category', '')).strip()
    unit = 'dona' if cat in config.DONA_CATEGORIES else 'pochka'

    warning = ''
    if color_type == 'white' and pending_df is not None and not pending_df.empty:
        match = pending_df[pending_df['artikul'] == article]
        if not match.empty:
            warning = f"\n⚠️ <b>Eslatma:</b> {int(match['quantity'].sum())} ta yo'lda."

    caption = f"{icon} <b>{article}</b>\n<i>{subcat}</i>{warning}\n"

    if color_type == 'white':
        price = first.get('supply_price', 0)
        try:
            price_str = f"{float(price):,.0f}".replace(',', ' ')
        except:
            price_str = '0'
        caption += f"👤 {first.get('supplier', '-')}\n💵 {price_str} so'm\n"
    elif color_type in ('yellow', 'red'):
        caption += f"({first.get('supplier', 'Noma\u02bclum')})\n"

    for shop, s_group in group.groupby('shop'):
        caption += f"\n🏪 <b>{shop}:</b>"
        for _, row in s_group.iterrows():
            qoldiq = int(float(row.get('hozirgi_qoldiq', 0) or 0))
            sotuv = int(float(row.get('prodano', 0) or 0))
            caption += f"\n  - {row.get('color','-')}: <b>{int(row.get('quantity',0))} {unit}</b> (Q:{qoldiq}) (S:{sotuv})"

    return caption
