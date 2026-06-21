import pandas as pd
from datetime import datetime, timedelta, timezone
import io
from sqlalchemy import text, create_engine, event, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool
import config
from .models import Base, InvitedUser, Supplier, AllowedUser, Admin, Setting, GeneratedOrder, SupplierNameHistory, BlockedUser

# --- VAQT SOZLAMASI (TASHKENT UTC+5) ---
TASHKENT_TZ = timezone(timedelta(hours=5))

# --- DB SESSIYASI ---
# NullPool: har bir so'rovdan keyin connection yopiladi, RAM tejash uchun
_is_sqlite = config.POSTGRES_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
engine = create_engine(config.POSTGRES_URL, connect_args=_connect_args, poolclass=NullPool)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

Session = sessionmaker(bind=engine)
# --- FUNKSIYALAR ---

def init_db():
    try:
        Base.metadata.create_all(engine)
        session = Session()
        try:
            if session.query(Setting).count() == 0:
                print("⚙️ Standart sozlamalar kiritilmoqda...")
                defaults = [
                    Setting(rule_name='m1_min_days', rule_value=16.0),
                    Setting(rule_name='m1_max_days', rule_value=20.0),
                    Setting(rule_name='m1_percentage', rule_value=80.0),
                    Setting(rule_name='m2_min_days', rule_value=11.0),
                    Setting(rule_name='m2_max_days', rule_value=15.0),
                    Setting(rule_name='m2_percentage', rule_value=70.0),
                    Setting(rule_name='m3_min_days', rule_value=6.0),
                    Setting(rule_name='m3_max_days', rule_value=10.0),
                    Setting(rule_name='m3_percentage', rule_value=60.0),
                    Setting(rule_name='m4_min_days', rule_value=1.0),
                    Setting(rule_name='m4_max_days', rule_value=5.0),
                    Setting(rule_name='m4_percentage', rule_value=30.0),
                ]
                session.add_all(defaults)
                session.commit()
        finally:
            session.close()

        # --- JINS (ПОЛ) USTUNINI QOLDIQ JADVALIGA QO'SHISH ---
        try:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE f_qoldiqlar ADD COLUMN "Пол" TEXT'))
        except Exception:
            pass # Agar allaqachon bor bo'lsa indamaydi

        # --- generated_orders ga product_id USTUNINI QO'SHISH (migration) ---
        # Eski bazalarda bu ustun bo'lmaydi. create_all yangi jadvalda yaratadi,
        # lekin mavjud jadvalga ustun qo'shmaydi — shuning uchun ALTER TABLE shart.
        # Agar ustun allaqachon mavjud bo'lsa, ALTER xato beradi va except yutadi.
        try:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE generated_orders ADD COLUMN "product_id" TEXT'))
        except Exception:
            pass

        try:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE d_mahsulotlar ADD COLUMN promo_price REAL'))
        except Exception:
            pass

        print("✅ Baza to'liq tayyor.")
    except Exception as e:
        print(f"❌ Bazani yaratishda xatolik: {e}")

def is_allowed(telegram_id: int) -> bool:
    session = Session()
    try:
        return session.query(AllowedUser).filter_by(telegram_id=telegram_id).first() is not None
    finally:
        session.close()

def toggle_allow_user(telegram_id: int, allow: bool):
    session = Session()
    try:
        user = session.query(AllowedUser).filter_by(telegram_id=telegram_id).first()
        if allow:
            if not user: session.add(AllowedUser(telegram_id=telegram_id))
        else:
            if user: session.delete(user)
        session.commit()
    finally:
        session.close()

def get_suppliers_with_orders() -> set:
    try:
        df = pd.read_sql("SELECT DISTINCT supplier FROM generated_orders WHERE status = 'Kutilmoqda'", engine)
        if not df.empty:
            return set(df['supplier'].str.replace('\u00A0', ' ', regex=False).str.strip().dropna())
        return set()
    except Exception as e:
        print(f"Xatolik (get_suppliers): {e}")
        return set()

def get_unassigned_suppliers() -> list[str]:
    return sorted(list(get_suppliers_with_orders()))

def is_admin(telegram_id: int) -> bool:
    # 1. Super Adminni tekshiramiz
    if telegram_id == config.SUPER_ADMIN_ID:
        return True
        
    # 2. .env fayldagi ADMIN_IDS ro'yxatini tekshiramiz
    if telegram_id in config.ADMIN_IDS:
        return True
        
    # 3. Bazadagi adminlarni tekshiramiz (agar bazaga qo'shilgan bo'lsa)
    session = Session()
    try:
        return session.query(Admin).filter_by(telegram_id=telegram_id).first() is not None
    finally:
        session.close()

def invite_users(telegram_ids: list[int]) -> tuple[int, int]:
    session = Session()
    added_count, exist_count = 0, 0
    try:
        for tid in telegram_ids:
            if not session.query(InvitedUser).filter_by(telegram_id=tid).first():
                session.add(InvitedUser(telegram_id=tid))
                added_count += 1
            else:
                exist_count += 1
        session.commit()
        return added_count, exist_count
    finally:
        session.close()

def check_invitation(telegram_id: int) -> InvitedUser | None:
    session = Session()
    try:
        return session.query(InvitedUser).filter_by(telegram_id=telegram_id, is_registered=False).first()
    finally:
        session.close()

def register_supplier(telegram_id: int, supplier_name: str) -> bool:
    session = Session()
    try:
        cleaned_name = supplier_name.replace('\u00A0', ' ').strip()
        
        # Nom bandligini tekshirmaymiz, shunchaki yangisini qo'shamiz yoki yangilaymiz
        existing_supplier = session.query(Supplier).filter_by(telegram_id=telegram_id).first()
        if existing_supplier:
            existing_supplier.name = cleaned_name
        else:
            new_supplier = Supplier(name=cleaned_name, telegram_id=telegram_id)
            session.add(new_supplier)
            
        invited_user = session.query(InvitedUser).filter_by(telegram_id=telegram_id).first()
        if invited_user:
            invited_user.is_registered = True
            
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False
    finally:
        session.close()

def get_supplier_by_id(telegram_id: int) -> Supplier | None:
    session = Session()
    try:
        return session.query(Supplier).filter_by(telegram_id=telegram_id).first()
    finally:
        session.close()

def update_supplier_name(telegram_id: int, new_name: str) -> tuple[bool, str | None]:
    session = Session()
    try:
        cleaned_new_name = new_name.replace('\u00A0', ' ').strip()
        supplier = session.query(Supplier).filter_by(telegram_id=telegram_id).first()
        if not supplier: return False, None

        old_name = supplier.name
        
        # Tarixga yozish (log uchun)
        history_log = SupplierNameHistory(
            telegram_id=telegram_id, old_name=old_name, new_name=cleaned_new_name
        )
        session.add(history_log)
        
        # --- O'ZGARISH SHU YERDA ---
        # 1. Faqat Supplier (Foydalanuvchi) ismini yangilaymiz.
        # U endi yangi nomdagi zakazlarni ko'radi.
        supplier.name = cleaned_new_name
        
        # 2. generated_orders JADVALIGA TEGMAYMIZ! 
        # (Eski kodda bu yerda session.execute(...) bor edi, uni o'chirdik).
        
        session.commit()
        return True, old_name
    except IntegrityError:
        session.rollback()
        return False, None
    finally:
        session.close()

def get_all_settings() -> dict:
    session = Session()
    try:
        settings = session.query(Setting).all()
        return {s.rule_name: s.rule_value for s in settings}
    except Exception as e:
        # Jadval yo'q (Railway da bot hali init_db qilmagan) — bo'sh sozlamalar
        print(f"❌ get_all_settings xatolik: {e}")
        return {}
    finally:
        session.close()

def update_setting(rule_name: str, new_value: float) -> bool:
    session = Session()
    try:
        setting = session.query(Setting).filter_by(rule_name=rule_name).first()
        if not setting: return False
        setting.rule_value = new_value
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()

def update_order_status(artikul: str, new_status: str) -> bool:
    session = Session()
    try:
        orders = session.query(GeneratedOrder).filter(
            (GeneratedOrder.artikul == artikul) | (GeneratedOrder.zakaz_id == artikul),
            GeneratedOrder.status == 'Kutilmoqda'
        ).all()
        if not orders: return False
        for order in orders:
            order.status = new_status
        session.commit()
        return True
    except Exception as e:
        print(f"❌ Status yangilashda xatolik: {e}")
        session.rollback()
        return False
    finally:
        session.close()
        
def get_full_report_data() -> pd.DataFrame:
    try:
        query = "SELECT * FROM generated_orders ORDER BY created_at DESC"
        df = pd.read_sql(query, engine)
        if 'id' in df.columns: df = df.drop(columns=['id'])
        
        rename_map = {
            'zakaz_id': 'Zakaz ID', 'supplier': 'Yetkazib beruvchi', 'artikul': 'Artikul',
            'category': 'Kategoriya', 'subcategory': 'Podkategoriya', 'shop': 'Do\'kon',
            'color': 'Rang (Sana)', 'quantity': 'Pochka Soni', 'supply_price': 'Sotuv Narxi',
            'hozirgi_qoldiq': 'Qoldiq', 'prodano': 'Yangi Sotuv', 'days_passed': 'Kun o\'tdi',
            'ortacha_sotuv': 'O\'rtacha kunlik', 'kutilyotgan_sotuv': 'Haftalik prognoz',
            'tovar_holati': 'Holat', 'import_date': 'Kelgan Sana', 'created_at': 'Yaratilgan Sana',
            'status': 'Status'
        }
        return df.rename(columns=rename_map)
    except Exception as e:
        print(f"❌ Hisobot olishda xatolik: {e}")
        return pd.DataFrame()

def get_pending_orders_for_reminder(hours: int = 24) -> list:
    session = Session()
    try:
        now_tashkent = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
        time_threshold = now_tashkent - timedelta(hours=hours)
        
        orders = session.query(GeneratedOrder).filter(
            GeneratedOrder.status == 'Kutilmoqda',
            GeneratedOrder.created_at < time_threshold.date()
        ).all()

        if not orders: return []

        unique_reminders = {}
        supplier_names = {o.supplier for o in orders}
        suppliers_db = session.query(Supplier).filter(Supplier.name.in_(supplier_names)).all()
        
        supplier_map = {}
        for s in suppliers_db:
            if s.name not in supplier_map: supplier_map[s.name] = []
            supplier_map[s.name].append(s.telegram_id)

        for order in orders:
            tids = supplier_map.get(order.supplier, [])
            for tid in tids:
                key = (tid, order.artikul)
                if key not in unique_reminders:
                    unique_reminders[key] = {
                        "telegram_id": tid,
                        "artikul": order.artikul,
                        "subcategory": order.subcategory
                    }
        return list(unique_reminders.values())
    except Exception as e:
        print(f"❌ Eslatmalarni olishda xatolik: {e}")
        return []
    finally:
        session.close()

# --- FILTRLASH FUNKSIYALARI (TO'G'RILANGAN) ---

def get_unassigned_categories() -> list[str]:
    session = Session()
    try:
        # --- O'ZGARISH: registered_list FILTRINI OLIB TASHLADIK ---
        query = session.query(GeneratedOrder.category).filter(
            GeneratedOrder.category != None,
            GeneratedOrder.status == 'Kutilmoqda'
        ).distinct()
        return sorted([r[0] for r in query.all() if r[0]])
    finally:
        session.close()

def get_unassigned_subcategories(category_name: str) -> list[str]:
    session = Session()
    try:
        # --- O'ZGARISH: registered_list FILTRINI OLIB TASHLADIK ---
        query = session.query(GeneratedOrder.subcategory).filter(
            GeneratedOrder.category == category_name,
            GeneratedOrder.status == 'Kutilmoqda'
        ).distinct()
        return sorted([r[0] for r in query.all() if r[0]])
    finally:
        session.close()

def get_unassigned_suppliers_by_filter(category: str, subcategory: str) -> list[str]:
    """
    Kategoriya va Podkategoriya bo'yicha filtrlab, supplierlarni qaytaradi.
    """
    session = Session()
    try:
        cat_clean = category.strip()
        sub_clean = subcategory.strip()

        query = session.query(GeneratedOrder.supplier).filter(
            GeneratedOrder.category == cat_clean,
            GeneratedOrder.subcategory == sub_clean,
            GeneratedOrder.status == 'Kutilmoqda'
        ).distinct()

        suppliers = set()
        for row in query.all():
            if row[0]:
                clean_name = row[0].replace('\u00A0', ' ').strip()
                suppliers.add(clean_name)

        return sorted(list(suppliers))
    except Exception as e:
        print(f"❌ Filtrda xatolik: {e}")
        return []
    finally:
        session.close()




# --- ADMIN STATISTIKASI UCHUN YANGI FUNKSIYALAR ---

def get_supplier_stats_detailed(telegram_id: int):
    """
    Yetkazib beruvchi uchun: Kategoriya va Podkategoriya bo'yicha pochkalarni hisoblaydi.
    """
    session = Session()
    try:
        supplier = session.query(Supplier).filter_by(telegram_id=telegram_id).first()
        if not supplier:
            return []

        results = session.query(
            GeneratedOrder.category,
            GeneratedOrder.subcategory,
            func.sum(GeneratedOrder.quantity)
        ).filter(
            GeneratedOrder.supplier == supplier.name,
            GeneratedOrder.status == 'Kutilmoqda'
        ).group_by(
            GeneratedOrder.category,
            GeneratedOrder.subcategory
        ).all()

        return results
    finally:
        session.close()

def get_stat_categories_global():
    """Faqat 'Kutilmoqda' statusidagi bor Kategoriyalar ro'yxatini qaytaradi"""
    session = Session()
    try:
        query = session.query(GeneratedOrder.category).filter(
            GeneratedOrder.status == 'Kutilmoqda'
        ).distinct()
        return sorted([r[0] for r in query.all() if r[0]])
    finally:
        session.close()

def get_stat_subcategories_global(category):
    """Tanlangan Kategoriya ichidagi Podkategoriyalar ro'yxati"""
    session = Session()
    try:
        query = session.query(GeneratedOrder.subcategory).filter(
            GeneratedOrder.category == category,
            GeneratedOrder.status == 'Kutilmoqda'
        ).distinct()
        return sorted([r[0] for r in query.all() if r[0]])
    finally:
        session.close()

def get_stat_total_packs(category, subcategory):
    """Aniq bir turdagi tovarning umumiy pochka soni"""
    session = Session()
    try:
        total = session.query(func.sum(GeneratedOrder.quantity)).filter(
            GeneratedOrder.category == category,
            GeneratedOrder.subcategory == subcategory,
            GeneratedOrder.status == 'Kutilmoqda'
        ).scalar()
        return total or 0
    finally:
        session.close()


# --- YANGI QO'SHILGAN: IMPORT TAHLILI FUNKSIYALARI ---

def get_stats_by_import_days(min_day, max_day, category=None):
    """
    Kun oralig'i bo'yicha GLOBAL qidiruv.
    Supplier nomiga qarab filtrlamaydi!
    """
    session = Session()
    try:
        query = session.query(GeneratedOrder).filter(
            GeneratedOrder.status == 'Kutilmoqda',
            GeneratedOrder.days_passed >= min_day,
            GeneratedOrder.days_passed <= max_day
        )

        if category is None:
            # Kategoriyalarni olish
            results = query.with_entities(GeneratedOrder.category).distinct().all()
        else:
            # Podkategoriyalarni olish
            results = query.filter(GeneratedOrder.category == category).with_entities(GeneratedOrder.subcategory).distinct().all()

        return sorted([r[0] for r in results if r[0]])
    finally:
        session.close()

def get_import_orders_detailed(min_day, max_day, category, subcategory):
    """
    Kartochkalar chiqarish uchun kerakli BARCHA ma'lumotni 
    Pandas DataFrame shaklida qaytaradi.
    """
    try:
        query = """
        SELECT * FROM generated_orders 
        WHERE status = 'Kutilmoqda' 
          AND days_passed >= :min_d
          AND days_passed <=  :max_d
          AND category = :cat
          AND subcategory = :sub
        """
        params = {
            "min_d": min_day, 
            "max_d": max_day, 
            "cat": category, 
            "sub": subcategory
        }
        
        return pd.read_sql(query, engine, params=params)
    except Exception as e:
        print(f"❌ Import detallarini olishda xatolik: {e}")
        return pd.DataFrame()
# --- YANGI QISM: BLOKLASH VA GLOBAL QULF ---

# 1. Botni yopish/ochish (Sozlamalar jadvaliga yozamiz)
def set_global_lock(is_locked: bool):
    """True = Yopish, False = Ochish"""
    val = 1.0 if is_locked else 0.0
    if not update_setting('global_lock', val):
        session = Session()
        try:
            session.add(Setting(rule_name='global_lock', rule_value=val))
            session.commit()
        finally:
            session.close()

def is_global_locked() -> bool:
    settings = get_all_settings()
    return settings.get('global_lock', 0.0) == 1.0

# 2. Userni bloklash
def toggle_block_user(telegram_id: int, block: bool):
    session = Session()
    try:
        user = session.query(BlockedUser).filter_by(telegram_id=telegram_id).first()
        if block:
            if not user: session.add(BlockedUser(telegram_id=telegram_id))
        else:
            if user: session.delete(user)
        session.commit()
        return True
    except:
        return False
    finally:
        session.close()

def is_blocked(telegram_id: int) -> bool:
    session = Session()
    try:
        return session.query(BlockedUser).filter_by(telegram_id=telegram_id).first() is not None
    finally:
        session.close()

# --- KANAL UCHUN MA'LUMOT OLISH ---
def get_confirmed_order_details(artikul: str):
    """
    Kanalga yuborish uchun 'Topdim' bo'lgan tovarning to'liq tafsilotlarini oladi.
    """
    try:
        query = """
        SELECT supplier, shop, color, quantity, photo, supply_price
        FROM generated_orders 
        WHERE artikul = :artikul AND status = 'Topdim'
        """
        df = pd.read_sql(query, engine, params={"artikul": artikul})
        return df
    except Exception as e:
        print(f"❌ Kanal ma'lumotini olishda xatolik: {e}")
        return pd.DataFrame()

# --- ENG OXIRGI SANADAGI QOLDIQLARNI HISOB-KITOB QILISH ---

def get_stock_report_by_date(target_date: str) -> tuple[dict, dict]:
    """Tanlangan sanadagi qoldiqlarni kategoriya bo'yicha qaytaradi."""
    session = Session()
    try:
        params = {"target_date": target_date}
        query_asosiy = text('''
            SELECT 
                COALESCE(NULLIF(TRIM("Категория"), ''), 'Boshqa tovarlar') as kat,
                SUM("Кол-во") as total_qty
            FROM f_qoldiqlar
            WHERE date("Дата") = :target_date
              AND "Артикул" NOT LIKE '010%'
              AND "Артикул" NOT LIKE '011%'
            GROUP BY kat
        ''')
        query_aksiya = text('''
            SELECT 
                COALESCE(NULLIF(TRIM("Категория"), ''), 'Boshqa tovarlar') as kat,
                SUM("Кол-во") as total_qty
            FROM f_qoldiqlar
            WHERE date("Дата") = :target_date
              AND ("Артикул" LIKE '010%' OR "Артикул" LIKE '011%')
            GROUP BY kat
        ''')
        
        asosiy_rows = session.execute(query_asosiy, params).fetchall()
        aksiya_rows = session.execute(query_aksiya, params).fetchall()
        
        asosiy = {kat: {"qty": float(qty or 0), "profit": 0} for kat, qty in asosiy_rows}
        aksiya = {kat: {"qty": float(qty or 0), "profit": 0} for kat, qty in aksiya_rows}
        
        return asosiy, aksiya
    except Exception as e:
        print(f"❌ Qoldiq hisobotida xatolik: {e}")
        return {}, {}
    finally:
        session.close()



def get_max_stock_date_str() -> str:
    """f_qoldiqlar jadvalidagi eng oxirgi sanani aniqlaydi"""
    session = Session()
    try:
        result = session.execute(text('SELECT MAX("Дата") FROM f_qoldiqlar')).scalar()
        if result:
            if isinstance(result, str):
                return result.split(" ")[0]
            return pd.to_datetime(result).strftime("%Y-%m-%d")
        return datetime.now().strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")
    finally:
        session.close()

def get_stock_categories_on_max_date() -> list[str]:
    """Eng oxirgi sanadagi barcha unikal Kategoriyalarni qaytaradi"""
    session = Session()
    try:
        max_date = get_max_stock_date_str()
        
        # --- LIKE o'rniga toza date() funksiyasi ishlatildi ---
        query = text('''
            SELECT DISTINCT "Категория" 
            FROM f_qoldiqlar 
            WHERE date("Дата") = :max_date
        ''')
        
        results = session.execute(query, {"max_date": max_date}).fetchall()
        return sorted([r[0] for r in results if r[0]])
    except Exception as e:
        print(f"Kategoriyalarni olishda xato: {e}")
        return []
    finally:
        session.close()



# --- QOLDIQLAR UCHUN VAQT VA KATEGORIYA SO'ROVLARI ---

def get_last_7_stock_dates() -> list[str]:
    """f_qoldiqlar jadvalidagi oxirgi 7 ta unikal sanani qaytaradi"""
    session = Session()
    try:
        query = text('''
            SELECT DISTINCT date("Дата") as d 
            FROM f_qoldiqlar 
            WHERE "Дата" IS NOT NULL
            ORDER BY d DESC 
            LIMIT 7
        ''')
        results = session.execute(query).fetchall()
        return [r[0] for r in results if r[0]]
    except Exception as e:
        print(f"Sanalarni olishda xato: {e}")
        return []
    finally:
        session.close()

def get_stock_categories_on_date(target_date: str) -> list[str]:
    """Tanlangan sanadagi barcha unikal Kategoriyalarni qaytaradi"""
    session = Session()
    try:
        query = text('''
            SELECT DISTINCT "Категория" 
            FROM f_qoldiqlar 
            WHERE date("Дата") = :target_date
        ''')
        results = session.execute(query, {"target_date": target_date}).fetchall()
        return sorted([r[0] for r in results if r[0]])
    except Exception as e:
        print(f"Kategoriyalarni olishda xato: {e}")
        return []
    finally:
        session.close()

def get_stock_subcategories_summary_v2(category: str, target_date: str) -> tuple[list[tuple[str, str, float]], list[tuple[str, str, float]]]:
    """Tanlangan sana va kategoriya bo'yicha qoldiqlarni jinsi bilan birga qaytaradi"""
    session = Session()
    try:
        # ASOSIY tovarlar: 010 va 011 bilan BOSHLANMAGANLAR
        query_asosiy = text('''
            SELECT "Подкатегория", "Пол", SUM("Кол-во") as total_qty
            FROM f_qoldiqlar
            WHERE "Категория" = :category
              AND date("Дата") = :target_date
              AND "Артикул" NOT LIKE '010%'
              AND "Артикул" NOT LIKE '011%'
            GROUP BY "Подкатегория", "Пол"
            ORDER BY total_qty DESC
        ''')
        
        # AKSIYA tovarlar: faqat 010 va 011 bilan boshlanganlar
        query_aksiya = text('''
            SELECT "Подкатегория", "Пол", SUM("Кол-во") as total_qty
            FROM f_qoldiqlar
            WHERE "Категория" = :category
              AND date("Дата") = :target_date
              AND ("Артикул" LIKE '010%' OR "Артикул" LIKE '011%')
            GROUP BY "Подкатегория", "Пол"
            ORDER BY total_qty DESC
        ''')
        
        res_asosiy = session.execute(query_asosiy, {"category": category, "target_date": target_date}).fetchall()
        res_aksiya = session.execute(query_aksiya, {"category": category, "target_date": target_date}).fetchall()
        
        # Python orqali bo'sh maydonlarni tozalash va dublikatlarni birlashtirish (SQL xatolaridan himoyalaydi)
        def process_rows(rows):
            merged = {}
            for r in rows:
                sub = str(r[0] or "").strip()
                if not sub:
                    sub = "Boshqa"
                gender = str(r[1] or "Универсал").strip()
                qty = float(r[2] or 0)
                
                key = (sub, gender)
                merged[key] = merged.get(key, 0.0) + qty
                
            sorted_list = [(k[0], k[1], v) for k, v in merged.items()]
            return sorted(sorted_list, key=lambda x: x[2], reverse=True)

        list_asosiy = process_rows(res_asosiy)
        list_aksiya = process_rows(res_aksiya)
        
        return list_asosiy, list_aksiya
    except Exception as e:
        print(f"Batafsil qoldiq hisoblashda xatolik: {e}")
        return [], []
    finally:
        session.close()

def get_all_stock_summary_for_excel(target_date: str) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Tanlangan sana bo'yicha barcha qoldiqlarni Excel uchun tayyorlaydi"""
    session = Session()
    try:
        query_asosiy_raw = text('''
            SELECT 
                "Подкатегория",
                "Категория",
                "Пол",
                "Кол-во"
            FROM f_qoldiqlar
            WHERE date("Дата") = :target_date 
              AND "Артикул" NOT LIKE '010%'
              AND "Артикул" NOT LIKE '011%'
        ''')
        
        query_aksiya_raw = text('''
            SELECT 
                "Подкатегория",
                "Категория",
                "Пол",
                "Кол-во"
            FROM f_qoldiqlar
            WHERE date("Дата") = :target_date 
              AND ("Артикул" LIKE '010%' OR "Артикул" LIKE '011%')
        ''')
        
        df_raw_asosiy = pd.read_sql(query_asosiy_raw, engine, params={"target_date": target_date})
        df_raw_aksiya = pd.read_sql(query_aksiya_raw, engine, params={"target_date": target_date})
        
        # Pandas yordamida tozalash va guruhlash (SQL xatoliklarining oldini oladi)
        def clean_and_aggregate(df):
            if df.empty:
                return pd.DataFrame(columns=["Подкатегория", "Категория", "Пол", "Қолдиқ (дона)"])
            
            df['Подкатегория'] = df['Подкатегория'].fillna('Boshqa').astype(str).str.strip().replace('', 'Boshqa')
            df['Категория'] = df['Категория'].fillna('Boshqa').astype(str).str.strip().replace('', 'Boshqa')
            df['Пол'] = df['Пол'].fillna('Универсал').astype(str).str.strip().replace('', 'Универсал')
            
            agg_df = df.groupby(['Подкатегория', 'Категория', 'Пол'], as_index=False)['Кол-во'].sum()
            agg_df.rename(columns={'Кол-во': 'Қолдиқ (дона)'}, inplace=True)
            return agg_df.sort_values(by=["Подкатегория", "Категория", "Пол"])

        df_asosiy = clean_and_aggregate(df_raw_asosiy)
        df_aksiya = clean_and_aggregate(df_raw_aksiya)
        
        return df_asosiy, df_aksiya, target_date
    except Exception as e:
        print(f"Excel hisobot hisoblashda xato: {e}")
        return pd.DataFrame(), pd.DataFrame(), target_date
    finally:
        session.close()


def get_sales_by_period(start_date: str, end_date: str) -> tuple:
    try:
        session = Session()
        try:
            params = {"start_date": start_date, "end_date": end_date}

            query_asosiy = text('''
                SELECT 
                    COALESCE(NULLIF(TRIM("Категория"), ''), 'Boshqa tovarlar') as kat,
                    SUM("Продано за вычетом возвратов") as total_sold,
                    SUM("Валовая прибыль") as total_profit
                FROM f_sotuvlar
                WHERE date("Дата") >= :start_date
                  AND date("Дата") <= :end_date
                  AND "Артикул" NOT LIKE '010%'
                  AND "Артикул" NOT LIKE '011%'
                  AND "Наименование" NOT LIKE 'Пакет%'
                GROUP BY kat
                ORDER BY kat
            ''')

            query_aksiya = text('''
                SELECT 
                    COALESCE(NULLIF(TRIM("Категория"), ''), 'Boshqa tovarlar') as kat,
                    SUM("Продано за вычетом возвратов") as total_sold,
                    SUM("Валовая прибыль") as total_profit
                FROM f_sotuvlar
                WHERE date("Дата") >= :start_date
                  AND date("Дата") <= :end_date
                  AND ("Артикул" LIKE '010%' OR "Артикул" LIKE '011%')
                  AND "Наименование" NOT LIKE 'Пакет%'
                GROUP BY kat
                ORDER BY kat
            ''')

            asosiy_rows = session.execute(query_asosiy, params).fetchall()
            aksiya_rows  = session.execute(query_aksiya, params).fetchall()

            asosiy = {kat: {"qty": float(qty or 0), "profit": float(prof or 0)} 
                      for kat, qty, prof in asosiy_rows}
            aksiya  = {kat: {"qty": float(qty or 0), "profit": float(prof or 0)} 
                      for kat, qty, prof in aksiya_rows}

            return asosiy, aksiya
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Sotuv tahlilida xatolik: {e}")
        return {}, {}

def get_stock_by_category() -> tuple[dict, dict]:
    try:
        session = Session()
        try:
            query_asosiy = text('''
                SELECT 
                    COALESCE(NULLIF(TRIM("Категория"), ''), 'skip') as kat,
                    SUM("Кол-во") as total_qty
                FROM f_qoldiqlar
                WHERE date("Дата") = (SELECT MAX(date("Дата")) FROM f_qoldiqlar)
                AND "Артикул" NOT LIKE '010%'
                AND "Артикул" NOT LIKE '011%'
                AND "Категория" IS NOT NULL
                AND TRIM("Категория") != ''
                GROUP BY kat
                HAVING SUM("Кол-во") > 0
                AND kat != 'skip'
                ORDER BY kat
            ''')

            query_aksiya = text('''
                SELECT 
                    COALESCE(NULLIF(TRIM("Категория"), ''), 'Boshqa tovarlar') as kat,
                    SUM("Кол-во") as total_qty
                FROM f_qoldiqlar
                WHERE date("Дата") = (SELECT MAX(date("Дата")) FROM f_qoldiqlar)
                  AND ("Артикул" LIKE '010%' OR "Артикул" LIKE '011%')
                  AND "Категория" IS NOT NULL
                  AND TRIM("Категория") != ''
                GROUP BY kat
                HAVING SUM("Кол-во") > 0
                ORDER BY kat
            ''')

            asosiy_rows = session.execute(query_asosiy).fetchall()
            aksiya_rows  = session.execute(query_aksiya).fetchall()

            asosiy_qoldiq = {kat: float(q or 0) for kat, q in asosiy_rows}
            aksiya_qoldiq = {kat: float(q or 0) for kat, q in aksiya_rows}

            return asosiy_qoldiq, aksiya_qoldiq
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Qoldiq olishda xatolik: {e}")
        return {}, {}

def generate_sklad_excel():
    """Jarayonda bo'lgan tovarlarni Skladchi uchun Excel shaklida tayyorlaydi (4 ta parametr: Kategoriya + Artikul + Rang + Narx bo'yicha moslashtiradi)"""
    try:
        # 1. Jarayonda turgan zakazlarni olamiz (status = 'Topdim')
        orders_query = "SELECT * FROM generated_orders WHERE status = 'Topdim'"
        orders_df = pd.read_sql(orders_query, engine)

        if orders_df.empty:
            return None

        # 2. Katalogdan barcha kerakli ustunlarni olamiz (Kategoriya va Narxni ham qo'shdik)
        cat_query = 'SELECT "Артикул", "Цвет", "Категория", "supply_price", "Наименование", "Материал", "Модель", "Крой", "Акция", "Вид", "Цена продажи", "Пол", "Сезон", "Размер", "Размер сетка", "Описание", "Группа_закупок" FROM d_mahsulotlar'
        cat_df = pd.read_sql(cat_query, engine)
        
        # Katalogdagi rangni tozalab olamiz
        cat_df['Цвет_toza_cat'] = cat_df['Цвет'].apply(lambda x: str(x).split('(')[0].strip() if pd.notna(x) else "")

        # 🟢 DUBLIKATLARNI 4 TA PARAMETR BO'YICHA O'CHIRAMIZ (Artikul + Kategoriya + Rang + Tan Narxi) 🟢
        cat_df = cat_df.drop_duplicates(subset=['Артикул', 'Категория', 'Цвет_toza_cat', 'supply_price']) 

        # Zakazlar jadvalidagi rangni tozalash
        def clean_color(c):
            if pd.isna(c): return ""
            return str(c).split('(')[0].strip()

        orders_df['Цвет_toza'] = orders_df['color'].apply(clean_color)

        # 🟢 MOSLASHTIRISH: 4 TA PARAMETR BIR XIL BO'LGANDA BIRLASHTIRADI 🟢
        merged_df = pd.merge(
            orders_df, 
            cat_df, 
            left_on=['artikul', 'category', 'Цвет_toza', 'supply_price'], 
            right_on=['Артикул', 'Категория', 'Цвет_toza_cat', 'supply_price'], 
            how='left'
        )

        today_str = datetime.now().strftime("I-%d.%m.%Y")

        # 4. EXCELGA TO'LDIRAMIZ
        excel_df = pd.DataFrame()
        excel_df['Дата'] = [today_str] * len(merged_df)
        excel_df['Поставщик'] = merged_df['supplier']
        excel_df['Наименование'] = merged_df['Наименование']
        excel_df['Артикул'] = merged_df['artikul']
        excel_df['Пол'] = merged_df['Пол']                 
        excel_df['Категория'] = merged_df['category']
        excel_df['Подкатегория'] = merged_df['subcategory']
        excel_df['Материал'] = merged_df['Материал']
        excel_df['Описание'] = merged_df['Описание']       
        excel_df['Модель'] = merged_df['Модель']
        excel_df['Крой'] = merged_df['Крой']
        excel_df['Группа_закупок'] = merged_df['Группа_закупок'] 
        excel_df['Акция'] = merged_df['Акция']
        excel_df['Цвет'] = merged_df['Цвет_toza']
        excel_df['Вид'] = merged_df['Вид']
        excel_df['Баркод'] = "" 
        excel_df['Сезон'] = merged_df['Сезон']             
        excel_df['Размер'] = merged_df['Размер']           
        excel_df['Размер сетка'] = merged_df['Размер сетка'] 
        excel_df['Цена поставки,'] = merged_df['supply_price']
        excel_df['Цена, UZS'] = merged_df['Цена продажи']
        excel_df['Кол-во'] = "" # Skladchi to'ldirishi uchun bo'sh qoladi

        # Excel faylga yozish
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            excel_df.to_excel(writer, index=False, sheet_name='Import_Billz')
            worksheet = writer.sheets['Import_Billz']
            for i, col in enumerate(excel_df.columns):
                worksheet.set_column(i, i, 16) 

        output.seek(0)
        return output

    except Exception as e:
        print(f"❌ Sklad uchun Excel yaratishda xato: {e}")
        return None
# 🟢 BILAN BOSHLANADIGAN KOD (db_manager.py faylining eng oxiriga qo'shing):
def add_admin_db(telegram_id: int) -> bool:
    """Yangi adminni bazaga xavfsiz qo'shadi"""
    session = Session()
    try:
        exists = session.query(Admin).filter_by(telegram_id=telegram_id).first()
        if not exists:
            session.add(Admin(telegram_id=telegram_id))
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()

# --- BOT ORQALI MAHSULOT MA'LUMOTLARINI TAHRIRLASH ---

# Adminga qaysi ustunlarni tahrirlashga ruxsat berilgan (SQL injection oldini olish uchun WHITELIST).
# Diqqat: generated_orders.color kiritilmagan — aktiv zakazlar bilan bog'lanish uziladi.
ALLOWED_EDIT_FIELDS = {"Категория", "Подкатегория", "Вид", "Материал", "Пол", "Сезон"}

# Qaysi jadvalda qaysi ustun mavjudligini ko'rsatadi (kontent jadvallari).
# Agar Billz API'dan keladigan schema o'zgarsa — bu xaritani yangilash kerak.
_EDITABLE_TABLES_COLUMNS = {
    "d_mahsulotlar": {"Категория", "Подкатегория", "Вид", "Материал", "Пол", "Сезон"},
    "f_sotuvlar":    {"Категория", "Подкатегория", "Вид", "Материал"},
    "f_qoldiqlar":   {"Категория", "Подкатегория", "Вид", "Материал", "Пол"},
}


def get_product_by_artikul(artikul: str) -> dict | None:
    """
    d_mahsulotlar dan berilgan artikul bo'yicha BIRINCHI mos satrni dict
    ko'rinishida qaytaradi (Naimenovanie, Категория va boshqa kerakli ustunlar).
    Bir artikul ostida bir nechta satr bo'lishi mumkin (turli rang/o'lcham) —
    biz ko'rsatish uchun bittasini olamiz, lekin update hamma satrlarda ishlaydi.

    Qaytaradi: dict (ustun_nomi -> qiymat) yoki None — agar topilmasa.
    """
    if not artikul:
        return None
    artikul_clean = artikul.strip()
    if not artikul_clean:
        return None

    session = Session()
    try:
        query = text(
            'SELECT "Артикул", "Наименование", "Категория", "Подкатегория", '
            '"Вид", "Материал", "Пол", "Сезон" '
            'FROM d_mahsulotlar WHERE "Артикул" = :artikul LIMIT 1'
        )
        row = session.execute(query, {"artikul": artikul_clean}).fetchone()
        if not row:
            return None
        return {
            "Артикул": row[0],
            "Наименование": row[1],
            "Категория": row[2],
            "Подкатегория": row[3],
            "Вид": row[4],
            "Материал": row[5],
            "Пол": row[6],
            "Сезон": row[7],
        }
    except Exception as e:
        print(f"ERR get_product_by_artikul: {e}")
        return None
    finally:
        session.close()


def update_product_field(artikul: str, field: str, new_value: str) -> int:
    """
    Berilgan artikul uchun BARCHA satrlarda (d_mahsulotlar + f_sotuvlar + f_qoldiqlar
    da, agar ustun mavjud bo'lsa) belgilangan field qiymatini yangilaydi.

    Args:
        artikul: tahrirlanadigan mahsulot artikuli (string)
        field: ustun nomi — faqat ALLOWED_EDIT_FIELDS ichida bo'lishi shart
        new_value: yangi qiymat (oldindan trim/normalize qilingan bo'lishi tavsiya etiladi)

    Qaytaradi: ta'sirlangan satrlar umumiy soni (barcha jadvallar bo'yicha).
    Agar field whitelist'da bo'lmasa — ValueError ko'tariladi (xavfsizlik).
    """
    if field not in ALLOWED_EDIT_FIELDS:
        raise ValueError(f"Ruxsat etilmagan field: {field!r}")

    if not artikul:
        return 0
    artikul_clean = artikul.strip()
    if not artikul_clean:
        return 0

    total_affected = 0
    # SQLAlchemy bilan engine.begin() ichida — barcha UPDATE bir tranzaksiyada
    try:
        with engine.begin() as conn:
            for table_name, cols in _EDITABLE_TABLES_COLUMNS.items():
                if field not in cols:
                    continue
                # SQL injection xavfsizligi:
                #   - table_name xardkod dict'dan keladi (foydalanuvchidan emas)
                #   - field oldin ALLOWED_EDIT_FIELDS bilan tekshirilgan
                #   - artikul va new_value param sifatida uzatiladi (bind)
                sql = text(
                    f'UPDATE "{table_name}" '
                    f'SET "{field}" = :new_value '
                    f'WHERE "Артикул" = :artikul'
                )
                result = conn.execute(sql, {"new_value": new_value, "artikul": artikul_clean})
                total_affected += result.rowcount or 0
    except Exception as e:
        print(f"ERR update_product_field [{field}={new_value!r} for {artikul_clean!r}]: {e}")
        return 0

    return total_affected


def remove_admin_db(telegram_id: int) -> bool:
    """Adminni bazadan xavfsiz o'chiradi"""
    session = Session()
    try:
        admin = session.query(Admin).filter_by(telegram_id=telegram_id).first()
        if admin:
            session.delete(admin)
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()

def get_supplier_sales_report(supplier_name: str) -> tuple:
    """Oy boshidan hisoblaydi (Legacy logic)"""
    try:
        session = Session()
        try:
            now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d")
            end_date   = now.strftime("%Y-%m-%d")

            like_pattern = f"%{supplier_name}%"
            params = {"supplier": like_pattern, "start_date": start_date, "end_date": end_date}

            query_sotuv = text('''
                SELECT
                    COALESCE(NULLIF(TRIM(s."Категория"), ''), 'Boshqa') as kat,
                    SUM(s."Продано за вычетом возвратов") as total_sold,
                    SUM(s."Валовая прибыль") as total_profit
                FROM f_sotuvlar s
                JOIN d_mahsulotlar d ON s.product_id = d.product_id
                WHERE d."Поставщик" LIKE :supplier
                  AND date(s."Дата") >= :start_date
                  AND date(s."Дата") <= :end_date
                  AND s."Артикул" NOT LIKE '010%'
                  AND s."Артикул" NOT LIKE '011%'
                  AND s."Наименование" NOT LIKE 'Пакет%'
                GROUP BY kat
                ORDER BY total_profit DESC
            ''')

            query_qoldiq = text('''
                SELECT
                    COALESCE(NULLIF(TRIM(q."Категория"), ''), 'Boshqa') as kat,
                    SUM(q."Кол-во") as total_qty
                FROM f_qoldiqlar q
                JOIN d_mahsulotlar d ON q.product_id = d.product_id
                WHERE d."Поставщик" LIKE :supplier
                  AND date(q."Дата") = (SELECT MAX(date("Дата")) FROM f_qoldiqlar)
                  AND q."Артикул" NOT LIKE '010%'
                  AND q."Артикул" NOT LIKE '011%'
                  AND q."Категория" IS NOT NULL
                  AND TRIM(q."Категория") != ''
                GROUP BY kat
                HAVING SUM(q."Кол-во") > 0
            ''')

            sotuv_rows  = session.execute(query_sotuv,  params).fetchall()
            qoldiq_rows = session.execute(query_qoldiq, params).fetchall()

            sotuv  = {kat: {"qty": float(q or 0), "profit": float(p or 0)} for kat, q, p in sotuv_rows}
            qoldiq = {kat: float(q or 0) for kat, q in qoldiq_rows}

            return sotuv, qoldiq, start_date, end_date
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Supplier hisobotida xatolik: {e}")
        return {}, {}, "", ""


def get_all_suppliers_stats() -> pd.DataFrame:
    """
    Barcha supplierlar uchun oy boshidan beri statistika:
    sotildi, summa, foyda, artikul soni, qoldiq.
    """
    try:
        now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
        oy_boshi = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d')

        sotuv_df = pd.read_sql(text('''
            SELECT
                d."Поставщик"                                     AS supplier,
                COUNT(DISTINCT s."Артикул")                       AS artikul_count,
                SUM(s."Продано за вычетом возвратов")             AS sotildi,
                SUM(s."Продажи со скидкой с учетом возвратов")    AS summa,
                SUM(s."Валовая прибыль")                          AS foyda
            FROM f_sotuvlar s
            JOIN d_mahsulotlar d ON s.product_id = d.product_id
            WHERE d."Поставщик" IS NOT NULL
              AND d."Поставщик" != ''
              AND date(s."Дата") >= :oy_boshi
              AND s."Артикул" NOT LIKE '010%'
              AND s."Артикул" NOT LIKE '011%'
              AND s."Наименование" NOT LIKE 'Пакет%'
            GROUP BY d."Поставщик"
        '''), engine, params={'oy_boshi': oy_boshi})

        # Katalogdagi jami artikul soni (qoldiq uchun)
        qoldiq_df = pd.read_sql(text('''
            SELECT
                d."Поставщик"   AS supplier,
                SUM(q."Кол-во") AS qoldiq
            FROM f_qoldiqlar q
            JOIN d_mahsulotlar d ON q.product_id = d.product_id
            WHERE d."Поставщик" IS NOT NULL
              AND d."Поставщик" != ''
              AND date(q."Дата") = (SELECT MAX(date("Дата")) FROM f_qoldiqlar)
              AND q."Артикул" NOT LIKE '010%'
              AND q."Артикул" NOT LIKE '011%'
            GROUP BY d."Поставщик"
        '''), engine)

        if sotuv_df.empty:
            return pd.DataFrame(columns=['supplier','artikul_count','sotildi','summa','foyda','qoldiq'])

        merged = pd.merge(sotuv_df, qoldiq_df, on='supplier', how='left')
        for col in ['sotildi','summa','foyda','qoldiq']:
            merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0)
        merged = merged.sort_values('foyda', ascending=False).reset_index(drop=True)
        return merged

    except Exception as e:
        print(f"get_all_suppliers_stats xatolik: {e}")
        return pd.DataFrame()


def get_supplier_daily_chart(supplier_name: str) -> dict:
    """Supplier uchun kunlik sotuv va qoldiq (oxirgi 30 kun)."""
    try:
        now = datetime.now(TASHKENT_TZ).replace(tzinfo=None)
        oy_boshi = (now - __import__('datetime').timedelta(days=30)).strftime('%Y-%m-%d')

        sotuv = pd.read_sql(text('''
            SELECT date(s."Дата") as kun,
                   SUM(s."Продано за вычетом возвратов") as sotildi,
                   SUM(s."Валовая прибыль") as foyda
            FROM f_sotuvlar s
            JOIN d_mahsulotlar d ON s.product_id = d.product_id
            WHERE d."Поставщик" LIKE :sup
              AND date(s."Дата") >= :oy_boshi
              AND s."Артикул" NOT LIKE '010%'
              AND s."Артикул" NOT LIKE '011%'
            GROUP BY kun ORDER BY kun
        '''), engine, params={'sup': f'%{supplier_name}%', 'oy_boshi': oy_boshi})

        if sotuv.empty:
            return {}

        return {
            'labels': sotuv['kun'].tolist(),
            'sotildi': [round(float(v), 0) for v in sotuv['sotildi']],
            'foyda':   [round(float(v), 0) for v in sotuv['foyda']],
        }
    except Exception as e:
        print(f"get_supplier_daily_chart xatolik: {e}")
        return {}
        return {}, {}, "", ""