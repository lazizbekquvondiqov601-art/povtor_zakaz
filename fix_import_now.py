"""
Hozirgi bazadagi NULL import_date larni tuzatish.
Uchta manba: f_qoldiqlar.Дата2, f_sotuvlar.Дата2, d_mahsulotlar.Дата1
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import src.database.db_manager as db_manager
from sqlalchemy import text
import pandas as pd
from data_engine import sync_missing_products

engine = db_manager.engine

print("=== BEFORE ===")
before = pd.read_sql("""
    SELECT COUNT(*) jami,
        SUM(CASE WHEN import_date IS NULL OR TRIM(COALESCE(import_date,'')) IN ('','None','nan') THEN 1 ELSE 0 END) nulls,
        SUM(CASE WHEN import_date IS NOT NULL AND TRIM(import_date) NOT IN ('','None','nan') THEN 1 ELSE 0 END) ok
    FROM d_mahsulotlar
""", engine)
print(before.to_string(index=False))

# 1) Ustunlar qo'shish
for stmt in [
    'ALTER TABLE f_qoldiqlar ADD COLUMN "Дата2" TEXT',
    'ALTER TABLE f_qoldiqlar ADD COLUMN "last_import" TEXT',
]:
    try:
        with engine.begin() as conn:
            conn.execute(text(stmt))
        print(f"✅ {stmt[:55]}")
    except Exception:
        pass

# 2) f_qoldiqlar.Дата2 ni d_mahsulotlar.Дата1 dan backfill
with engine.begin() as conn:
    r = conn.execute(text('''
        UPDATE f_qoldiqlar
        SET "Дата2" = (
            SELECT d."Дата1" FROM d_mahsulotlar d
            WHERE d.product_id = f_qoldiqlar.product_id
              AND d."Дата1" IS NOT NULL
              AND TRIM(d."Дата1") NOT IN ('', 'None')
        )
        WHERE "Дата2" IS NULL OR "Дата2" = ''
    '''))
    print(f"✅ f_qoldiqlar.Дата2 backfill: {r.rowcount} qator")

# 2.5) d_mahsulotlar.import_date ni TO'G'RIDAN-TO'G'RI f_sotuvlar.Дата2 dan to'ldirish.
#      Sabab: faqat sotuvda uchraydigan (qoldig'i yo'q) mahsulotlar uchun
#      f_qoldiqlar backfill ishlamaydi. f_sotuvlar.Дата2 formati: "I-19.06.2026"
#      -> oxirgi "-" dan keyingi qism olinadi va DD.MM.YYYY tekshiriladi.
#      sync_missing_products ham buni qiladi, lekin bu yerda aniq va vektorlashtirilgan
#      tarzda NULL import_date larni sotuv sanasidan to'ldiramiz.
try:
    with engine.begin() as conn:
        r2 = conn.execute(text('''
            UPDATE d_mahsulotlar
            SET import_date = (
                SELECT TRIM(
                    CASE
                        WHEN INSTR(s."Дата2", '-') > 0
                        THEN SUBSTR(s."Дата2", INSTR(s."Дата2", '-') + 1)
                        ELSE s."Дата2"
                    END
                )
                FROM f_sotuvlar s
                WHERE s.product_id = d_mahsulotlar.product_id
                  AND s."Дата2" IS NOT NULL
                  AND TRIM(s."Дата2") NOT IN ('', 'None', 'nan')
                LIMIT 1
            )
            WHERE (import_date IS NULL OR TRIM(COALESCE(import_date, '')) IN ('', 'None', 'nan'))
              AND EXISTS (
                  SELECT 1 FROM f_sotuvlar s2
                  WHERE s2.product_id = d_mahsulotlar.product_id
                    AND s2."Дата2" IS NOT NULL
                    AND TRIM(s2."Дата2") NOT IN ('', 'None', 'nan')
              )
        '''))
        print(f"✅ d_mahsulotlar.import_date <- f_sotuvlar.Дата2 backfill: {r2.rowcount} qator")
except Exception as e:
    print(f"⚠️ f_sotuvlar.Дата2 -> import_date backfill xatosi (Дата2 ustuni yo'q bo'lishi mumkin): {e}")

# 3) sync_missing_products (Дата2 + Дата1 uchala manba)
sync_missing_products(engine)

print("\n=== AFTER ===")
after = pd.read_sql("""
    SELECT COUNT(*) jami,
        SUM(CASE WHEN import_date IS NULL OR TRIM(COALESCE(import_date,'')) IN ('','None','nan') THEN 1 ELSE 0 END) nulls,
        SUM(CASE WHEN import_date IS NOT NULL AND TRIM(import_date) NOT IN ('','None','nan') THEN 1 ELSE 0 END) ok
    FROM d_mahsulotlar
""", engine)
print(after.to_string(index=False))

null_b = int(before['nulls'].iloc[0])
null_a = int(after['nulls'].iloc[0])
print(f"\n✅ Tuzatildi: {null_b - null_a} ta | Qoldi: {null_a} ta (Billz da Дата field yo'q)")
