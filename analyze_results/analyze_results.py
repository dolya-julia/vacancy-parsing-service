
from pathlib import Path
import re
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 1. ПУТИ К ДАННЫМ
# ============================================================

CSHARP_DIR = Path(
    r"C:\Data\Projects\web_mining\lab5\Csharp_parser\RabotaParser"
)
PYTHON_DIR = Path(
    r"C:\Data\Projects\web_mining\lab5\PythonParser\RabotaParser"
)

CSHARP_VACANCIES = CSHARP_DIR / "vacancies_all.csv"
PYTHON_VACANCIES = PYTHON_DIR / "vacancies_all.csv"

CSHARP_STATS = CSHARP_DIR / "parsing_stats_all.csv"
PYTHON_STATS = PYTHON_DIR / "parsing_stats_all.csv"

OUT = Path("analysis_results")
OUT.mkdir(parents=True, exist_ok=True)

# Для графиков с русскими подписями
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# 2. ЧТЕНИЕ CSV
# ============================================================


def read_csv(path, separator):
    """Читает CSV с явно заданным разделителем."""
    path = Path(path)

    if not path.exists():
        print(f"[ПРЕДУПРЕЖДЕНИЕ] Файл не найден: {path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(
            path,
            sep=separator,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
            quotechar='"',
            on_bad_lines="error"
        )

        df.columns = (
            df.columns.astype(str)
            .str.replace("\ufeff", "", regex=False)
            .str.strip()
        )

        print(
            f"[ЗАГРУЖЕНО] {path}\n"
            f"  Разделитель: {repr(separator)}\n"
            f"  Строк: {len(df)}; столбцов: {len(df.columns)}"
        )

        return df

    except Exception as error:
        print(f"[ОШИБКА] Не удалось прочитать {path}: {error}")
        return pd.DataFrame()



# ============================================================
# 3. НОРМАЛИЗАЦИЯ НАЗВАНИЙ СТОЛБЦОВ
# ============================================================

ALIASES = {
    "Источник": "source",
    "Поисковый запрос": "query",
    "Дата сбора": "date",
    "Дата сбора вакансии": "date",
    "Название": "title",
    "Название вакансии": "title",
    "Компания": "company",
    "Город": "city",
    "Зарплата": "salary",
    "Уровень": "level",
    "Формат работы": "work_format",
    "Навыки": "skills",
    "Ссылка": "link",

    "Source": "source",
    "Query": "query",
    "Date": "date",
    "Title": "title",
    "Company": "company",
    "City": "city",
    "Salary": "salary",
    "Level": "level",
    "Work format": "work_format",
    "Work_format": "work_format",
    "Skills": "skills",
    "Link": "link",

    # Названия из возможных вариантов выгрузки
    "vacancy_title": "title",
    "job_title": "title",
    "employer": "company",
    "location": "city",
    "url": "link",
}


def normalize_columns(df):
    if df.empty:
        return df

    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()
    df = df.rename(columns=ALIASES)

    # Если после переименования возникли дубли столбцов,
    # оставляем первое вхождение.
    df = df.loc[:, ~df.columns.duplicated()]

    return df


# ============================================================
# 4. ОЧИСТКА ТЕКСТОВЫХ ЗНАЧЕНИЙ
# ============================================================

MISSING_VALUES = {
    "",
    "не указан",
    "не указано",
    "не указана",
    "не указаны",
    "не задан",
    "не задано",
    "нет данных",
    "нет информации",
    "неизвестно",
    "unknown",
    "none",
    "null",
    "nan",
    "n/a",
    "na",
    "-"
}


def clean_text(value):
    """Удаляет лишние пробелы и приводит пустые маркеры к пустой строке."""
    if pd.isna(value):
        return ""

    value = str(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()

    if value.casefold() in MISSING_VALUES:
        return ""

    return value


def clean_dataframe(df):
    df = df.copy()

    for column in df.select_dtypes(include=["object"]).columns:
        df[column] = df[column].map(clean_text)

    return df


# ============================================================
# 5. НОРМАЛИЗАЦИЯ ГОРОДОВ
# ============================================================

def normalize_city(value):
    """
    Нормализует распространённые варианты записи городов.

    Исходный столбец city не изменяется:
    нормализованный результат сохраняется в city_normalized.
    """
    value = clean_text(value)

    if not value:
        return "Не указан"

    original = value
    value = re.sub(r"\s+", " ", value).strip(" ,;")

    # Приводим текст к регистронезависимому виду для сопоставления
    lower = value.casefold()


    # Москва с указанием улицы, проспекта, района или другого адреса
    if re.match(
        r"^г\.?\s*москва(?:\s*[,;].*|\s+.*)?$",
        lower
    ):
        return "Москва"

    # Москва с адресом, в том числе без пробела после названия города
    if re.match(r"^(?:г\.?\s*)?москва(?:\s*[,;].*|[а-яё].*|\s+.*)?$", lower):
        return "Москва"

    # Казань с указанием станции или дополнительного объекта
    if re.match(
        r"^казань(?:\s*[,;].*|[а-яё].*|\s+.*)?$",
        lower
    ):
        return "Казань"

    # Москва с указанием федерального округа
    if (
        "центральный федеральный округ" in lower
        and "москв" in lower
    ):
        return "Москва"

    # Известные варианты написания Москвы
    if lower in {
        "москва",
        "г. москва",
        "г москва",
        "москва, россия",
        "москва, московская область"
    }:
        return "Москва"

    # Некоторые сайты объединяют город и станцию метро/район
    # без разделителя. В этом случае распознаём только известные
    # сочетания, а не любое слово, начинающееся с "Москва".
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

    compact = re.sub(r"[\s,;]+", "", lower)

    for suffix in known_moscow_suffixes:
        compact_suffix = re.sub(r"[\s,;]+", "", suffix)

        if compact == "москва" + compact_suffix:
            return "Москва"

    # Варианты записи Санкт-Петербурга
    if lower in {
        "санкт-петербург",
        "санкт петербург",
        "г. санкт-петербург",
        "г санкт-петербург",
        "спб",
        "петербург"
    }:
        return "Санкт-Петербург"

    # Некоторые значения могут содержать дополнительные
    # пояснения после запятой. Известные города распознаём
    # только при наличии города в отдельной части строки.
    parts = [
        part.strip(" .")
        for part in re.split(r"[,;]", value)
        if part.strip(" .")
    ]

    known_cities = {
        "москва": "Москва",
        "санкт-петербург": "Санкт-Петербург",
        "санкт петербург": "Санкт-Петербург",
        "казань": "Казань",
        "новосибирск": "Новосибирск",
        "краснодар": "Краснодар",
        "екатеринбург": "Екатеринбург",
        "нижний новгород": "Нижний Новгород",
    }

    for part in parts:
        if part.casefold() in known_cities:
            return known_cities[part.casefold()]

    # Если уверенного соответствия нет, сохраняем исходное значение.
    return original


# ============================================================
# 6. НОРМАЛИЗАЦИЯ ФОРМАТА РАБОТЫ
# ============================================================

def normalize_work_format(value):
    value = clean_text(value)

    if not value:
        return "Не указан"

    lower = value.casefold()

    remote_variants = [
        "удаленно",
        "удалённо",
        "дистанционно",
        "remote",
        "полностью удаленно",
        "полностью удалённо",
    ]

    office_variants = [
        "офис",
        "офисный формат",
        "работа в офисе",
        "на месте работодателя",
        "on-site",
        "onsite",
    ]

    hybrid_variants = [
        "гибрид",
        "гибридный формат",
        "гибридно",
        "hybrid",
    ]

    if any(item in lower for item in remote_variants):
        return "Удалённо"

    if any(item in lower for item in office_variants):
        return "Офис"

    if any(item in lower for item in hybrid_variants):
        return "Гибрид"

    return value


# ============================================================
# 7. ЗАГРУЗКА ДАННЫХ ОБОИХ ПАРСЕРОВ
# ============================================================

csharp_df = clean_dataframe(
    normalize_columns(read_csv(CSHARP_VACANCIES, separator=";"))
)

python_df = clean_dataframe(
    normalize_columns(read_csv(PYTHON_VACANCIES, separator=","))
)


if csharp_df.empty and python_df.empty:
    raise SystemExit(
        "Не удалось загрузить данные. "
        "Проверь пути к vacancies_all.csv."
    )

if not csharp_df.empty:
    csharp_df["parser"] = "C# HtmlAgilityPack"

if not python_df.empty:
    python_df["parser"] = "Python Scrapy"

# Общий набор со всеми записями — в том числе повторяющимися
df_all = pd.concat(
    [csharp_df, python_df],
    ignore_index=True,
    sort=False
).dropna(how="all")

# Сохраняем полную таблицу без удаления совпадений
df_all.to_csv(
    OUT / "vacancies_combined_all.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n========== ИСХОДНЫЕ РЕЗУЛЬТАТЫ ==========")
print(f"C# HtmlAgilityPack: {len(csharp_df)}")
print(f"Python Scrapy:      {len(python_df)}")
print(f"Всего записей:      {len(df_all)}")


# ============================================================
# 8. СОЗДАНИЕ ЕДИНОГО НАБОРА ДЛЯ АНАЛИЗА
# ============================================================

def normalize_link(value):
    """
    Удаляет пробелы и фрагмент URL после #.
    Не удаляет параметры запроса, поскольку они иногда
    могут быть частью идентификатора вакансии.
    """
    value = clean_text(value)

    if not value:
        return ""

    return value.split("#", 1)[0].rstrip("/")


df_all["link_normalized"] = (
    df_all["link"].map(normalize_link)
    if "link" in df_all.columns
    else ""
)

has_link = df_all["link_normalized"].ne("")

# Ссылки используются для удаления повторов между парсерами.
# Записи без ссылки сохраняются, но не объединяются между собой.
linked = df_all.loc[has_link].drop_duplicates(
    subset=["link_normalized"],
    keep="first"
)

without_link = df_all.loc[~has_link]

df_unique = pd.concat(
    [linked, without_link],
    ignore_index=True,
    sort=False
)

df_unique.to_csv(
    OUT / "vacancies_unique.csv",
    index=False,
    encoding="utf-8-sig"
)

print(f"Уникальных записей: {len(df_unique)}")
print(f"Удалено повторов по ссылкам: {len(df_all) - len(df_unique)}")


# ============================================================
# 9. ПОДГОТОВКА ДАННЫХ ДЛЯ СОДЕРЖАТЕЛЬНОГО АНАЛИЗА
# ============================================================

# Анализируем единый набор, а не сумму результатов двух парсеров.
analysis_df = df_unique.copy()

if "city" in analysis_df.columns:
    analysis_df["city_normalized"] = (
        analysis_df["city"].map(normalize_city)
    )

if "work_format" in analysis_df.columns:
    analysis_df["work_format_normalized"] = (
        analysis_df["work_format"].map(normalize_work_format)
    )

# Отдельно нормализуем поисковые запросы.
if "query" in analysis_df.columns:
    analysis_df["query_normalized"] = (
        analysis_df["query"].map(clean_text)
    )

    query_aliases = {
        "python": "Python",
        "data scientist": "Data Scientist",
        "machine learning": "Machine Learning",
    }

    analysis_df["query_normalized"] = (
        analysis_df["query_normalized"]
        .map(lambda x: query_aliases.get(x.casefold(), x) if x else "")
    )

# Записываем подготовленный набор для проверки.
analysis_df.to_csv(
    OUT / "vacancies_analysis_dataset.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 10. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ТАБЛИЦ И ГРАФИКОВ
# ============================================================

def save_frequency_table(series, category_name, filename):
    """Создаёт таблицу частот, включая категорию пропусков."""
    series = series.fillna("").astype(str).str.strip()
    series = series.replace("", "Не указан")

    table = (
        series.value_counts(dropna=False)
        .rename_axis(category_name)
        .reset_index(name="Количество вакансий")
    )

    table.to_csv(
        OUT / filename,
        index=False,
        encoding="utf-8-sig"
    )

    return table


def save_bar_chart(
    table,
    category_column,
    value_column,
    title,
    xlabel,
    ylabel,
    filename,
    horizontal=False,
    top_n=None
):
    """Сохраняет столбчатую диаграмму."""
    if table.empty:
        return

    plot_df = table.copy()

    if top_n is not None:
        plot_df = plot_df.head(top_n)

    if horizontal:
        plot_df = plot_df.sort_values(value_column, ascending=True)
        ax = plot_df.plot(
            x=category_column,
            y=value_column,
            kind="barh",
            legend=False,
            figsize=(10, max(4, len(plot_df) * 0.4))
        )
    else:
        ax = plot_df.plot(
            x=category_column,
            y=value_column,
            kind="bar",
            legend=False,
            figsize=(10, 5)
        )
        plt.xticks(rotation=25, ha="right")

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    plt.tight_layout()
    plt.savefig(OUT / filename, dpi=160, bbox_inches="tight")
    plt.close()


# ============================================================
# 11. СРАВНЕНИЕ ПАРСЕРОВ
# ============================================================

comparison = pd.DataFrame({
    "Парсер": [
        "C# HtmlAgilityPack",
        "Python Scrapy"
    ],
    "Количество исходных записей": [
        len(csharp_df),
        len(python_df)
    ],
})

comparison.to_csv(
    OUT / "parser_comparison.csv",
    index=False,
    encoding="utf-8-sig"
)

save_bar_chart(
    comparison,
    "Парсер",
    "Количество исходных записей",
    "Количество записей по парсерам",
    "Парсер",
    "Количество записей",
    "01_parser_comparison.png"
)


# ============================================================
# 12. РАСПРЕДЕЛЕНИЕ ПО ИСТОЧНИКАМ
# ============================================================

if "source" in analysis_df.columns:
    by_source = save_frequency_table(
        analysis_df["source"],
        "Источник",
        "vacancies_by_source.csv"
    )

    save_bar_chart(
        by_source,
        "Источник",
        "Количество вакансий",
        "Количество уникальных вакансий по источникам",
        "Источник",
        "Количество вакансий",
        "02_by_source.png"
    )


# ============================================================
# 13. РАСПРЕДЕЛЕНИЕ ПО ПОИСКОВЫМ ЗАПРОСАМ
# ============================================================

if "query_normalized" in analysis_df.columns:
    by_query = save_frequency_table(
        analysis_df["query_normalized"],
        "Поисковый запрос",
        "vacancies_by_query.csv"
    )

    save_bar_chart(
        by_query,
        "Поисковый запрос",
        "Количество вакансий",
        "Распределение вакансий по поисковым запросам",
        "Поисковый запрос",
        "Количество вакансий",
        "03_by_query.png"
    )


# ============================================================
# 14. РАСПРЕДЕЛЕНИЕ ПО ГОРОДАМ
# ============================================================

if "city_normalized" in analysis_df.columns:
    by_city = save_frequency_table(
        analysis_df["city_normalized"],
        "Город",
        "vacancies_by_city.csv"
    )

    # Полная таблица содержит все города и "Не указан".
    # На графике отображаем топ-10 категорий.
    save_bar_chart(
        by_city,
        "Город",
        "Количество вакансий",
        "Топ-10 городов по количеству вакансий",
        "Количество вакансий",
        "Город",
        "04_by_city.png",
        horizontal=True,
        top_n=10
    )

    # Сохраняем значения городов, которые требуют проверки.
    if "city" in analysis_df.columns:
        city_audit = (
            analysis_df[
                ["city", "city_normalized"]
            ]
            .drop_duplicates()
            .sort_values(
                ["city_normalized", "city"],
                na_position="last"
            )
        )

        city_audit.to_csv(
            OUT / "city_normalization_audit.csv",
            index=False,
            encoding="utf-8-sig"
        )


# ============================================================
# 15. РАСПРЕДЕЛЕНИЕ ПО ФОРМАТАМ РАБОТЫ
# ============================================================

if "work_format_normalized" in analysis_df.columns:
    by_format = save_frequency_table(
        analysis_df["work_format_normalized"],
        "Формат работы",
        "vacancies_by_format.csv"
    )

    save_bar_chart(
        by_format,
        "Формат работы",
        "Количество вакансий",
        "Распределение вакансий по формату работы",
        "Формат работы",
        "Количество вакансий",
        "05_by_format.png"
    )


# ============================================================
# 16. ТОП-10 НАЗВАНИЙ ВАКАНСИЙ
# ============================================================

if "title" in analysis_df.columns:
    titles = (
        analysis_df["title"]
        .map(clean_text)
    )

    # Не считаем пустое название вакансии отдельной профессией.
    titles = titles[titles.ne("")]

    top_titles = (
        titles.value_counts()
        .head(10)
        .rename_axis("Название вакансии")
        .reset_index(name="Количество вакансий")
    )

    top_titles.to_csv(
        OUT / "top_vacancies.csv",
        index=False,
        encoding="utf-8-sig"
    )

    save_bar_chart(
        top_titles,
        "Название вакансии",
        "Количество вакансий",
        "Топ-10 названий вакансий",
        "Количество вакансий",
        "Название вакансии",
        "06_top_vacancies.png",
        horizontal=True
    )


# ============================================================
# 17. ЗАПОЛНЕННОСТЬ ПОЛЕЙ
# ============================================================

fields_to_check = [
    "title",
    "company",
    "city",
    "salary",
    "level",
    "work_format",
    "skills",
    "link"
]

existing_fields = [
    field for field in fields_to_check
    if field in df_all.columns
]

if existing_fields and "parser" in df_all.columns:
    completeness = []

    for parser_name, group in df_all.groupby("parser"):
        for field in existing_fields:
            values = group[field].map(clean_text)
            filled = int(values.ne("").sum())
            total = len(group)

            completeness.append({
                "Парсер": parser_name,
                "Поле": field,
                "Заполнено записей": filled,
                "Всего записей": total,
                "Заполнено, %": round(
                    filled / total * 100, 2
                ) if total else 0
            })

    completeness_df = pd.DataFrame(completeness)

    completeness_df.to_csv(
        OUT / "field_completeness.csv",
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# 18. СТАТИСТИКА ПРОПУЩЕННЫХ ЗНАЧЕНИЙ
# ============================================================

missing_rows = []

for field in existing_fields:
    values = analysis_df[field].map(clean_text)
    total = len(analysis_df)
    missing = int(values.eq("").sum())

    missing_rows.append({
        "Поле": field,
        "Всего записей": total,
        "Не заполнено": missing,
        "Заполнено": total - missing,
        "Заполнено, %": round(
            (total - missing) / total * 100, 2
        ) if total else 0
    })

missing_df = pd.DataFrame(missing_rows)

missing_df.to_csv(
    OUT / "missing_values_summary.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 19. ПРОВЕРКА ССЫЛОК И ПОВТОРОВ
# ============================================================

link_stats = []

for parser_name, group in df_all.groupby("parser"):
    if "link_normalized" in group.columns:
        links = group["link_normalized"]
    else:
        links = pd.Series([""] * len(group), index=group.index)

    nonempty = links[links.ne("")]

    link_stats.append({
        "Парсер": parser_name,
        "Всего записей": len(group),
        "Записей с непустой ссылкой": int(links.ne("").sum()),
        "Уникальных непустых ссылок": int(nonempty.nunique()),
        "Повторных ссылок": int(
            len(nonempty) - nonempty.nunique()
        )
    })

link_stats_df = pd.DataFrame(link_stats)

link_stats_df.to_csv(
    OUT / "link_statistics.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 20. ИТОГОВЫЙ ОТЧЁТ
# ============================================================

summary = pd.DataFrame([
    {
        "Показатель": "Записей C# HtmlAgilityPack",
        "Значение": len(csharp_df)
    },
    {
        "Показатель": "Записей Python Scrapy",
        "Значение": len(python_df)
    },
    {
        "Показатель": "Записей до удаления повторов",
        "Значение": len(df_all)
    },
    {
        "Показатель": "Записей после удаления повторов по ссылкам",
        "Значение": len(df_unique)
    },
    {
        "Показатель": "Удалено повторных записей",
        "Значение": len(df_all) - len(df_unique)
    },
])

summary.to_csv(
    OUT / "analysis_summary.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n========== АНАЛИЗ ЗАВЕРШЁН ==========")
print(summary.to_string(index=False))
print(f"\nРезультаты сохранены в: {OUT.resolve()}")

print("\nОсновные файлы:")
print("- vacancies_combined_all.csv — исходные записи обоих парсеров")
print("- vacancies_unique.csv — набор без повторов по ссылкам")
print("- vacancies_analysis_dataset.csv — подготовленный набор для анализа")
print("- vacancies_by_source.csv — распределение по источникам")
print("- vacancies_by_query.csv — распределение по поисковым запросам")
print("- vacancies_by_city.csv — нормализованная статистика городов")
print("- city_normalization_audit.csv — проверка нормализации городов")
print("- vacancies_by_format.csv — распределение по форматам работы")
print("- top_vacancies.csv — топ-10 названий вакансий")
print("- field_completeness.csv — заполненность полей по парсерам")
print("- missing_values_summary.csv — сводка пропусков")
print("- link_statistics.csv — статистика повторов ссылок")
print("- analysis_summary.csv — сводка анализа")
print("- PNG-файлы — графики для отчёта")
