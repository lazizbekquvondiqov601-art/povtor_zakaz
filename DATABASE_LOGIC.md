# 📊 Database Logic & OBR Algorithm

Ushbu loyihaning asosi ma'lumotlar tahlili va avtomatik zakaz hisob-kitobiga asoslangan.

## 🗄 Ma'lumotlar Bazasi (SQLAlchemy)
Loyihada PostgreSQL (Railway-da) ishlatiladi, lekin kesh va lokal tahlil uchun SQLite (`Data_Model.db`) ham qo'llaniladi.
- `f_sotuvlar`: Billz API dan olingan oxirgi 30 kunlik sotuvlar.
- `f_qoldiqlar`: Joriy mahsulot qoldiqlari.
- `d_mahsulotlar`: Mahsulotlar katalogi (Artikul, Rang, Supplier va boshqalar).
- `generated_orders`: Algoritm tomonidan yaratilgan zakazlar.

## 📉 OBR (Ostatki-Baza-Raschet) Algoritmi
`auto_zakaz.py` va `data_engine.py` fayllarida amalga oshirilgan. 4 ta asosiy qoida (Svetofor tizimi) asosida ishlaydi:
1. **🔥 4-Qoida (1-5 kun):** Yangi kelgan tovarning 50% dan ko'pi sotilsa, sotilgan miqdorda zakaz qilinadi.
2. **⚡️ 3-Qoida (6-9 kun):** Agar sotuv foizi 70% dan oshsa, o'rtacha kunlik sotuvning 7 kunligi (haftalik) zakaz qilinadi.
3. **⚠️ 2-Qoida (10-14 kun):** 85% dan ko'p sotilsa, haftalik prognoz asosida zakaz.
4. **❄️ 1-Qoida (15+ kun):** 99% sotilgan bo'lsa (deyarli tugagan), haftalik prognoz asosida zakaz.

## 🔄 Data Engine Workflow
1. Billz API dan yangi `access_token` olish.
2. Katalog (`d_mahsulotlar`) yangilash.
3. Sotuvlar va Qoldiqlarni (oxirgi 30 kun) kunma-kun yuklash.
4. `sync_missing_products`: Katalogda yo'q mahsulotlarni sotuv/qoldiqdan tiklash.
5. OBR hisob-kitobi va `generated_orders` jadvalini yangilash.
