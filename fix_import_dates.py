"""
d_mahsulotlar.import_date NULL larni API dan tuzatish.
update_catalog() chaqiradi → barcha mahsulot ma'lumotlari yangilanadi.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import src.database.db_manager as db_manager
import pandas as pd
from sqlalchemy import text
from data_engine import get_billz_access_token, update_catalog, sync_missing_products

engine = db_manager.engine

# Дата2 va last_import ustunlarini qo'shish (yo'q bo'lsa)
for stmt in [
    'ALTER TABLE f_qoldiqlar ADD COLUMN "Дата2" TEXT',
    'ALTER TABLE f_qoldiqlar ADD COLUMN "last_import" TEXT',
]:
    try:
        with engine.begin() as conn:
            conn.execute(text(stmt))
        print(f"✅ {stmt}")
    except Exception:
        pass  # allaqachon bor

# Before
before = pd.read_sql("""
    SELECT
        COUNT(*) AS jami,
        SUM(CASE WHEN import_date IS NULL OR TRIM(import_date)='' OR TRIM(import_date)='None' THEN 1 ELSE 0 END) AS null_count
    FROM d_mahsulotlar
""", engine).iloc[0]
print(f"\nBEFORE → jami: {before['jami']}, NULL: {before['null_count']}")

# Token
token = get_billz_access_token()
if not token:
    print("❌ Token olinmadi")
    sys.exit(1)

# Catalog reload (d_mahsulotlar ni to'liq yangilaydi)
update_catalog(token, engine)

# sync_missing_products — NULL qolganlarni qoldiq+sotuv Дата2 dan tuzatadi
sync_missing_products(engine)

# After
after = pd.read_sql("""
    SELECT
        COUNT(*) AS jami,
        SUM(CASE WHEN import_date IS NULL OR TRIM(import_date)='' OR TRIM(import_date)='None' THEN 1 ELSE 0 END) AS null_count,
        SUM(CASE WHEN import_date IS NOT NULL AND TRIM(import_date)!='' AND TRIM(import_date)!='None' THEN 1 ELSE 0 END) AS ok_count
    FROM d_mahsulotlar
""", engine).iloc[0]
print(f"\nAFTER → jami: {after['jami']}, NULL: {after['null_count']}, OK: {after['ok_count']}")
print(f"✅ Tuzatildi: {int(before['null_count']) - int(after['null_count'])} ta")
