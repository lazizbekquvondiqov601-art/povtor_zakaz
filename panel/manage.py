#!/usr/bin/env python
"""Django boshqaruv yordamchi skripti."""
import os
import sys


def main():
    """Asosiy ishga tushiruvchi funksiya."""
    # Django sozlamalar moduli sifatida panel_config ni belgilaymiz
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel_config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django import qilib bo'lmadi. Virtual muhit faollashtirilganmi? "
            "pip install django bajaring."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
