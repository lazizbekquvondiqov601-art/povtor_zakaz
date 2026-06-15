import io
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from src.utils.helpers import format_money

def generate_macro_image(df: pd.DataFrame, sub_name: str) -> io.BytesIO:
    """Makro tahlil jadvalini rasm ko'rinishida yaratadi."""
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

    # Jins bo'yicha totallar
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
            table_rows.append([f"{prev_jins} TOTAL", "", f"{int(prev_obr)}%", f"{prev_s}", f"{prev_q}", "100%", "100%", f"{prev_z}" if prev_z > 0 else "—", "total"])

        table_rows.append([jins, seg_short, f"{int(obr_val)}%", f"{sotuv}", f"{qoldiq}", f"{q_ul}%", f"{s_ul}%", f"{zakaz}" if zakaz > 0 else "—", "data"])
        prev_jins = jins

    if prev_jins:
        prev_row = macro[macro['Пол'] == prev_jins].iloc[0]
        prev_s = int(prev_row['jins_total_sotuv'])
        prev_q = int(prev_row['jins_total_qoldiq'])
        prev_sred = prev_row['jins_total_sred']
        prev_z = int(prev_row['jins_total_zakaz'])
        prev_obr = (prev_s / prev_sred * 100) if prev_sred > 0 else 0
        table_rows.append([f"{prev_jins} TOTAL", "", f"{int(prev_obr)}%", f"{prev_s}", f"{prev_q}", "100%", "100%", f"{prev_z}" if prev_z > 0 else "—", "total"])

    table_rows.append(["JAMI", "", f"{int(total_obr)}%", f"{int(total_sales)}", f"{int(total_qoldiq)}", "100%", "100%", f"{int(total_zakaz)}", "grand"])

    col_labels = ["Jins", "Segment", "OBR%", "Sotildi", "Qoldiq", "Q.Ulush", "S.Ulush", "Zakaz"]
    display_rows = [r[:8] for r in table_rows]

    n_rows = len(display_rows)
    fig_h  = 0.45 * (n_rows + 1) + 0.8
    fig, ax = plt.subplots(figsize=(14, fig_h))
    ax.axis('off')

    fig.text(0.04, 0.97, f"📊  MAKRO TAHLIL: {sub_name}", fontsize=13, fontweight='bold', va='top', color='#1a1a1a')
    fig.text(0.04, 0.90, "Davr: oy boshidan", fontsize=9, va='top', color='#888888')

    table = ax.table(cellText=display_rows, colLabels=col_labels, cellLoc='center', loc='center')
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
                    if obr_val >= 100: cell.set_facecolor('#d4edda'); cell.set_text_props(color='#155724', fontweight='bold')
                    elif obr_val >= 50: cell.set_facecolor('#fff3cd'); cell.set_text_props(color='#856404', fontweight='bold')
                    else: cell.set_facecolor('#f8d7da'); cell.set_text_props(color='#721c24', fontweight='bold')
                except: cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
            elif c == 7:
                try:
                    z = int(table_rows[r-1][7])
                    if z > 0: cell.set_facecolor('#cce5ff'); cell.set_text_props(color='#004085', fontweight='bold')
                    else: cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
                except: cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
            elif c in (5, 6):
                try:
                    q = int(table_rows[r-1][5].replace('%',''))
                    s = int(table_rows[r-1][6].replace('%',''))
                    if c == 6 and s > q + 5: cell.set_facecolor('#fff3cd'); cell.set_text_props(color='#856404', fontweight='bold')
                    elif c == 5 and q > s + 10: cell.set_facecolor('#d1ecf1'); cell.set_text_props(color='#0c5460')
                    else: cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
                except: cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')
            else:
                cell.set_facecolor('#ffffff' if r % 2 == 1 else '#f9f9f9')

    plt.tight_layout(rect=[0, 0, 1, 0.88])
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf

def generate_sales_table_image(asosiy: dict, aksiya: dict, qoldiq: dict, aks_qoldiq: dict, label: str) -> io.BytesIO:
    """Sotuv tahlili jadvalini rasm ko'rinishida yaratadi."""
    all_cats = sorted(set(list(asosiy.keys()) + list(aksiya.keys())))
    rows = []
    total_qoldiq = total_sotuv = total_foyda = 0
    total_aks_sotuv = total_aks_foyda = 0

    for cat in all_cats:
        if cat == 'Boshqa tovarlar': continue
        a, ax = asosiy.get(cat, {}), aksiya.get(cat, {})
        q, aks_q = qoldiq.get(cat, 0), aks_qoldiq.get(cat, 0)
        qoldiq_qty, aks_qoldiq_qty = int(q), int(aks_q)
        sotuv_qty, sotuv_prof = int(a.get('qty', 0)), int(a.get('profit', 0))
        aks_qty, aks_prof = int(ax.get('qty', 0)), int(ax.get('profit', 0))

        total_qoldiq += qoldiq_qty
        total_sotuv += sotuv_qty
        total_foyda += sotuv_prof
        total_aks_sotuv += aks_qty
        total_aks_foyda += aks_prof

        total_stock = sotuv_qty + qoldiq_qty
        obr = int(sotuv_qty / total_stock * 100) if total_stock > 0 else 0

        rows.append([cat[:16], f"{qoldiq_qty}", f"{sotuv_qty}", format_money(sotuv_prof), f"{obr}%", f"{aks_qoldiq_qty}" if aks_qoldiq_qty > 0 else "—", f"{aks_qty}" if aks_qty > 0 else "—", format_money(aks_prof) if aks_prof > 0 else "—"])

    total_stock_all = total_sotuv + total_qoldiq
    total_obr = int(total_sotuv / total_stock_all * 100) if total_stock_all > 0 else 0
    rows.append(["JAMI", f"{total_qoldiq}", f"{total_sotuv}", format_money(total_foyda), f"{total_obr}%", f"{sum(aks_qoldiq.values()):.0f}", f"{total_aks_sotuv}", format_money(total_aks_foyda)])
    
    col_labels = ["Kategoriya", "Qoldiq", "Sotildi", "Foyda", "OBR%", "AksQoldiq", "AksSot.", "AksFoyda"]
    n_rows = len(rows)
    fig_h  = 0.42 * (n_rows + 1) + 1.2
    fig, ax = plt.subplots(figsize=(9, fig_h))
    ax.axis('off')
    fig.text(0.03, 0.98, "📊  SOTUV TAHLILI", fontsize=13, fontweight='bold', va='top', color='#1a1a1a')
    fig.text(0.03, 0.93, f"📅  {label}", fontsize=10, va='top', color='#555555')

    table = ax.table(cellText=rows, colLabels=col_labels, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.6)

    col_widths = [0.15, 0.32, 0.10, 0.10, 0.10, 0.10, 0.10, 0.09]
    for j, w in enumerate(col_widths):
        for i in range(n_rows + 1): table[i, j].set_width(w)

    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#dddddd'); cell.set_linewidth(0.5)
        if r == 0: cell.set_facecolor('#2C3E50'); cell.set_text_props(color='white', fontweight='bold', fontsize=8.5)
        elif r == n_rows: cell.set_facecolor('#ECF0F1'); cell.set_text_props(fontweight='bold')
        else:
            bg = '#ffffff' if r % 2 == 1 else '#f9f9f9'
            if c == 2:
                try:
                    val = int(rows[r-1][1])
                    if val == 0: cell.set_facecolor('#ffebee'); cell.set_text_props(color='#b71c1c', fontweight='bold')
                    elif val < 100: cell.set_facecolor('#fff3e0'); cell.set_text_props(color='#e65100')
                    else: cell.set_facecolor('#e3f2fd'); cell.set_text_props(color='#0d47a1')
                except: cell.set_facecolor(bg)
            elif c == 3: cell.set_facecolor('#e8f5e9' if r % 2 == 1 else '#f1f8e9'); cell.set_text_props(color='#1b5e20')
            elif c == 4:
                try:
                    obr_val = int(rows[r-1][4].replace('%', ''))
                    if obr_val >= 20: cell.set_facecolor('#d4edda'); cell.set_text_props(color='#155724', fontweight='bold')
                    elif obr_val >= 10: cell.set_facecolor('#fff3cd'); cell.set_text_props(color='#856404', fontweight='bold')
                    else: cell.set_facecolor('#f8d7da'); cell.set_text_props(color='#721c24', fontweight='bold')
                except: cell.set_facecolor(bg)
            elif c == 7: cell.set_facecolor('#fce4ec' if r % 2 == 1 else '#fdf2f5'); cell.set_text_props(color='#880e4f')
            else: cell.set_facecolor(bg)

    plt.tight_layout(rect=[0, 0, 1, 0.90])
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf
