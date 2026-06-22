"""
Panel Settings — OBR sozlamalari ko'rish va tahrirlash.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db import connections
from django.db.utils import OperationalError, ProgrammingError, DatabaseError
from django.contrib import messages
import src.database.db_manager as db_manager


RULE_GROUPS = [
    {
        'id': 'm1',
        'label': '1-Qoida — Kritik holat',
        'desc': 'Tovar deyarli tugagan: uzoq vaqt sotilgan va qoldiq kam.',
        'tone': 'danger',
        'icon': 'alert-circle',
        'fields': [
            ('m1_min_days', 'Minimal kunlar', 'kun'),
            ('m1_max_days', 'Maksimal kunlar', 'kun'),
            ('m1_percentage', 'Sotuv foizi (min)', '%'),
        ],
    },
    {
        'id': 'm2',
        'label': '2-Qoida — Ogohlantirish',
        'desc': 'Tovar tez sotilmoqda, qoldiq kamayib bormoqda.',
        'tone': 'warning',
        'icon': 'alert-triangle',
        'fields': [
            ('m2_min_days', 'Minimal kunlar', 'kun'),
            ('m2_max_days', 'Maksimal kunlar', 'kun'),
            ('m2_percentage', 'Sotuv foizi (min)', '%'),
        ],
    },
    {
        'id': 'm3',
        'label': '3-Qoida — Kuzatuv',
        'desc': 'Sotuv faol, lekin hali muammo yo\'q.',
        'tone': 'info',
        'icon': 'info',
        'fields': [
            ('m3_min_days', 'Minimal kunlar', 'kun'),
            ('m3_max_days', 'Maksimal kunlar', 'kun'),
            ('m3_percentage', 'Sotuv foizi (min)', '%'),
        ],
    },
    {
        'id': 'm4',
        'label': '4-Qoida — Yangi tovar',
        'desc': 'Yaqinda kelgan tovar, dastlabki sotuv ko\'rsatkichlari.',
        'tone': 'success',
        'icon': 'package',
        'fields': [
            ('m4_min_days', 'Minimal kunlar', 'kun'),
            ('m4_max_days', 'Maksimal kunlar', 'kun'),
            ('m4_percentage', 'Sotuv foizi (min)', '%'),
        ],
    },
]


@login_required
def settings_main(request):
    # get_all_settings o'zi xatoda {} qaytaradi, lekin har ehtimolga qarshi
    # bu yerda ham himoyalaymiz — jadval yo'q bo'lsa sahifa baribir ochilsin.
    try:
        settings = db_manager.get_all_settings()
    except (OperationalError, ProgrammingError, DatabaseError, Exception) as e:
        print(f"[settings_main] sozlamalarni olishda xatolik: " + str(e).split("[SQL:")[0].rstrip())
        settings = {}

    groups = []
    for g in RULE_GROUPS:
        fields = []
        for key, label, unit in g['fields']:
            fields.append({
                'name': key,
                'label': label,
                'unit': unit,
                'value': settings.get(key, ''),
            })
        groups.append({**g, 'fields': fields})

    global_lock = settings.get('global_lock', 0.0) == 1.0

    return render(request, 'panel_settings/main.html', {
        'groups': groups,
        'global_lock': global_lock,
    })


@login_required
def settings_update(request):
    if request.method != 'POST':
        return redirect('panel_settings:main')

    try:
        with connections['botdb'].cursor() as cursor:
            for key in request.POST:
                if key == 'csrfmiddlewaretoken':
                    continue
                if key == 'global_lock':
                    float_val = 1.0
                else:
                    try:
                        float_val = float(request.POST[key])
                    except (ValueError, TypeError):
                        continue

                cursor.execute(
                    "UPDATE settings SET rule_value = %s WHERE rule_name = %s",
                    [float_val, key]
                )

            # global_lock checkbox tanllanmasa — 0 qo'yamiz
            if 'global_lock' not in request.POST:
                cursor.execute(
                    "UPDATE settings SET rule_value = 0.0 WHERE rule_name = 'global_lock'"
                )

        messages.success(request, "Sozlamalar muvaffaqiyatli saqlandi!")
    except (OperationalError, ProgrammingError, DatabaseError, Exception) as e:
        # settings jadvali yo'q (bot hali init_db qilmagan) — sahifa qulamasin
        print(f"[settings_update] saqlashda xatolik: " + str(e).split("[SQL:")[0].rstrip())
        messages.error(
            request,
            "Sozlamalar saqlanmadi: ma'lumotlar bazasi hali tayyor emas. "
            "Bot ishga tushgach qaytadan urinib ko'ring."
        )

    return redirect('panel_settings:main')
