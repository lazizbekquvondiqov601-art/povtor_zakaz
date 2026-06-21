"""
Bot bazasidagi (Data_Model.db) jadvallar uchun Django modellari.

Diqqat: bu modellar managed=False — Django ularni migratsiya qilmaydi.
Jadvallar bot kodi tomonidan yaratiladi va to'ldiriladi.
"""

from django.db import models


class DMahsulotlar(models.Model):
    """d_mahsulotlar — bot bazasidagi mahsulotlar lug'ati."""

    product_id = models.TextField(primary_key=True)
    artikul = models.TextField(db_column='Артикул', blank=True, null=True)
    naimenovanie = models.TextField(db_column='Наименование', blank=True, null=True)
    kategoriya = models.TextField(db_column='Категория', blank=True, null=True)
    podkategoriya = models.TextField(db_column='Подкатегория', blank=True, null=True)
    material = models.TextField(db_column='Материал', blank=True, null=True)
    vid = models.TextField(db_column='Вид', blank=True, null=True)
    tsena = models.FloatField(db_column='Цена продажи', blank=True, null=True)
    pol = models.TextField(db_column='Пол', blank=True, null=True)
    postavshik = models.TextField(db_column='Поставщик', blank=True, null=True)
    razmer_setka = models.TextField(db_column='Размер сетка', blank=True, null=True)

    class Meta:
        managed = False  # Django bu jadvalga tegmaydi
        db_table = 'd_mahsulotlar'
        app_label = 'botdb'


class FSotuvlar(models.Model):
    """f_sotuvlar — sotuvlar faktlari."""

    id = models.AutoField(primary_key=True)
    product_id = models.TextField(blank=True, null=True)
    magazin = models.TextField(db_column='Магазин', blank=True, null=True)
    prodano = models.FloatField(
        db_column='Продано за вычетом возвратов', blank=True, null=True
    )
    data = models.TextField(db_column='Дата', blank=True, null=True)
    tsena = models.FloatField(db_column='Цена продажи', blank=True, null=True)
    valovaya = models.FloatField(db_column='Валовая прибыль', blank=True, null=True)
    kategoriya = models.TextField(db_column='Категория', blank=True, null=True)
    podkategoriya = models.TextField(db_column='Подкатегория', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'f_sotuvlar'
        app_label = 'botdb'


class FQoldiqlar(models.Model):
    """f_qoldiqlar — omborlardagi qoldiqlar fakti (sana bo'yicha)."""

    id = models.AutoField(primary_key=True)
    product_id = models.TextField(blank=True, null=True)
    magazin = models.TextField(db_column='Магазин', blank=True, null=True)
    kolvo = models.FloatField(db_column='Кол-во', blank=True, null=True)
    data = models.TextField(db_column='Дата', blank=True, null=True)
    kategoriya = models.TextField(db_column='Категория', blank=True, null=True)
    podkategoriya = models.TextField(db_column='Подкатегория', blank=True, null=True)
    pol = models.TextField(db_column='Пол', blank=True, null=True)
    vid = models.TextField(db_column='Вид', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'f_qoldiqlar'
        app_label = 'botdb'


class GeneratedOrder(models.Model):
    """generated_orders — bot tomonidan tuzilgan zakazlar."""

    zakaz_id = models.AutoField(primary_key=True)
    supplier = models.TextField(blank=True, null=True)
    artikul = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    subcategory = models.TextField(blank=True, null=True)
    shop = models.TextField(blank=True, null=True)
    quantity = models.FloatField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    created_at = models.TextField(blank=True, null=True)
    color = models.TextField(blank=True, null=True)
    photo = models.TextField(blank=True, null=True)
    supply_price = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'generated_orders'
        app_label = 'botdb'


class BotSetting(models.Model):
    """settings — bot OBR qoidalari (rule_name -> rule_value)."""

    id = models.AutoField(primary_key=True)
    rule_name = models.TextField(blank=True, null=True)
    rule_value = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'settings'
        app_label = 'botdb'
