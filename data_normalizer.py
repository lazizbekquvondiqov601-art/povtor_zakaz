import re

# Non-breaking space (U+00A0)
NBSP = " "

KNOWN_ALIASES = {
    "Вид": {
        "однотонный": "Однотонный",
    },
    "Категория": {},
    "Подкатегория": {},
    "Материал": {},
    "Пол": {
        "девочек": "Девочки",
        "мальчик": "Мальчики",
    },
    "Сезон": {},
}

CATEGORICAL_COLUMNS = {
    "Категория", "Подкатегория", "Вид", "Материал", "Пол", "Сезон", "Акция",
    "category", "subcategory", "pol", "dax_group",
}

COLUMN_ALIAS_MAP = {
    "category": "Категория",
    "subcategory": "Подкатегория",
    "pol": "Пол",
}

# Faqat safe_normalize qilinadigan (case o'zgarmaydi) ustunlar
_SOFT_COLUMNS = {"Цвет", "Поставщик", "color", "supplier", "Наименование"}


def safe_normalize(value):
    """NBSP, qo'sh bo'shliq, trim — hech qachon ma'noni o'zgartirmaydi."""
    if value is None:
        return None
    try:
        if value != value:  # NaN
            return value
    except Exception:
        pass
    s = str(value)
    s = s.replace(NBSP, " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _is_simple_word(s):
    """Faqat harf va bo'shliqdan iboratmi? (raqam, qavs, defis yo'q)"""
    return all(ch.isalpha() or ch.isspace() for ch in s)


def canonical_form(value, column):
    """
    Kategoriya ustunlari uchun standart qiymat qaytaradi.
    safe_normalize + KNOWN_ALIASES lookup + capitalize (faqat harf-bo'shliq uchun).
    """
    if value is None:
        return None
    try:
        if value != value:  # NaN
            return value
    except Exception:
        pass
    normalized = safe_normalize(value)
    if not normalized:
        return normalized
    canonical_col = COLUMN_ALIAS_MAP.get(column, column)
    if canonical_col not in CATEGORICAL_COLUMNS and column not in CATEGORICAL_COLUMNS:
        return normalized
    aliases = KNOWN_ALIASES.get(canonical_col, {})
    key = normalized.casefold()
    if key in aliases:
        return aliases[key]
    if _is_simple_word(normalized):
        return normalized[0].upper() + normalized[1:].lower()
    return normalized


def normalize_dataframe(df, columns=None):
    """DataFrame ustunlarini normalize qiladi (in-place)."""
    import pandas as pd  # noqa: F401

    if columns is None:
        columns = [c for c in df.columns if c in CATEGORICAL_COLUMNS]
        for soft_col in _SOFT_COLUMNS:
            if soft_col in df.columns and soft_col not in columns:
                columns.append(soft_col)

    for col in columns:
        if col not in df.columns:
            continue
        if col in CATEGORICAL_COLUMNS or COLUMN_ALIAS_MAP.get(col) in CATEGORICAL_COLUMNS:
            df[col] = df[col].map(lambda v, c=col: canonical_form(v, c))
        else:
            df[col] = df[col].map(safe_normalize)
    return df


def safe_api_edit(data: dict) -> dict:
    """
    API dan kelgan bitta satr (dict) ni bazaga yozishdan oldin tozalaydi.

    Kategoriya ustunlari (Категория, Подкатегория, Вид, Материал, Пол, Сезон)
    -> canonical_form: case normalizatsiya + KNOWN_ALIASES replace.

    Matn ustunlari (Цвет, Поставщик, Наименование va boshqalar)
    -> safe_normalize: faqat NBSP, qo'sh bo'shliq, trim.

    Raqam, None, NaN qiymatlar o'zgarmaydi.
    """
    if not isinstance(data, dict):
        return data
    result = {}
    for key, value in data.items():
        if key in CATEGORICAL_COLUMNS or COLUMN_ALIAS_MAP.get(key) in CATEGORICAL_COLUMNS:
            result[key] = canonical_form(value, key)
        elif isinstance(value, str):
            result[key] = safe_normalize(value)
        else:
            result[key] = value
    return result
