import pandas as pd
from datetime import datetime
import config

def classify_imported_product(subcategory: str, retail_price: float) -> str:
    """Mahsulotni podkategoriya va narxi bo'yicha segmentlarga ajratadi (DAX logic)."""
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
    elif sub == "Фudbolka" or sub == "Фудболка":
        if price <= 29900: return "1. Fudbolka Arzon (30k gacha)"
        if price <= 44900: return "2. Fudbolka O'rta (45k gacha)"
        return "3. Fudbolka Premium (45k dan yuqori)"
    elif sub == "Футболka" or sub == "Футболка":
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
    elif sub == "Ласиna":       return "Lasina (19900)"
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

def is_dona_category(category_name: str) -> bool:
    """Kategoriya dona hisobida (pochka emas) zakaz qilinishini tekshiradi."""
    dona_cats = {'Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье'}
    return str(category_name).strip() in dona_cats

def format_money(val: float) -> str:
    """Pullarni o'zbek formatida chiqaradi."""
    return f"{int(val):,}".replace(",", " ")

def build_caption(article, group, first, color_type, pending_df=None):
    DONA_CATS = {'Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье'}
    icon   = {'white': '📦', 'yellow': '🟡', 'red': '🔴'}.get(color_type, '📦')
    subcat = str(first.get('subcategory', '-')).strip()
    unit   = 'dona' if str(first.get('category', '')).strip() in DONA_CATS else 'pochka'

    warning = ''
    if color_type == 'white' and pending_df is not None and not pending_df.empty:       
        match = pending_df[pending_df['artikul'] == article]
        if not match.empty:
            warning = f"\n⚠️ <b>Eslatma:</b> {int(match['quantity'].sum())} ta yo'lda."

    caption = f"{icon} <b>{article}</b>\n<i>{subcat}</i>{warning}\n"

    if color_type == 'white':
        price = first.get('supply_price', 0)
        try:    price_str = f"{float(price):,.0f}".replace(',', ' ')
        except: price_str = '0'
        caption += f"👤 {first.get('supplier', '-')}\n💵 {price_str} so'm\n"
    elif color_type in ('yellow', 'red'):
        caption += f"({first.get('supplier', 'Noma\u02bclum')})\n"

    for shop, s_group in group.groupby('shop'):
        caption += f"\n🏪 <b>{shop}:</b>"
        for _, row in s_group.iterrows():
            qoldiq = int(float(row.get('hozirgi_qoldiq', 0) or 0))
            sotuv  = int(float(row.get('prodano', 0) or 0))
            caption += f"\n  - {row.get('color','-')}: <b>{int(row.get('quantity',0))} {unit}</b> (Q:{qoldiq}) (S:{sotuv})"

    return caption
