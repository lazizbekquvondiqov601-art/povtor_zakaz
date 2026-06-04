import db_manager
from sqlalchemy import text

with db_manager.engine.connect() as conn:
    result = conn.execute(text('''
        SELECT 
            date("Дата") as kun,
            COUNT(DISTINCT "Артикул") as unikal_artikul,
            COUNT(*) as jami_qator,
            SUM("Продано за вычетом возвратов") as jami_sotuv
        FROM f_sotuvlar
        WHERE date("Дата") >= '2026-05-22'
          AND date("Дата") <= '2026-05-26'
        GROUP BY date("Дата")
        ORDER BY date("Дата")
    ''')).fetchall()
    
    for row in result:
        print(f"Sana: {row[0]} | Artikul: {row[1]} | Qator: {row[2]} | Sotuv: {row[3]}")