"""
Super Admin Only middleware.

Har bir request'da foydalanuvchi login qilganmi tekshiradi.
Agar yo'q bo'lsa — /login/ ga yo'naltiradi.
Faqat /login/ va /static/ yo'llari ochiq.
"""

from django.shortcuts import redirect


class SuperAdminOnlyMiddleware:
    """Faqat tizimga kirgan foydalanuvchilarni o'tkazadi."""

    # Login qilmasdan ham ochiq bo'ladigan yo'llar
    OPEN_PATHS = ('/login', '/static', '/admin/login', '/webapp')

    def __init__(self, get_response):
        # get_response — keyingi middleware yoki view chaqiruvchi callable
        self.get_response = get_response

    def __call__(self, request):
        # Ochiq yo'llarga tegmaymiz
        path = request.path
        is_open = any(path.startswith(prefix) for prefix in self.OPEN_PATHS)

        if not is_open and not request.user.is_authenticated:
            # Tizimga kirmagan — login sahifasiga
            return redirect('/login/')

        # Ruxsat berildi — request'ni davom ettiramiz
        return self.get_response(request)
