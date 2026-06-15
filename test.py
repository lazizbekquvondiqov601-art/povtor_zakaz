import pandas as pd
from sqlalchemy import create_engine
import config

engine = create_engine(config.POSTGRES_URL)

# f_qoldiqlar da Пол ustuni bormi?
df = pd.read_sql('''
    SELECT "Пол", COUNT(*) as soni
    FROM f_qoldiqlar
    WHERE "Подкатегория" = 'Двойка'
    GROUP BY "Пол"
    ORDER BY soni DESC
    LIMIT 10
''', engine)

print("=== f_qoldiqlar dagi Пол (to'g'ridan) ===")
print(df.to_string())

# auto_zakaz dagi prod_lookup simulatsiyasi
df2 = pd.read_sql('''
    SELECT "Пол", COUNT(*) as soni
    FROM d_mahsulotlar
    WHERE "Подкатегория" = 'Двойка'
    GROUP BY "Пол"
    ORDER BY soni DESC
''', engine)

print("\n=== d_mahsulotlar Пол ===")
print(df2.to_string())

# Ikkisini taqqoslash - oxirgi sana qoldig'i
df3 = pd.read_sql('''
    SELECT 
        COALESCE(q."Пол", d."Пол", 'NULL') as pol_qoldiq,
        SUM(q."Кол-во") as qoldiq
    FROM f_qoldiqlar q
    JOIN d_mahsulotlar d ON q.product_id = d.product_id
    WHERE d."Подкатегория" = 'Двойка'
      AND date(q."Дата") = (SELECT MAX(date("Дата")) FROM f_qoldiqlar)
    GROUP BY COALESCE(q."Пол", d."Пол", 'NULL')
    ORDER BY qoldiq DESC
''', engine)

print("\n=== Qoldiq: q.Пол vs d.Пол ===")
print(df3.to_string())