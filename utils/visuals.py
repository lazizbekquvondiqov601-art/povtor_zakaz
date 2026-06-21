import io
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

DONA_CATS = {'Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье'}

def build_caption(article, group, first, color_type, pending_df=None):
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
        _unknown = 'Noma\u02bclum'
        caption += f"({first.get('supplier', _unknown)})\n"

    for shop, s_group in group.groupby('shop'):
        caption += f"\n🏪 <b>{shop}:</b>"
        for _, row in s_group.iterrows():
            qoldiq = int(float(row.get('hozirgi_qoldiq', 0) or 0))
            sotuv  = int(float(row.get('prodano', 0) or 0))
            caption += f"\n  - {row.get('color','-')}: <b>{int(row.get('quantity',0))} {unit}</b> (Q:{qoldiq}) (S:{sotuv})"

    return caption

def generate_macro_image(df, sub_name: str):
    sub_df_full = df[df['Подкатегория'] == sub_name]
    if sub_df_full.empty:
        return None

    sub_df_full = sub_df_full.copy()
    sub_df_full['Пол'] = sub_df_full['Пол'].fillna('').astype(str).str.strip()
    sub_df_full['Пол'] = sub_df_full['Пол'].replace({
        '': 'Универсал',
        'Девочек': 'Девочки',
        'Мальчик': 'Мальчики',
    })

    macro = sub_df_full.groupby(['Пол', 'Real_Sotuv_Segmenti']).agg(
        Sred_Ost=('Ortacha_Qoldiq', 'sum'),
        Hoz_Qoldiq=('Hozirgi_Qoldiq', 'sum'),
        Sotuv=('Продано', 'sum'),
        Auto_Zakaz=('Zakaz', 'sum')
    ).reset_index().sort_values(['Пол', 'Real_Sotuv_Segmenti'])
    
    jins_totals = macro.groupby('Пол').agg(
        jins_total_sotuv=('Sotuv', 'sum'),
        jins_total_qoldiq=('Hoz_Qoldiq', 'sum'),
        jins_total_sred=('Sred_Ost', 'sum'),
        jins_total_zakaz=('Auto_Zakaz', 'sum'),
    ).reset_index()
    macro = pd.merge(macro, jins_totals, on='Пол', how='left')

    total_sales  = macro['Sotuv'].sum()
    total_qoldiq = macro['Hoz_Qoldiq'].sum()
    total_sred   = macro['Sred_Ost'].sum()
    total_zakaz  = macro['Auto_Zakaz'].sum()
    total_obr    = (total_sales / total_sred * 100) if total_sred > 0 else 0

    JINS_ORDER = ['Девочки', 'Мальчики', 'Универсал']
    def jins_sort_key(v):
        try: return JINS_ORDER.index(str(v).strip())
        except: return len(JINS_ORDER)

    macro['_jins_sort'] = macro['Пол'].apply(jins_sort_key)
    macro = macro.sort_values(['_jins_sort', 'Real_Sotuv_Segmenti']).reset_index(drop=True)

    table_rows = []
    prev_jins = None

    for _, row in macro.iterrows():
        seg_full = row['Real_Sotuv_Segmenti']
        try:
            num  = seg_full.split(".")[0].strip()
            rest = seg_full.split(".", 1)[1].strip()
            for word in sub_name.split():
                rest = rest.replace(word, "").strip()
            seg_short = f"{num}. {rest}"
        except:
            seg_short = seg_full

        sotuv  = int(row['Sotuv'])
        qoldiq = int(row['Hoz_Qoldiq'])
        sred   = row['Sred_Ost']
        zakaz  = int(row['Auto_Zakaz'])
        obr_val = (sotuv / sred * 100) if sred > 0 else 0

        jins = str(row['Пол']).strip() or 'Универсал'

        jins_s = row['jins_total_sotuv']
        jins_q = row['jins_total_qoldiq']
        q_ul = round(qoldiq / jins_q * 100) if jins_q > 0 else 0
        s_ul = round(sotuv  / jins_s * 100) if jins_s > 0 else 0

        if prev_jins is not None and jins != prev_jins:
            prev_row = macro[macro['Пол'] == prev_jins].iloc[0]
            prev_s = int(prev_row['jins_total_sotuv'])
            prev_q = int(prev_row['jins_total_qoldiq'])
            prev_sred = prev_row['jins_total_sred']
            prev_z = int(prev_row['jins_total_zakaz'])
            prev_obr = (prev_s / prev_sred * 100) if prev_sred > 0 else 0
            table_rows.append([
                f"{prev_jins} TOTAL",
                "",
                f"{int(prev_obr)}%",
                f"{prev_s}",
                f"{prev_q}",
                "100%",
                "100%",
                f"{prev_z}" if prev_z > 0 else "—",
                "total"
            ])

        table_rows.append([
            jins,
            seg_short,
            f"{int(obr_val)}%",
            f"{sotuv}",
            f"{qoldiq}",
            f"{q_ul}%",
            f"{s_ul}%",
            f"{zakaz}" if zakaz > 0 else "—",
            "data"
        ])
        prev_jins = jins

    if prev_jins:
        prev_row = macro[macro['Пол'] == prev_jins].iloc[0]
        prev_s = int(prev_row['jins_total_sotuv'])
        prev_q = int(prev_row['jins_total_qoldiq'])
        prev_sred = prev_row['jins_total_sred']
        prev_z = int(prev_row['jins_total_zakaz'])
        prev_obr = (prev_s / prev_sred * 100) if prev_sred > 0 else 0
        table_rows.append([
            f"{prev_jins} TOTAL",
            "",
            f"{int(prev_obr)}%",
            f"{prev_s}",
            f"{prev_q}",
            "100%",
            "100%",
            f"{prev_z}" if prev_z > 0 else "—",
            "total"
        ])

    table_rows.append([
        "JAMI",
        "",
        f"{int(total_obr)}%",
        f"{int(total_sales)}",
        f"{int(total_qoldiq)}",
        "100%",
        "100%",
        f"{int(total_zakaz)}",
        "grand"
    ])

    col_labels = ["Jins", "Segment", "OBR%", "Sotildi", "Qoldiq", "Q.Ulush", "S.Ulush", "Zakaz"]
    display_rows = [r[:8] for r in table_rows]

    n_rows = len(display_rows)
    fig_h  = 0.45 * (n_rows + 1) + 0.8
    fig, ax = plt.subplots(figsize=(14, fig_h))
    ax.axis('off')

    fig.text(0.04, 0.97, f"📊  MAKRO TAHLIL: {sub_name}",
             fontsize=13, fontweight='bold', va='top', color='#1a1a1a')
    fig.text(0.04, 0.90, "Davr: oy boshidan",
             fontsize=9, va='top', color='#888888')

    table = ax.table(
        cellText=display_rows,
        colLabels=col_labels,
        cellLoc='center',
        loc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.55)

    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#dddddd')
        cell.set_linewidth(0.5)

        if r == 0:
            cell.set_facecolor('#2C3E50')
            cell.set_text_props(color='white', fontweight='bold', fontsize=9)
            continue

        marker = table_rows[r-1][8] if r <= len(table_rows) else "data"

        if marker == "grand":
            cell.set_facecolor('#2C3E50')
            cell.set_text_props(color='white', fontweight='bold')
        elif marker == "total":
            cell.set_facecolor('#F39C12')
            cell.set_text_props(color='white', fontweight='bold')
        else:
            if c == 2:
                try:
                    obr_val = int(table_rows[r-1][2].replace('%',''))
                    if obr_val >= 100:
                        cell.set_facecolor('#d4edda')
                        cell.set_text_props(color='#155724', fontweight='bold')
                    elif obr_val >= 50:
                        cell.set_facecolor('#fff3cd')
                        cell.set_text_props(color='#856404', fontweight='bold')
                    else:
                        cell.set_facecolor('#f8d7da')
                        cell.set_text_props(color='#721c24', fontweight='bold')
                except:
                    cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
            elif c == 7:
                try:
                    z = int(table_rows[r-1][7])
                    if z > 0:
                        cell.set_facecolor('#cce5ff')
                        cell.set_text_props(color='#004085', fontweight='bold')
                    else:
                        cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
                except:
                    cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
            elif c in (5, 6):
                try:
                    q = int(table_rows[r-1][5].replace('%',''))
                    s = int(table_rows[r-1][6].replace('%',''))
                    if c == 6 and s > q + 5:
                        cell.set_facecolor('#fff3cd')
                        cell.set_text_props(color='#856404', fontweight='bold')
                    elif c == 5 and q > s + 10:
                        cell.set_facecolor('#d1ecf1')
                        cell.set_text_props(color='#0c5460')
                    else:
                        cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
                except:
                    cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
            else:
                cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')

    plt.tight_layout(rect=[0, 0, 1, 0.88])
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf
