# migrate_normalize_existing.py
"""
ESKI BAZADAGI DUPLIKATLARNI BIR MARTALIK TUZATISH.

ISHLATILISH:
    python migrate_normalize_existing.py        # faqat DRY-RUN, hech narsa o'zgartirmaydi
    python migrate_normalize_existing.py --apply  # haqiqiy yangilash

NIMA QILADI:
    1. d_mahsulotlar, f_sotuvlar, f_qoldiqlar, generated_orders jadvallaridagi
       kategoriya tipidagi ustunlarni canonical formga keltiradi.
    2. Цвет, Поставщик, Наименование ustunlarida faqat NBSP/trim tuzatadi.

XAVFSIZLIK:
    - DRY-RUN rejimi standart — har bir UPDATE'ning tasiri ko'rsatiladi,
      lekin bajarilmaydi.
    - --apply bayrog'i bilan ishga tushirilganda HAR BIR jadval uchun
      avtomatik backup yaratiladi: <jadval>_backup_YYYYMMDD_HHMMSS.
    - Transaction ichida ishlaydi — xatolik bo'lsa hammasi rollback.

ISHLATISHDAN OLDIN:
    - Bot va data_engine ishga tushgan bo'lmasin (WAL fayllari yopiq bo'lsin).
    - Data_Model.db fayli zaxiraga ko'chirib qo'yilsin (qo'shimcha himoya).
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Ushbu loyihadagi normalize lug'atini ishlatamiz
from data_normalizer import safe_normalize, canonical_form


def resolve_db_path():
    """
    DB faylining universal yo'lini aniqlaydi (har qanday kompyuter/deploy uchun).

    Mantiq:
      1. DATABASE_URL env o'zgaruvchisi bor va sqlite bo'lsa -> undagi fayl yo'lini ishlatamiz.
      2. DATABASE_URL bor, lekin PostgreSQL (postgres://...) bo'lsa -> bu skript faqat
         SQLite bilan ishlaydi, shu sababli ogohlantiramiz va to'xtaymiz.
      3. Aks holda -> skript bilan bir papkadagi (loyiha root) Data_Model.db.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        low = db_url.strip().lower()
        if low.startswith("sqlite"):
            # sqlite:///Data_Model.db  yoki  sqlite:////abs/path/Data_Model.db
            path_part = db_url.split("///", 1)[-1]
            if not path_part:
                path_part = "Data_Model.db"
            p = Path(path_part)
            if not p.is_absolute():
                # Relative yo'l skript turgan papkadan hisoblanadi
                p = Path(__file__).parent / p
            return str(p)
        else:
            # PostgreSQL yoki boshqa: bu skript faqat SQLite rejimida ishlaydi
            print(
                "❌ DATABASE_URL SQLite emas (PostgreSQL aniqlandi).\n"
                "   migrate_normalize_existing.py faqat SQLite (Data_Model.db) bilan ishlaydi.\n"
                "   PostgreSQL bazasini normalize qilish uchun alohida vositadan foydalaning."
            )
            sys.exit(1)

    # Fallback: skript bilan bir papkadagi Data_Model.db
    return str(Path(__file__).parent / "Data_Model.db")


DB_PATH = resolve_db_path()

# Jadval va ustun xaritasi: qaysi ustunlar qanday rejimda normalize qilinadi.
# mode = 'canonical' -> canonical_form (case ham o'zgaradi)
# mode = 'safe'      -> safe_normalize (faqat trim/NBSP)
TABLES = {
    "d_mahsulotlar": [
        ("Категория", "canonical"),
        ("Подкатегория", "canonical"),
        ("Вид", "canonical"),
        ("Материал", "canonical"),
        ("Акция", "canonical"),
        ("Пол", "canonical"),
        ("Сезон", "canonical"),
        ("Цвет", "safe"),
        ("Поставщик", "safe"),
        ("Наименование", "safe"),
        ("Бренд", "safe"),
    ],
    "f_sotuvlar": [
        ("Категория", "canonical"),
        ("Подкатегория", "canonical"),
        ("Вид", "canonical"),
        ("Материал", "canonical"),
        ("Акция", "canonical"),
        ("Наименование", "safe"),
        ("Магазин", "safe"),
    ],
    "f_qoldiqlar": [
        ("Категория", "canonical"),
        ("Подкатегория", "canonical"),
        ("Вид", "canonical"),
        ("Материал", "canonical"),
        ("Пол", "canonical"),
        ("Наименование", "safe"),
        ("Магазин", "safe"),
    ],
    "generated_orders": [
        ("category", "canonical"),
        ("subcategory", "canonical"),
        ("supplier", "safe"),
        ("shop", "safe"),
        ("color", "safe"),  # Цвет — case saqlash MUHIM, faqat trim
    ],
}


def normalize_value(value, column, mode):
    """Ustun va rejimga qarab to'g'ri normalize qiladi."""
    if value is None:
        return None
    if mode == "canonical":
        return canonical_form(value, column)
    return safe_normalize(value)


def collect_changes(conn):
    """
    Har bir jadval va ustun uchun o'zgaradigan satrlar sonini hisoblaydi.
    Hech narsa o'zgartirmaydi — faqat HISOB qaytaradi.
    """
    cur = conn.cursor()
    report = {}

    for table, columns in TABLES.items():
        # Jadval mavjudligini tekshirish
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        if not cur.fetchone():
            report[table] = {"_missing": True}
            continue

        table_report = {}

        for col, mode in columns:
            # Ustun mavjudligini tekshirish
            cur.execute(f'PRAGMA table_info("{table}")')
            cols_in_table = [r[1] for r in cur.fetchall()]
            if col not in cols_in_table:
                table_report[col] = {"_missing": True}
                continue

            cur.execute(
                f'SELECT DISTINCT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL'
            )
            values = [r[0] for r in cur.fetchall()]

            change_map = {}  # old_value -> new_value (faqat farqi borlar)
            for v in values:
                new_v = normalize_value(v, col, mode)
                if new_v != v:
                    change_map[v] = new_v

            # Har bir o'zgarish uchun ta'sirlangan satrlar sonini hisoblash
            details = []
            for old, new in change_map.items():
                cur.execute(
                    f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" = ?', (old,)
                )
                cnt = cur.fetchone()[0]
                details.append((old, new, cnt))

            table_report[col] = {
                "mode": mode,
                "changes": details,
                "total_rows_affected": sum(d[2] for d in details),
            }

        report[table] = table_report

    return report


def print_report(report):
    """Hisobotni o'qish uchun chiroyli formatda chiqaradi."""
    grand_total = 0
    for table, table_report in report.items():
        if table_report.get("_missing"):
            print(f"  [SKIP] {table} — jadval mavjud emas")
            continue
        print(f"\n=== {table} ===")
        table_total = 0
        for col, info in table_report.items():
            if info.get("_missing"):
                print(f"  [SKIP] {col} — ustun mavjud emas")
                continue
            changes = info["changes"]
            if not changes:
                print(f"  [OK] {col} ({info['mode']}) — o'zgarish yo'q")
                continue
            print(
                f"  [CHANGE] {col} ({info['mode']}) — {len(changes)} ta unique, "
                f"{info['total_rows_affected']} ta satr ta'sirlanadi"
            )
            for old, new, cnt in changes:
                print(f"      {old!r:40s} -> {new!r:40s}  ({cnt} satr)")
            table_total += info["total_rows_affected"]
        print(f"  --- Jami: {table_total} satr ---")
        grand_total += table_total
    print(f"\n>>> UMUMIY: {grand_total} satr o'zgaradi <<<")
    return grand_total


def apply_changes(conn, report):
    """Hisobotdagi o'zgarishlarni transaction ichida qo'llaydi."""
    cur = conn.cursor()
    backup_suffix = datetime.now().strftime("_backup_%Y%m%d_%H%M%S")

    # 1) Avval har bir jadval uchun backup yaratamiz
    for table in report:
        if report[table].get("_missing"):
            continue
        backup_name = f"{table}{backup_suffix}"
        print(f"  Backup yaratilmoqda: {backup_name}")
        cur.execute(f'CREATE TABLE "{backup_name}" AS SELECT * FROM "{table}"')

    # 2) UPDATE'larni qo'llaymiz
    total_applied = 0
    for table, table_report in report.items():
        if table_report.get("_missing"):
            continue
        for col, info in table_report.items():
            if info.get("_missing") or not info["changes"]:
                continue
            for old, new, cnt in info["changes"]:
                cur.execute(
                    f'UPDATE "{table}" SET "{col}" = ? WHERE "{col}" = ?',
                    (new, old),
                )
                total_applied += cur.rowcount
                print(
                    f"    {table}.{col}: {old!r} -> {new!r}  ({cur.rowcount} satr)"
                )

    print(f"\n>>> JAMI {total_applied} ta satr yangilandi <<<")
    print(f"Backuplar: *_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


def main():
    apply = "--apply" in sys.argv

    print(f"Database: {DB_PATH}")
    mode_label = "APPLY (haqiqiy yangilash)" if apply else "DRY-RUN (faqat ko'rish)"
    print(f"Rejim: {mode_label}\n")

    conn = sqlite3.connect(DB_PATH)
    try:
        report = collect_changes(conn)
        total = print_report(report)

        if apply and total > 0:
            confirm = input("\nDavom ettirilsinmi? (HA ni yozing): ").strip()
            if confirm != "HA":
                print("Bekor qilindi.")
                return
            apply_changes(conn, report)
            conn.commit()
            print("\n✅ Tranzaksiya commit qilindi.")
        elif apply and total == 0:
            print("\n✅ Hech narsa o'zgartirilmadi (duplikat topilmadi).")
        else:
            print(
                "\n[DRY-RUN] Hech narsa o'zgartirilmadi. "
                "Haqiqiy yangilash uchun: python migrate_normalize_existing.py --apply"
            )
    except Exception as e:
        conn.rollback()
        print(f"\n❌ XATOLIK: {e}")
        print("Tranzaksiya rollback qilindi — ma'lumotlar o'zgarmadi.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
