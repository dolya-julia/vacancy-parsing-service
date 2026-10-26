
import re
import html
from datetime import datetime

import pandas as pd


# ============================================================
# 1. ПСЕВДОНИМЫ СТОЛБЦОВ
# ============================================================

ALIASES = {
    "source": ["source", "источник", "site", "сайт"],
    "url": ["url", "link", "ссылка", "vacancy_url"],
    "title": ["title", "название", "должность", "вакансия"],
    "company": ["company", "компания", "работодатель"],
    "region": ["region", "city", "город", "регион", "location"],
    "salary": ["salary", "зарплата", "оплата"],
    "description": ["description", "описание", "текст"],
    "skills": ["skills", "навыки", "требования"],
    "query": ["query", "запрос", "search_query"],
    "collected_at": [
        "collected_at", "date", "дата сбора",
        "дата сбора вакансии"
    ],
    "parser": ["parser", "парсер"],
}


# ============================================================
# 2. ОЧИСТКА ТЕКСТА
# ============================================================

MISSING_VALUES = {
    "", "не указан", "не указано", "не указана",
    "не указаны", "не задан", "не задано",
    "нет данных", "нет информации", "неизвестно",
    "unknown", "none", "null", "nan", "n/a", "na", "-"
}


def clean_text(value):
    """Удаляет HTML-разметку, лишние пробелы и HTML-сущности."""

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text = html.unescape(str(value))
    text = text.replace("\xa0", " ")

    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.I | re.S
    )
    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.I | re.S
    )
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if text.casefold() in MISSING_VALUES:
        return ""

    return text


# ============================================================
# 3. НОРМАЛИЗАЦИЯ ГОРОДОВ
# ============================================================

KNOWN_CITIES = {
    "москва": "Москва",
    "санкт-петербург": "Санкт-Петербург",
    "санкт петербург": "Санкт-Петербург",
    "спб": "Санкт-Петербург",
    "петербург": "Санкт-Петербург",
    "казань": "Казань",
    "новосибирск": "Новосибирск",
    "краснодар": "Краснодар",
    "екатеринбург": "Екатеринбург",
    "нижний новгород": "Нижний Новгород",
    "минск": "Минск",
}


def normalize_city(value):
    """
    Приводит распространённые варианты записи города
    к единому названию.

    Неизвестные значения сохраняются для последующей проверки.
    """

    value = clean_text(value)

    if not value:
        return "Не указан"

    original = value
    lower = re.sub(r"\s+", " ", value.casefold()).strip()
    lower = lower.strip(" ,;")

    # Убираем распространённый префикс «г.» для сопоставления.
    comparable = re.sub(r"^г\.?\s*", "", lower).strip()

    # Сначала проверяем точные совпадения.
    if comparable in KNOWN_CITIES:
        return KNOWN_CITIES[comparable]

    # Москва: адрес, район, метро или другая информация
    # после названия города, в том числе без пробела.
    if re.match(r"^москва(?:$|[\s,;].*|[а-яё].*)", comparable):
        return "Москва"

    # Москва, указанная вместе с федеральным округом.
    if (
        "центральный федеральный округ" in lower
        and "москв" in lower
    ):
        return "Москва"

    # Некоторые источники склеивают город и название станции
    # метро или района без разделителя.
    known_moscow_suffixes = [
        "народное ополчение",
        "деловой центр",
        "белорусская",
        "павелецкая",
        "курская",
        "арбатская",
        "тверская",
        "сокольники",
        "митино",
        "химки",
    ]

    compact = re.sub(r"[\s,;]+", "", comparable)

    for suffix in known_moscow_suffixes:
        compact_suffix = re.sub(r"[\s,;]+", "", suffix)

        if compact == "москва" + compact_suffix:
            return "Москва"

    # Казань с дополнительным описанием.
    if re.match(r"^казань(?:$|[\s,;].*|[а-яё].*)", comparable):
        return "Казань"

    # Санкт-Петербург с адресом или дополнительными сведениями.
    if re.match(
        r"^(?:санкт-петербург|санкт петербург|спб|петербург)"
        r"(?:$|[\s,;].*|[а-яё].*)",
        comparable
    ):
        return "Санкт-Петербург"

    # Другие известные города: допускаем дополнительные сведения
    # после запятой или точки с запятой.
    parts = [
        re.sub(r"\s+", " ", part.casefold()).strip(" .")
        for part in re.split(r"[,;]", value)
        if part.strip(" .")
    ]

    for part in parts:
        part = re.sub(r"^г\.?\s*", "", part).strip()

        if part in KNOWN_CITIES:
            return KNOWN_CITIES[part]

    # Не пытаемся угадывать неизвестный город.
    return original


# ============================================================
# 4. НОРМАЛИЗАЦИЯ НАЗВАНИЙ СТОЛБЦОВ
# ============================================================

def normalize_columns(df):
    df = df.copy()

    df.columns = [
        str(column).replace("\ufeff", "").strip().casefold()
        for column in df.columns
    ]

    # Удаляем дубли исходных названий столбцов.
    df = df.loc[:, ~df.columns.duplicated()].copy()

    rename = {}

    for canonical, variants in ALIASES.items():
        for variant in variants:
            if variant.casefold() in df.columns:
                rename[variant.casefold()] = canonical
                break

    df = df.rename(columns=rename)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Создаём отсутствующие поля, чтобы формат данных был единым.
    for column in ALIASES:
        if column not in df.columns:
            df[column] = ""

    return df


# ============================================================
# 5. ПРЕДОБРАБОТКА ВАКАНСИЙ
# ============================================================

def preprocess_vacancies(df, parser_name):
    """
    Подготавливает вакансии к сохранению в базе данных:
    очищает поля, нормализует регионы и удаляет дубликаты.
    """

    df = normalize_columns(df)

    text_fields = [
        "source", "url", "title", "company", "region",
        "salary", "description", "skills", "query",
        "collected_at", "parser"
    ]

    for field in text_fields:
        df[field] = df[field].map(clean_text)

    # Нормализация региона выполняется до сохранения.
    df["region"] = df["region"].map(normalize_city)

    df["parser"] = df["parser"].replace("", parser_name)

    now = datetime.now().isoformat(timespec="seconds")
    df["collected_at"] = df["collected_at"].replace("", now)

    # Без названия вакансия не включается в набор.
    df = df[df["title"].str.strip().ne("")].copy()

    # Формируем ключ для удаления повторов внутри набора.
    def make_dedup_key(row):
        if row["url"]:
            return row["source"] + "|" + row["url"].split("#", 1)[0].rstrip("/")

        return "|".join([
            row["source"],
            row["title"],
            row["company"],
            row["region"],
            row["query"]
        ])

    df["_dedup_key"] = df.apply(make_dedup_key, axis=1)
    df = df.drop_duplicates("_dedup_key", keep="last")
    df = df.drop(columns=["_dedup_key"])

    return df[text_fields].to_dict(orient="records")


# ============================================================
# 6. ПРЕДОБРАБОТКА СТАТИСТИКИ ПАРСИНГА
# ============================================================

def preprocess_stats(df):
    df = df.copy()

    df.columns = [
        str(column).replace("\ufeff", "").strip().casefold()
        for column in df.columns
    ]

    df = df.loc[:, ~df.columns.duplicated()].copy()

    aliases = {
        "parser": ["parser", "парсер"],
        "source": ["source", "источник", "site", "сайт"],
        "query": ["query", "запрос"],
        "page": ["page", "страница"],
        "found_links": ["found_links", "найдено ссылок"],
        "unique_added": ["unique_added", "добавлено уникальных"],
        "elapsed_ms": [
            "elapsed_ms", "elapsed", "время выполнения"
        ],
        "status": ["status", "статус"],
    }

    rename = {}

    for target, variants in aliases.items():
        for variant in variants:
            if variant.casefold() in df.columns:
                rename[variant.casefold()] = target
                break

    df = df.rename(columns=rename)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    for column in aliases:
        if column not in df.columns:
            df[column] = ""

    return df
