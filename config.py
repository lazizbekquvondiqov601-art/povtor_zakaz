# config.py
import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# --- BOT SOZLAMALARI ---
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", 1205534758))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ARCHIVE_CHANNEL_ID = int(os.getenv("ARCHIVE_CHANNEL_ID", -1003971521196))

# Admin ID'larni string'dan integer list'ga o'tkazish
try:
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in os.getenv("ADMIN_IDS", "").split(',')]
except (ValueError, AttributeError):
    ADMIN_IDS = []

# --- BAZA VA FAYLLAR ---
POSTGRES_URL = os.getenv("DATABASE_URL") or "sqlite:///Data_Model.db"
DB_PATH = "database/Data_Model.db"
PRODUCTS_JSON_FILE = "products_cataloglar.json"
LAST_SYNC_FILE = "database/catalog_last_sync.txt"

# --- BILLZ API ---
BILLZ_SECRET_KEY = os.getenv("BILLZ_SECRET_KEY")
ALL_SHOPS_IDS = os.getenv("BILLZ_SHOP_IDS")

# --- WEB PANEL ---
WEB_URL = os.getenv("WEB_URL", "").rstrip("/")

# --- BIZNES LOGIKA ---
AKSIYA_PREFIXES = ('010', '011')
EXCLUDED_NAMES = ('Пакет',)
DONA_CATEGORIES = {'Аксессуары', 'Головной убор', 'Игрушка', 'Нижнее белье'}

# Tekshiruv
if not all([TELEGRAM_BOT_TOKEN, BILLZ_SECRET_KEY, ALL_SHOPS_IDS, POSTGRES_URL]):
    print("OGOHLANTIRISH: .env faylidagi ba'zi o'zgaruvchilar to'ldirilmagan!")

