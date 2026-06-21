# 🏗 Project Architecture & AI Instructions

Ushbu loyiha Billz API orqali kiyim-kechak do'konlari uchun avtomatik zakaz (OBR) tizimini boshqaruvchi Telegram botdir.

## 📁 Loyiha Strukturasi
- `src/database/`: Barcha ma'lumotlar bazasi modellari (`models.py`) va boshqaruv funksiyalari (`db_manager.py`) shu yerda. Bu loyihaning yadrosidir.
- `src/bot/`: Botning mantiqiy qismlari:
  - `handlers/`: Admin, Super Admin, Supplier va Analytics bo'limlari uchun alohida routerlar.
  - `middlewares/`: `security.py` orqali bloklash va tizimga kirish huquqlari nazorat qilinadi.
  - `keyboards/`: Dinamik tugmalar joylashuvi.
- `data_engine.py`: Billz API bilan sinxronizatsiya qiluvchi asosiy vosita.
- `auto_zakaz.py`: OBR (Ostatki-Baza-Raschet) algoritmi hisob-kitobi.

## 🤖 AI Agentlar uchun Muhim Eslatmalar
1. **Database Layer:** Har qanday baza bilan bog'liq o'zgarishda `src/database/db_manager.py` dan foydalaning. SQL so'rovlarini bevosita handlerlar ichida yozmang.
2. **Security:** Botda `SecurityMiddleware` mavjud. U Super Admin, VIP foydalanuvchilar va bloklangan foydalanuvchilarni ajratadi. O'zgarish qilganda bu zanjirni buzmang.
3. **Billz API:** API tokeni dinamik olinadi (`get_billz_access_token`). Hech qachon statik tokenni kodga yozib qo'ymang.
4. **Keyboard UI:** Super Admin menyusi ko'p bosqichli. Muhim tugmalar (Update, Reset) `Tizim Sozlamalari` bo'limida saqlanadi.

## 🔄 Oxirgi O'zgarishlar (Iyun 2026)
- Loyiha to'liq modullashtirildi (restructuring).
- Baza sinxronizatsiyasidagi xatoliklar (missing products) tuzatildi.
- **MUHIM:** `import_date` endi API dan `custom_fields` ichidagi "Дата" maydonidan harf-sana formatida (`M-15.05.2026`) olinadi.
- **MUHIM:** Missing mahsulotlar `product_id` bo'yicha guruhlanib, sanasi `Дата2` dan tiklanadi. Prefikslarni o'chirmang.
- Supplier qidiruv tizimi optimallashtirildi.
- Super Admin interfeysi UX/UI jihatdan yaxshilandi.
