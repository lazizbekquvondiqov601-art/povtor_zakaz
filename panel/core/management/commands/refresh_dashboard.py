"""
Django management command: refresh_dashboard
Foydalanish: python manage.py refresh_dashboard

Maqsad: dashboard_queries modulidagi barcha so'rovlar
to'g'ri ishlashini tekshirish (ma'lumotlar live hisoblanadi,
kesh saqlanmaydi).
"""

import sys
from pathlib import Path

from django.core.management.base import BaseCommand

# Bot loyihasining ildiz papkasini Python path'ga qo'shamiz,
# chunki src.database.db_manager shu yerda joylashgan.
# panel/ -> povtor-zakaz-bot-button/ (5 daraja yuqori)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

import src.database.db_manager as db_manager  # noqa: E402

# Dashboard so'rovlari (core/dashboard_queries.py dan import)
from core.dashboard_queries import (  # noqa: E402
    get_category_donut,
    get_kpi_summary,
    get_sales_sparkline,
    get_supplier_problems,
    get_urgent_orders,
)


class Command(BaseCommand):
    # Management command qisqacha tavsifi (help matnida ko'rinadi)
    help = "Dashboard so'rovlarini tekshiradi — barcha query'lar ishlashini tasdiqlaydi"

    def handle(self, *args, **options):
        """
        Asosiy bajarish metodi. Django `python manage.py refresh_dashboard`
        deb chaqirilganda shu metod ishga tushadi.
        """

        self.stdout.write("Dashboard tekshiruvi boshlanmoqda...\n")

        # 1. KPI xulosasi: bugungi sotuv, zaxira, kutilayotgan buyurtmalar
        try:
            kpi = get_kpi_summary()
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] KPI xulosasi: {kpi}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[XATO] get_kpi_summary: {e}"))

        # 2. Shoshilinch buyurtmalar ro'yxati
        try:
            urgent = get_urgent_orders()
            count = len(urgent) if urgent else 0
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Shoshilinch buyurtmalar soni: {count}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[XATO] get_urgent_orders: {e}"))

        # 3. Sotuv sparkline (grafik ma'lumotlari, oxirgi N kun)
        try:
            sparkline = get_sales_sparkline()
            count = len(sparkline) if sparkline else 0
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Sparkline nuqtalari soni: {count}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[XATO] get_sales_sparkline: {e}"))

        # 4. Yetkazib beruvchi muammolari (kechikkan yoki muammoli ta'minotchilar)
        try:
            problems = get_supplier_problems()
            count = len(problems) if problems else 0
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Muammoli ta'minotchilar soni: {count}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[XATO] get_supplier_problems: {e}"))

        # 5. Kategoriya donut diagrammasi uchun ma'lumotlar
        try:
            donut = get_category_donut()
            count = len(donut) if donut else 0
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Kategoriya bo'limlari soni: {count}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[XATO] get_category_donut: {e}"))

        # Barcha so'rovlar muvaffaqiyatli tekshirildi
        self.stdout.write("\nDashboard ma'lumotlari yangilandi")
