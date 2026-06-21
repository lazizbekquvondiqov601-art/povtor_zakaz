"""
Ma'lumotlar bazasi routeri.

botdb app_label dagi modellarni 'botdb' bazasiga yo'naltiradi.
Yozish faqat GeneratedOrder uchun ruxsat etiladi (qolganlari read-only).
Migratsiyalar botdb bazasiga umuman tushmaydi (bu bot tomonidan boshqariladi).
"""


class BotDbRouter:
    """botdb ilovasi modellari uchun marshrutlovchi."""

    # Yozishga ruxsat berilgan modellar (faqat shu modellar botdb ga yoza oladi)
    WRITABLE_MODELS = {'generatedorder'}

    def db_for_read(self, model, **hints):
        """O'qish: botdb ilovasi modellari uchun botdb bazasi."""
        if model._meta.app_label == 'botdb':
            return 'botdb'
        return None

    def db_for_write(self, model, **hints):
        """Yozish: faqat GeneratedOrder uchun botdb ga yozishga ruxsat."""
        if model._meta.app_label == 'botdb':
            # model._meta.model_name odatda kichik harflarda bo'ladi
            if model._meta.model_name in self.WRITABLE_MODELS:
                return 'botdb'
            # Boshqa botdb modellarini yozish taqiqlangan
            return None
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """botdb ichidagi modellar bir-biri bilan bog'lana oladi."""
        if obj1._meta.app_label == 'botdb' and obj2._meta.app_label == 'botdb':
            return True
        # Boshqa holatlarda Django o'zi qaror qiladi
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        botdb ilovasi modellari uchun hech qachon migratsiya qilinmaydi
        (bu jadvallar bot kodi tomonidan tashqarida yaratiladi).
        """
        if app_label == 'botdb':
            return False
        # botdb bazasiga boshqa hech narsa migratsiya qilinmasin
        if db == 'botdb':
            return False
        # default bazaga esa boshqa hamma narsa migratsiya qilinishi mumkin
        return True
