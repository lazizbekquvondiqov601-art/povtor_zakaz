"""
Dashboard uchun barcha SQL so'rovlar.
Har bir funksiya try/except bilan o'ralgan — xatolik bo'lsa bo'sh/nol qaytaradi.
"""
import sys
from pathlib import Path
from datetime import date

# Bot loyihasi src/ papkasiga yo'l qo'shamiz
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text
import src.database.db_manager as db_manager


def _err(fn, e):
    """SQL kodi ko'rsatmasdan qisqa xatolik log."""
    msg = str(e).split('[SQL:')[0].rstrip().rstrip('\n')
    print(f"[dq:{fn}] {msg}")


# ---------------------------------------------------------------------------
# Yordamchi: 010/011 va Пакет% ni chiqarib tashlash uchun umumiy WHERE qismi
# ---------------------------------------------------------------------------
_EXCLUDE_WHERE = """
    AND "Артикул" NOT LIKE '010%'
    AND "Артикул" NOT LIKE '011%'
    AND "Наименование" NOT LIKE 'Пакет%'
"""


def get_kpi_summary(engine):
    """
    Dashboard yuqori qismidagi KPI kartalar uchun ma'lumot qaytaradi.

    Qaytariladi (dict):
        today_sum       — bugungi sotuv summasi (so'm)
        yesterday_sum   — kechagi sotuv summasi (so'm)
        trend_pct       — o'sish/pasayish foizi (float)
        pending_orders  — 'Kutilmoqda' statusli zakazlar soni
        urgent_count    — qoldig'i < 7 kunlik mahsulotlar soni
        problem_suppliers — 'Kutilmoqda' zakazli yetkazib beruvchilar soni
    """
    # Standart bo'sh natija — xatolik bo'lsa shu qaytadi
    result = {
        'today_sum': 0.0,
        'yesterday_sum': 0.0,
        'trend_pct': 0.0,
        'pending_orders': 0,
        'urgent_count': 0,
        'problem_suppliers': 0,
    }

    session = db_manager.Session()
    try:
        # --- Bugungi sotuv summasi ---
        row = session.execute(text("""
            SELECT COALESCE(SUM("Продажи со скидкой с учетом возвратов"), 0)
            FROM f_sotuvlar
            WHERE date("Дата") = date('now')
        """ + _EXCLUDE_WHERE)).fetchone()
        result['today_sum'] = float(row[0]) if row else 0.0

        # --- Kechagi sotuv summasi ---
        row = session.execute(text("""
            SELECT COALESCE(SUM("Продажи со скидкой с учетом возвратов"), 0)
            FROM f_sotuvlar
            WHERE date("Дата") = date('now', '-1 day')
        """ + _EXCLUDE_WHERE)).fetchone()
        result['yesterday_sum'] = float(row[0]) if row else 0.0

        # --- O'sish foizini hisoblaymiz ---
        if result['yesterday_sum'] > 0:
            result['trend_pct'] = round(
                (result['today_sum'] - result['yesterday_sum'])
                / result['yesterday_sum'] * 100,
                1
            )
        else:
            # Kecha sotuvlar bo'lmagan bo'lsa — 0 qoladi
            result['trend_pct'] = 0.0

        # --- Kutilmoqda zakazlar soni ---
        row = session.execute(text("""
            SELECT COUNT(*) FROM generated_orders
            WHERE status = 'Kutilmoqda'
        """)).fetchone()
        result['pending_orders'] = int(row[0]) if row else 0

        # --- Shoshilinch mahsulotlar: qoldiq / kunlik_o_rtacha < 7 kun ---
        # Oxirgi 30 kunlik o'rtacha sotuvni olamiz, so'ng qoldiq bilan taqqoslaymiz
        row = session.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT
                    q."Артикул",
                    COALESCE(q.last_stock, 0)                       AS qoldiq,
                    COALESCE(s.avg_daily, 0)                        AS avg_daily
                FROM (
                    -- Har bir artikulning eng so'nggi qoldig'i
                    SELECT "Артикул", SUM("Кол-во") AS last_stock
                    FROM f_qoldiqlar
                    WHERE date("Дата") = (SELECT MAX(date("Дата")) FROM f_qoldiqlar)
                      AND "Артикул" NOT LIKE '010%'
                      AND "Артикул" NOT LIKE '011%'
                      AND "Наименование" NOT LIKE 'Пакет%'
                    GROUP BY "Артикул"
                ) q
                LEFT JOIN (
                    -- Oxirgi 30 kunlik o'rtacha kunlik sotuv
                    SELECT "Артикул",
                           SUM("Продано за вычетом возвратов") * 1.0
                               / 30 AS avg_daily
                    FROM f_sotuvlar
                    WHERE date("Дата") >= date('now', '-30 days')
                      AND "Артикул" NOT LIKE '010%'
                      AND "Артикул" NOT LIKE '011%'
                      AND "Наименование" NOT LIKE 'Пакет%'
                    GROUP BY "Артикул"
                ) s ON q."Артикул" = s."Артикул"
                WHERE COALESCE(s.avg_daily, 0) > 0
                  AND (COALESCE(q.last_stock, 0) / s.avg_daily) < 7
            ) urgent
        """)).fetchone()
        result['urgent_count'] = int(row[0]) if row else 0

        # --- Muammoli yetkazib beruvchilar: 'Kutilmoqda' zakazli unique supplierlar ---
        row = session.execute(text("""
            SELECT COUNT(DISTINCT supplier)
            FROM generated_orders
            WHERE status = 'Kutilmoqda'
              AND supplier IS NOT NULL
              AND TRIM(supplier) != ''
        """)).fetchone()
        result['problem_suppliers'] = int(row[0]) if row else 0

    except Exception as e:
        # Xatolik bo'lsa standart nol qiymatlar qaytadi
        _err('kpi_summary', e)
    finally:
        session.close()

    return result


def get_urgent_orders(engine, limit=10):
    """
    Qoldig'i 7 kundan kam bo'lgan mahsulotlar ro'yxati.
    Hisoblash: qoldiq / o'rtacha_kunlik_sotuv < 7 kun.
    010/011 artikullar va 'Пакет%' nomli mahsulotlar chiqarib tashlanadi.

    Qaytariladi (list of dict):
        artikul, naim, kategoriya, qoldiq, avg_daily, kunlar_qoldi
    """
    session = db_manager.Session()
    try:
        rows = session.execute(text("""
            SELECT
                q."Артикул"                                             AS artikul,
                q."Наименование"                                        AS naim,
                COALESCE(NULLIF(TRIM(q."Категория"), ''), 'Boshqa')    AS kategoriya,
                COALESCE(q.last_stock, 0)                              AS qoldiq,
                ROUND(COALESCE(s.avg_daily, 0), 2)                     AS avg_daily,
                ROUND(
                    COALESCE(q.last_stock, 0)
                    / NULLIF(s.avg_daily, 0),
                    1
                )                                                       AS kunlar_qoldi
            FROM (
                -- Eng so'nggi sanadagi qoldiqlar
                SELECT
                    "Артикул",
                    MAX("Наименование")  AS "Наименование",
                    MAX("Категория")     AS "Категория",
                    SUM("Кол-во")        AS last_stock
                FROM f_qoldiqlar
                WHERE date("Дата") = (SELECT MAX(date("Дата")) FROM f_qoldiqlar)
                  AND "Артикул" NOT LIKE '010%'
                  AND "Артикул" NOT LIKE '011%'
                  AND "Наименование" NOT LIKE 'Пакет%'
                GROUP BY "Артикул"
            ) q
            LEFT JOIN (
                -- Oxirgi 30 kun bo'yicha kunlik o'rtacha sotuv
                SELECT
                    "Артикул",
                    SUM("Продано за вычетом возвратов") * 1.0 / 30 AS avg_daily
                FROM f_sotuvlar
                WHERE date("Дата") >= date('now', '-30 days')
                  AND "Артикул" NOT LIKE '010%'
                  AND "Артикул" NOT LIKE '011%'
                  AND "Наименование" NOT LIKE 'Пакет%'
                GROUP BY "Артикул"
            ) s ON q."Артикул" = s."Артикул"
            WHERE COALESCE(s.avg_daily, 0) > 0
              AND (COALESCE(q.last_stock, 0) / s.avg_daily) < 7
            ORDER BY kunlar_qoldi ASC
            LIMIT :lim
        """), {'lim': limit}).fetchall()

        return [
            {
                'artikul':    row[0],
                'naim':       row[1],
                'kategoriya': row[2],
                'qoldiq':     float(row[3]),
                'avg_daily':  float(row[4]),
                'kunlar_qoldi': float(row[5]) if row[5] is not None else 0.0,
            }
            for row in rows
        ]

    except Exception as e:
        _err('urgent_orders', e)
        return []
    finally:
        session.close()


def get_sales_sparkline(engine, end_date=None):
    """
    7 kunlik kunlik sotuv summasi (sparkline grafik uchun).
    end_date — oxirgi kun (default: bugun). Orqaga/oldinga navigatsiya uchun.
    """
    from datetime import timedelta
    standart = {'labels': [], 'values': [], 'last': 0.0, 'prev': 0.0, 'week_ago': 0.0}

    today = date.today()
    if end_date:
        try:
            end_d = date.fromisoformat(str(end_date))
        except Exception:
            end_d = today
    else:
        end_d = today

    start_d = end_d - timedelta(days=6)

    session = db_manager.Session()
    try:
        rows = session.execute(text("""
            SELECT
                date("Дата") AS kun,
                COALESCE(SUM("Продажи со скидкой с учетом возвратов"), 0) AS summa
            FROM f_sotuvlar
            WHERE date("Дата") >= :s AND date("Дата") <= :e
              AND "Артикул" NOT LIKE '010%'
              AND "Артикул" NOT LIKE '011%'
              AND "Наименование" NOT LIKE 'Пакет%'
            GROUP BY kun ORDER BY kun ASC
        """), {'s': str(start_d), 'e': str(end_d)}).fetchall()

        data_map = {str(r[0]): float(r[1]) for r in rows}
        labels = [str(start_d + timedelta(days=i)) for i in range(7)]
        values = [data_map.get(lbl, 0.0) for lbl in labels]

        def fmt(n):
            return f"{int(n):,}".replace(",", " ")

        prev_d = end_d - timedelta(days=1)

        return {
            'labels':     labels,
            'values':     values,
            'last':       values[-1],
            'prev':       values[-2] if len(values) >= 2 else 0.0,
            'last_fmt':   fmt(values[-1]),
            'prev_fmt':   fmt(values[-2] if len(values) >= 2 else 0.0),
            'end_date':   str(end_d),
            'prev_date':  str(prev_d),
            'start_date': str(start_d),
            'prev_start': str(start_d - timedelta(days=7)),
            'next_end':   str(min(end_d + timedelta(days=7), today)),
            'prev_day':   str(end_d - timedelta(days=1)),
            'next_day':   str(min(end_d + timedelta(days=1), today)),
            'is_today':   end_d >= today,
        }

    except Exception as e:
        _err('sales_sparkline', e)
        return standart
    finally:
        session.close()


def get_supplier_problems(engine, limit=5):
    """
    'Kutilmoqda' statusli eng ko'p zakazga ega yetkazib beruvchilar.
    oldest_days — eng eski 'Kutilmoqda' zakazdan o'tgan kunlar soni.

    Qaytariladi (list of dict):
        supplier, pending_count, oldest_days
    """
    session = db_manager.Session()
    try:
        rows = session.execute(text("""
            SELECT
                supplier,
                COUNT(*)                                              AS pending_count,
                COALESCE(
                    CAST(
                        julianday('now') - julianday(MIN(created_at))
                    AS INTEGER),
                    0
                )                                                     AS oldest_days
            FROM generated_orders
            WHERE status = 'Kutilmoqda'
              AND supplier IS NOT NULL
              AND TRIM(supplier) != ''
            GROUP BY supplier
            ORDER BY pending_count DESC, oldest_days DESC
            LIMIT :lim
        """), {'lim': limit}).fetchall()

        return [
            {
                'supplier':     row[0],
                'pending_count': int(row[1]),
                'oldest_days':  int(row[2]) if row[2] is not None else 0,
            }
            for row in rows
        ]

    except Exception as e:
        _err('supplier_problems', e)
        return []
    finally:
        session.close()


def get_category_donut(engine):
    """
    Bugungi sotuv summasi kategoriya bo'yicha (donut grafik uchun).
    Top 5 kategoriya + qolgan hammasi 'Boshqalar' sifatida birlashtiriladi.
    010/011 va Пакет% chiqarib tashlanadi.

    Qaytariladi (list of dict):
        kategoriya, summa, foiz
    """
    session = db_manager.Session()
    try:
        rows = session.execute(text("""
            SELECT
                COALESCE(NULLIF(TRIM("Категория"), ''), 'Boshqa') AS kategoriya,
                COALESCE(SUM("Продажи со скидкой с учетом возвратов"), 0) AS summa
            FROM f_sotuvlar
            WHERE date("Дата") = date('now')
              AND "Артикул" NOT LIKE '010%'
              AND "Артикул" NOT LIKE '011%'
              AND "Наименование" NOT LIKE 'Пакет%'
            GROUP BY kategoriya
            ORDER BY summa DESC
        """)).fetchall()

        if not rows:
            return []

        # Jami summani hisoblaymiz
        total = sum(float(row[1]) for row in rows)
        if total == 0:
            return []

        # Top 5 ni ajratamiz
        top5 = rows[:5]
        rest = rows[5:]

        result = []
        for row in top5:
            summa = float(row[1])
            result.append({
                'kategoriya': row[0],
                'summa':      round(summa, 2),
                'foiz':       round(summa / total * 100, 1),
            })

        # Qolgan kategoriyalarni 'Boshqalar' sifatida yig'amiz
        if rest:
            rest_sum = sum(float(r[1]) for r in rest)
            result.append({
                'kategoriya': 'Boshqalar',
                'summa':      round(rest_sum, 2),
                'foiz':       round(rest_sum / total * 100, 1),
            })

        return result

    except Exception as e:
        _err('category_donut', e)
        return []
    finally:
        session.close()


def get_mtd_marja(engine):
    """
    Oy boshidan hozirgacha (MTD) valovoy marja foizi.
    O'tgan oyning xuddi shu davri bilan taqqoslaydi.

    Qaytariladi (dict):
        marja_pct       — joriy MTD marja % (float)
        gross_profit    — valovoy foyda (float)
        sotuv_summa     — jami sotuv summasi (float)
        prev_marja_pct  — o'tgan oy xuddi shu davr marja % (float)
        delta           — farq (float, musbat = o'sish)
        month_start     — oy boshi sanasi (str)
        today           — bugun sanasi (str)
        day_of_month    — oyning necha-kuni (int)
        days_in_month   — oydagi jami kunlar (int)
    """
    from datetime import timedelta
    import calendar as _cal

    today_d = date.today()
    month_start = today_d.replace(day=1)

    prev_month_last = month_start - timedelta(days=1)
    prev_month_start = prev_month_last.replace(day=1)
    prev_days_in_month = _cal.monthrange(prev_month_start.year, prev_month_start.month)[1]
    prev_same_day = prev_month_start.replace(day=min(today_d.day, prev_days_in_month))

    empty = {
        'marja_pct': 0.0, 'gross_profit': 0.0, 'sotuv_summa': 0.0,
        'prev_marja_pct': 0.0, 'delta': 0.0,
        'month_start': str(month_start), 'today': str(today_d),
        'day_of_month': today_d.day,
        'days_in_month': _cal.monthrange(today_d.year, today_d.month)[1],
    }

    session = db_manager.Session()
    try:
        # 010/011 aksiya tovarlar KIRITILADI — analytics bilan bir xil formula
        row = session.execute(text("""
            SELECT
                COALESCE(SUM("Валовая прибыль"), 0),
                COALESCE(SUM("Продажи со скидкой с учетом возвратов"), 0)
            FROM f_sotuvlar
            WHERE date("Дата") >= :ms AND date("Дата") <= :td
              AND "Наименование" NOT LIKE 'Пакет%'
        """), {'ms': str(month_start), 'td': str(today_d)}).fetchone()

        gross = float(row[0])
        sotuv = float(row[1])
        marja_pct = round(gross / sotuv * 100, 1) if sotuv > 0 else 0.0

        row2 = session.execute(text("""
            SELECT
                COALESCE(SUM("Валовая прибыль"), 0),
                COALESCE(SUM("Продажи со скидкой с учетом возвратов"), 0)
            FROM f_sotuvlar
            WHERE date("Дата") >= :ps AND date("Дата") <= :pe
              AND "Наименование" NOT LIKE 'Пакет%'
        """), {'ps': str(prev_month_start), 'pe': str(prev_same_day)}).fetchone()

        prev_gross = float(row2[0])
        prev_sotuv = float(row2[1])
        prev_marja = round(prev_gross / prev_sotuv * 100, 1) if prev_sotuv > 0 else 0.0

        days_in_month = _cal.monthrange(today_d.year, today_d.month)[1]

        has_prev = prev_sotuv > 0

        return {
            'marja_pct':      marja_pct,
            'gross_profit':   gross,
            'sotuv_summa':    sotuv,
            'prev_marja_pct': prev_marja,
            'delta':          round(marja_pct - prev_marja, 1) if has_prev else None,
            'has_prev':       has_prev,
            'month_start':    str(month_start),
            'today':          str(today_d),
            'day_of_month':   today_d.day,
            'days_in_month':  days_in_month,
        }

    except Exception as e:
        _err('mtd_marja', e)
        return empty
    finally:
        session.close()


def get_dead_stock(engine, limit=15):
    """
    30 kun ichida birorta ham sotilmagan, lekin omborda qoldig'i bor tovarlar.
    Muzlagan kapital qiymatiga ko'ra kamayish tartibida.

    Qaytariladi (list of dict):
        artikul, naim, kategoriya, qoldiq, narx, jami_summa
    """
    session = db_manager.Session()
    try:
        rows = session.execute(text("""
            SELECT
                q."Артикул"                                              AS artikul,
                MAX(q."Наименование")                                    AS naim,
                COALESCE(NULLIF(TRIM(MAX(q."Категория")), ''), 'Boshqa') AS kategoriya,
                SUM(q."Кол-во")                                          AS qoldiq,
                MAX(q."Цена поставки")                                   AS narx,
                SUM(q."Кол-во") * MAX(q."Цена поставки")                AS jami_summa
            FROM f_qoldiqlar q
            WHERE date(q."Дата") = (SELECT MAX(date("Дата")) FROM f_qoldiqlar)
              AND q."Артикул" NOT LIKE '010%'
              AND q."Артикул" NOT LIKE '011%'
              AND q."Наименование" NOT LIKE 'Пакет%'
              AND q."Кол-во" > 0
              AND q."Артикул" NOT IN (
                  SELECT DISTINCT "Артикул"
                  FROM f_sotuvlar
                  WHERE date("Дата") >= date('now', '-30 days')
                    AND "Продано за вычетом возвратов" > 0
              )
            GROUP BY q."Артикул"
            ORDER BY jami_summa DESC
            LIMIT :lim
        """), {'lim': limit}).fetchall()

        return [
            {
                'artikul':    row[0],
                'naim':       row[1],
                'kategoriya': row[2],
                'qoldiq':     float(row[3]),
                'narx':       float(row[4]) if row[4] else 0.0,
                'jami_summa': float(row[5]) if row[5] else 0.0,
            }
            for row in rows
        ]

    except Exception as e:
        _err('dead_stock', e)
        return []
    finally:
        session.close()


def get_supplier_rating(engine, limit=12):
    """
    Supplierlar samaradorlik reytingi — generated_orders asosida.
    Jami zakaz, bajarildi soni, completion rate, kutilmoqda.

    Qaytariladi (list of dict):
        supplier, jami_zakaz, bajarildi, completion_rate, kutilmoqda, investitsiya_mln
    """
    session = db_manager.Session()
    try:
        rows = session.execute(text("""
            SELECT
                supplier,
                COUNT(*)                                                          AS jami_zakaz,
                SUM(CASE WHEN status != 'Kutilmoqda' THEN 1 ELSE 0 END)          AS bajarildi,
                ROUND(
                    SUM(CASE WHEN status != 'Kutilmoqda' THEN 1 ELSE 0 END)
                    * 100.0 / COUNT(*), 1
                )                                                                 AS completion_rate,
                SUM(CASE WHEN status = 'Kutilmoqda' THEN 1 ELSE 0 END)           AS kutilmoqda,
                ROUND(
                    COALESCE(SUM(CAST(supply_price AS REAL) * CAST(quantity AS REAL)), 0)
                    / 1000000.0, 1
                )                                                                 AS investitsiya_mln
            FROM generated_orders
            WHERE supplier IS NOT NULL
              AND TRIM(supplier) != ''
            GROUP BY supplier
            ORDER BY jami_zakaz DESC, completion_rate DESC
            LIMIT :lim
        """), {'lim': limit}).fetchall()

        return [
            {
                'supplier':          row[0],
                'jami_zakaz':        int(row[1]),
                'bajarildi':         int(row[2]),
                'completion_rate':   float(row[3]) if row[3] is not None else 0.0,
                'kutilmoqda':        int(row[4]),
                'investitsiya_mln':  float(row[5]) if row[5] is not None else 0.0,
            }
            for row in rows
        ]

    except Exception as e:
        _err('supplier_rating', e)
        return []
    finally:
        session.close()
