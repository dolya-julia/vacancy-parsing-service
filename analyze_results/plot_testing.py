#
# from pathlib import Path
# import pandas as pd
# import matplotlib.pyplot as plt
#
# # ============================================================
# # 1. ПУТИ К ФАЙЛАМ
# # ============================================================
#
# # ЗАМЕНИ НА СВОИ РЕАЛЬНЫЕ ПУТИ
# CSHARP_DIR = Path(r"C:\Data\Projects\web_mining\lab5\Csharp_parser\TestRabotaParser")
# PYTHON_DIR = Path(r"C:\Data\Projects\web_mining\lab5\PythonParser\TestRabotaParser")
#
# CSHARP_STATS = CSHARP_DIR / "parsing_stats_all.csv"
# PYTHON_STATS = PYTHON_DIR / "parsing_stats_all.csv"
#
# CSHARP_VACANCIES = CSHARP_DIR / "vacancies_all.csv"
# PYTHON_VACANCIES = PYTHON_DIR / "vacancies_all.csv"
#
# OUT = Path("testing_results")
# OUT.mkdir(parents=True, exist_ok=True)
#
#
# # ============================================================
# # 2. ЧТЕНИЕ CSV
# # ============================================================
#
# def read_csv(path):
#     path = Path(path)
#
#     if not path.exists():
#         print(f"[ПРЕДУПРЕЖДЕНИЕ] Файл не найден: {path}")
#         return pd.DataFrame()
#
#     # Пробуем распространённые разделители.
#     # Строгий режим нужен, чтобы не выбирать файл,
#     # в котором строки были пропущены из-за ошибки разделителя.
#     candidates = []
#
#     for separator in [";", ",", "\t"]:
#         try:
#             data = pd.read_csv(
#                 path,
#                 sep=separator,
#                 encoding="utf-8-sig",
#                 engine="python",
#                 on_bad_lines="error"
#             )
#
#             # Корректная таблица обычно имеет несколько столбцов.
#             if len(data.columns) > 1:
#                 candidates.append(data)
#
#         except Exception:
#             continue
#
#     if not candidates:
#         print(f"[ОШИБКА] Не удалось прочитать CSV: {path}")
#         print("Проверь разделитель и кавычки в исходном файле.")
#         return pd.DataFrame()
#
#     # Выбираем вариант с наибольшим количеством столбцов.
#     # При равенстве предпочитаем вариант с большим числом строк.
#     data = max(
#         candidates,
#         key=lambda item: (len(item.columns), len(item))
#     )
#
#     data.columns = data.columns.astype(str).str.strip()
#
#     # Удаляем повторяющиеся исходные названия столбцов.
#     data = data.loc[:, ~data.columns.duplicated()]
#
#     print(f"\nФайл: {path}")
#     print(f"Строк: {len(data)}")
#     print(f"Столбцы: {data.columns.tolist()}")
#
#     return data
#
#
# # ============================================================
# # 3. НОРМАЛИЗАЦИЯ НАЗВАНИЙ СТОЛБЦОВ
# # ============================================================
#
# ALIASES = {
#     # Общие поля
#     "Источник": "source",
#     "Source": "source",
#     "Поисковый запрос": "query",
#     "Query": "query",
#     "Страница": "page",
#     "Номер страницы": "page",
#     "Page": "page",
#
#     # Статистика парсинга
#     "Найдено ссылок": "found_links",
#     "Found links": "found_links",
#     "found_links": "found_links",
#     "Found": "found_links",
#     "Найдено вакансий": "found_links",
#
#     "Уникальных добавлено": "unique_added",
#     "Добавлено уникальных": "unique_added",
#     "Unique added": "unique_added",
#     "unique_added": "unique_added",
#     "Added": "unique_added",
#
#     "Время, сек": "elapsed",
#     "Время выполнения": "elapsed",
#     "Время выполнения, сек": "elapsed",
#     "Elapsed": "elapsed",
#     "Elapsed seconds": "elapsed",
#
#     "Время, мс": "elapsed_ms",
#     "Время выполнения, мс": "elapsed_ms",
#     "Elapsed ms": "elapsed_ms",
#     "elapsed_ms": "elapsed_ms",
#
#     "Статус": "status",
#     "Status": "status",
#
#     # Поля вакансий
#     "Дата сбора": "date",
#     "Date": "date",
#     "Название": "title",
#     "Название вакансии": "title",
#     "Title": "title",
#     "Компания": "company",
#     "Company": "company",
#     "Город": "city",
#     "City": "city",
#     "Зарплата": "salary",
#     "Salary": "salary",
#     "Уровень": "level",
#     "Level": "level",
#     "Формат работы": "work_format",
#     "Work format": "work_format",
#     "Навыки": "skills",
#     "Skills": "skills",
#     "Ссылка": "link",
#     "Link": "link",
# }
#
#
# def normalize_columns(data):
#     if data.empty:
#         return data
#
#     data = data.copy()
#     data.columns = data.columns.astype(str).str.strip()
#     data = data.rename(columns=ALIASES)
#
#     # После переименования, например, "Название" и "Title"
#     # могут превратиться в два столбца "title".
#     # Оставляем первое вхождение каждого названия.
#     data = data.loc[:, ~data.columns.duplicated()]
#
#     return data
#
#
# def clean_text_columns(data):
#     """Нормализует текстовые поля, не меняя числовые значения."""
#     data = data.copy()
#
#     for column in data.select_dtypes(include=["object"]).columns:
#         data[column] = (
#             data[column]
#             .fillna("")
#             .astype(str)
#             .str.strip()
#         )
#
#     return data
#
#
# def save_csv(data, filename):
#     data.to_csv(
#         OUT / filename,
#         index=False,
#         encoding="utf-8-sig"
#     )
#
#
# def save_bar_chart(series, title, xlabel, ylabel, filename):
#     if series.empty:
#         print(f"Нет данных для графика: {title}")
#         return
#
#     ax = series.plot(kind="bar", figsize=(9, 5))
#     ax.set_title(title)
#     ax.set_xlabel(xlabel)
#     ax.set_ylabel(ylabel)
#     plt.xticks(rotation=20, ha="right")
#     plt.tight_layout()
#     plt.savefig(OUT / filename, dpi=160)
#     plt.close()
#
#
# # ============================================================
# # 4. ЗАГРУЗКА СТАТИСТИКИ ОБОИХ ПАРСЕРОВ
# # ============================================================
#
# stats_parts = []
#
# for path, parser_name in [
#     (CSHARP_STATS, "C# HtmlAgilityPack"),
#     (PYTHON_STATS, "Python Scrapy")
# ]:
#     data = normalize_columns(read_csv(path))
#
#     if not data.empty:
#         data["parser"] = parser_name
#         stats_parts.append(data)
#
# if stats_parts:
#     stats = pd.concat(
#         stats_parts,
#         ignore_index=True,
#         sort=False
#     )
# else:
#     stats = pd.DataFrame()
#
# if not stats.empty:
#     stats = clean_text_columns(stats)
#
#     # Преобразуем числовые показатели
#     for column in [
#         "page", "pages", "found_links",
#         "unique_added", "elapsed", "elapsed_ms"
#     ]:
#         if column in stats.columns:
#             stats[column] = pd.to_numeric(
#                 stats[column], errors="coerce"
#             )
#
#     # Время из C# в примере хранится в миллисекундах.
#     # Переводим в секунды для сопоставимости.
#     if "elapsed_ms" in stats.columns:
#         if "elapsed" not in stats.columns:
#             stats["elapsed"] = stats["elapsed_ms"] / 1000
#         else:
#             missing_time = stats["elapsed"].isna()
#             stats.loc[missing_time, "elapsed"] = (
#                 stats.loc[missing_time, "elapsed_ms"] / 1000
#             )
#
#     save_csv(stats, "combined_testing_stats.csv")
#
#     print("\n=== СТАТИСТИКА ПАРСИНГА ===")
#     print(stats.head(10).to_string(index=False))
# else:
#     print(
#         "\nСтатистика парсинга не загружена. "
#         "Графики по времени и страницам построить нельзя."
#     )
#
#
# # ============================================================
# # 5. ГРАФИК: СРЕДНЕЕ ВРЕМЯ ОБРАБОТКИ
# # ============================================================
#
# if not stats.empty and "elapsed" in stats.columns:
#     timing = stats.dropna(subset=["elapsed"]).copy()
#
#     if not timing.empty:
#         average_time = timing.groupby("parser")["elapsed"].mean()
#
#         save_csv(
#             average_time.rename("Среднее время, сек")
#             .reset_index(),
#             "average_processing_time.csv"
#         )
#
#         save_bar_chart(
#             average_time,
#             "Среднее время обработки страницы",
#             "Парсер",
#             "Время, секунды",
#             "01_average_processing_time.png"
#         )
#
#         # График времени по страницам.
#         # Если несколько запросов используют одинаковые номера страниц,
#         # вычисляем среднее время для каждого номера.
#         if "page" in timing.columns:
#             page_time = (
#                 timing.dropna(subset=["page"])
#                 .groupby(["parser", "page"])["elapsed"]
#                 .mean()
#                 .reset_index()
#             )
#
#             if not page_time.empty:
#                 for parser_name, group in page_time.groupby("parser"):
#                     group = group.sort_values("page")
#                     plt.plot(
#                         group["page"],
#                         group["elapsed"],
#                         marker="o",
#                         label=parser_name
#                     )
#
#                 plt.title("Время обработки по номеру страницы")
#                 plt.xlabel("Номер страницы")
#                 plt.ylabel("Среднее время, секунды")
#                 plt.legend()
#                 plt.tight_layout()
#                 plt.savefig(
#                     OUT / "02_time_by_page.png",
#                     dpi=160
#                 )
#                 plt.close()
#
#
# # ============================================================
# # 6. ГРАФИК: КОЛИЧЕСТВО НАЙДЕННЫХ ССЫЛОК
# # ============================================================
#
# if not stats.empty and "found_links" in stats.columns:
#     found = stats.dropna(subset=["found_links"])
#
#     if not found.empty:
#         found_sum = found.groupby("parser")["found_links"].sum()
#
#         save_csv(
#             found_sum.rename("Количество найденных ссылок")
#             .reset_index(),
#             "found_links_by_parser.csv"
#         )
#
#         save_bar_chart(
#             found_sum,
#             "Суммарное количество найденных ссылок",
#             "Парсер",
#             "Количество ссылок",
#             "03_found_links.png"
#         )
#
#         # Распределение найденных ссылок по номерам страниц
#         if "page" in found.columns:
#             page_found = (
#                 found.dropna(subset=["page"])
#                 .groupby(["parser", "page"])["found_links"]
#                 .mean()
#                 .reset_index()
#             )
#
#             if not page_found.empty:
#                 for parser_name, group in page_found.groupby("parser"):
#                     group = group.sort_values("page")
#                     plt.plot(
#                         group["page"],
#                         group["found_links"],
#                         marker="o",
#                         label=parser_name
#                     )
#
#                 plt.title("Найденные ссылки по номеру страницы")
#                 plt.xlabel("Номер страницы")
#                 plt.ylabel("Среднее количество ссылок")
#                 plt.legend()
#                 plt.tight_layout()
#                 plt.savefig(
#                     OUT / "04_found_by_page.png",
#                     dpi=160
#                 )
#                 plt.close()
#
#
# # ============================================================
# # 7. СТАТУСЫ ЗАПРОСОВ
# # ============================================================
#
# if not stats.empty and "status" in stats.columns:
#     status_table = (
#         stats.groupby(["parser", "status"], dropna=False)
#         .size()
#         .reset_index(name="Количество")
#     )
#
#     save_csv(status_table, "request_statuses.csv")
#
#     status_pivot = status_table.pivot(
#         index="status",
#         columns="parser",
#         values="Количество"
#     ).fillna(0)
#
#     ax = status_pivot.plot(
#         kind="bar",
#         figsize=(9, 5)
#     )
#     ax.set_title("Распределение статусов запросов")
#     ax.set_xlabel("Статус")
#     ax.set_ylabel("Количество записей")
#     plt.xticks(rotation=25, ha="right")
#     plt.tight_layout()
#     plt.savefig(OUT / "05_request_statuses.png", dpi=160)
#     plt.close()
#
#
# # ============================================================
# # 8. ЗАГРУЗКА ВАКАНСИЙ ОБОИХ ПАРСЕРОВ
# # ============================================================
#
# vacancy_parts = []
#
# for path, parser_name in [
#     (CSHARP_VACANCIES, "C# HtmlAgilityPack"),
#     (PYTHON_VACANCIES, "Python Scrapy")
# ]:
#     data = normalize_columns(read_csv(path))
#
#     if not data.empty:
#         data["parser"] = parser_name
#         vacancy_parts.append(data)
#
# if vacancy_parts:
#     vacancies = pd.concat(
#         vacancy_parts,
#         ignore_index=True,
#         sort=False
#     )
#
#     vacancies = normalize_columns(vacancies)
#     vacancies = clean_text_columns(vacancies)
#     vacancies = vacancies.dropna(how="all")
#
#     save_csv(vacancies, "vacancies_combined_all.csv")
#
#     # Число строк в исходных результатах каждого парсера.
#     # Это количество записей, а не обязательно уникальных вакансий.
#     counts = vacancies.groupby("parser").size()
#
#     save_csv(
#         counts.rename("Количество записей").reset_index(),
#         "vacancy_counts.csv"
#     )
#
#     save_bar_chart(
#         counts,
#         "Количество записей о вакансиях",
#         "Парсер",
#         "Количество записей",
#         "06_vacancy_counts.png"
#     )
#
#     # ========================================================
#     # 9. СРАВНЕНИЕ ЗАПОЛНЕННОСТИ ПОЛЕЙ
#     # ========================================================
#
#     fields = [
#         field for field in [
#             "title", "company", "city",
#             "salary", "level", "work_format",
#             "skills", "link"
#         ]
#         if field in vacancies.columns
#     ]
#
#     completeness = []
#
#     for parser_name, group in vacancies.groupby("parser"):
#         for field in fields:
#             # Если названия столбцов не дублируются,
#             # group[field] является Series.
#             values = group[field].fillna("").astype(str).str.strip()
#             filled = int(values.ne("").sum())
#
#             completeness.append({
#                 "Парсер": parser_name,
#                 "Поле": field,
#                 "Заполнено записей": filled,
#                 "Всего записей": len(group),
#                 "Заполнено, %": round(
#                     filled / len(group) * 100, 2
#                 ) if len(group) else 0
#             })
#
#     if completeness:
#         completeness_df = pd.DataFrame(completeness)
#         save_csv(completeness_df, "field_completeness.csv")
#
#         pivot = completeness_df.pivot(
#             index="Поле",
#             columns="Парсер",
#             values="Заполнено, %"
#         )
#
#         ax = pivot.plot(
#             kind="bar",
#             figsize=(10, 6)
#         )
#         ax.set_title("Полнота извлечения полей вакансий")
#         ax.set_xlabel("Поле")
#         ax.set_ylabel("Заполнено, %")
#         ax.set_ylim(0, 100)
#         plt.xticks(rotation=25, ha="right")
#         plt.tight_layout()
#         plt.savefig(
#             OUT / "07_field_completeness.png",
#             dpi=160
#         )
#         plt.close()
#
#     # ========================================================
#     # 10. СОДЕРЖАТЕЛЬНАЯ СТАТИСТИКА
#     # ========================================================
#
#     # Количество вакансий по сайтам
#     if "source" in vacancies.columns:
#         by_source = (
#             vacancies[vacancies["source"].ne("")]
#             .groupby(["parser", "source"])
#             .size()
#             .reset_index(name="Количество записей")
#         )
#         save_csv(by_source, "vacancies_by_source_and_parser.csv")
#
#     # Распределение по поисковым запросам
#     if "query" in vacancies.columns:
#         by_query = (
#             vacancies[vacancies["query"].ne("")]
#             .groupby(["parser", "query"])
#             .size()
#             .reset_index(name="Количество записей")
#         )
#         save_csv(by_query, "vacancies_by_query_and_parser.csv")
#
#     # Топ-10 городов
#     if "city" in vacancies.columns:
#         cities = (
#             vacancies["city"]
#             .replace("", pd.NA)
#             .dropna()
#             .value_counts()
#             .head(10)
#         )
#
#         if not cities.empty:
#             save_csv(
#                 cities.rename_axis("Город")
#                 .rename("Количество вакансий")
#                 .reset_index(),
#                 "vacancies_by_city.csv"
#             )
#
#             cities.sort_values().plot(kind="barh", figsize=(9, 5))
#             plt.title("Топ-10 городов по количеству записей")
#             plt.xlabel("Количество записей")
#             plt.ylabel("Город")
#             plt.tight_layout()
#             plt.savefig(OUT / "08_by_city.png", dpi=160)
#             plt.close()
#
# else:
#     print(
#         "\nФайлы с вакансиями не найдены. "
#         "Проверь CSHARP_VACANCIES и PYTHON_VACANCIES."
#     )
#
#
# # ============================================================
# # 11. ЗАВЕРШЕНИЕ
# # ============================================================
#
# print("\n========== АНАЛИЗ ЗАВЕРШЁН ==========")
# print(f"Папка с результатами: {OUT.resolve()}")
#
# print("\nСозданные графики:")
# for file in sorted(OUT.glob("*.png")):
#     print(f" - {file.name}")
#
# print("\nСозданные таблицы:")
# for file in sorted(OUT.glob("*.csv")):
#     print(f" - {file.name}")

from pathlib import Path
import csv
import re
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# 1. ПУТИ К ФАЙЛАМ
# ============================================================
CSHARP_DIR = Path(r"C:\Data\Projects\web_mining\lab5\Csharp_parser\TestRabotaParser")
PYTHON_DIR = Path(r"C:\Data\Projects\web_mining\lab5\PythonParser\TestRabotaParser")

CSHARP_STATS = CSHARP_DIR / "parsing_stats_all.csv"
PYTHON_STATS = PYTHON_DIR / "parsing_stats_all.csv"

CSHARP_VACANCIES = CSHARP_DIR / "vacancies_all.csv"
PYTHON_VACANCIES = PYTHON_DIR / "vacancies_all.csv"

# Оба парсера записывают сводку запуска.
CSHARP_SUMMARY = CSHARP_DIR / "run_summary.csv"
PYTHON_SUMMARY = PYTHON_DIR / "run_summary.csv"

OUT = Path("testing_results")
OUT.mkdir(parents=True, exist_ok=True)

PARSER_NAMES = ["C# HtmlAgilityPack", "Python Scrapy"]

# Файлы, создаваемые этим скриптом. При повторном запуске старые версии
# удаляются, чтобы не спутать результаты текущего запуска с прежними.
GENERATED_FILES = [
    "combined_testing_stats.csv",
    "average_response_time.csv",
    "response_time_by_page.csv",
    "found_links_by_parser.csv",
    "unique_added_by_parser.csv",
    "request_statuses.csv",
    "combined_run_summary.csv",
    "vacancies_combined_all.csv",
    "vacancy_counts.csv",
    "field_completeness.csv",
    "vacancies_by_source_and_parser.csv",
    "vacancies_by_query_and_parser.csv",
    "vacancies_by_city.csv",
    "vacancy_duplicates_by_parser.csv",
    "01_average_response_time.png",
    "02_response_time_by_page.png",
    "03_found_links_by_parser.png",
    "04_unique_added_by_parser.png",
    "05_request_statuses.png",
    "06_total_runtime.png",
    "07_vacancy_counts.png",
    "08_field_completeness.png",
    "09_vacancies_by_source.png",
    "10_top_cities.png",
]
for filename in GENERATED_FILES:
    target = OUT / filename
    if target.exists():
        target.unlink()


# ============================================================
# 2. ЧТЕНИЕ CSV
# ============================================================
def detect_separator(path: Path) -> str:
    """Определяет разделитель по первой непустой строке заголовка."""
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        for line in f:
            if line.strip():
                # В заголовках файлов парсеров разделители — запятая или точка с запятой.
                semicolons = line.count(";")
                commas = line.count(",")
                return ";" if semicolons > commas else ","
    return ","


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[ИНФО] Файл не найден: {path}")
        return pd.DataFrame()

    try:
        separator = detect_separator(path)
        data = pd.read_csv(
            path,
            sep=separator,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
            quoting=csv.QUOTE_MINIMAL,
            on_bad_lines="warn",
        )
        data.columns = data.columns.astype(str).str.strip().str.replace("\ufeff", "", regex=False)
        data = data.loc[:, ~data.columns.duplicated()]
        print(
            f"\nФайл: {path}\n"
            f"Разделитель: {separator!r}\n"
            f"Строк: {len(data)}\n"
            f"Столбцы: {data.columns.tolist()}"
        )
        return data
    except Exception as exc:
        print(f"[ОШИБКА] Не удалось прочитать {path}: {exc}")
        return pd.DataFrame()


# ============================================================
# 3. НОРМАЛИЗАЦИЯ СТОЛБЦОВ
# ============================================================
def canonical_column(name: str) -> str:
    """Сопоставляет русские и английские заголовки с едиными именами."""
    original = str(name).strip().replace("\ufeff", "")
    key = re.sub(r"\s+", " ", original).strip().lower()

    aliases = {
        # Статистика страниц
        "источник": "source",
        "source": "source",
        "поисковый запрос": "query",
        "query": "query",
        "страница": "page",
        "номер страницы": "page",
        "page": "page",
        "найдено ссылок": "found_links",
        "найдено вакансий": "found_links",
        "found links": "found_links",
        "found_links": "found_links",
        "found": "found_links",
        "добавлено уникальных": "unique_added",
        "уникальных добавлено": "unique_added",
        "unique added": "unique_added",
        "unique_added": "unique_added",
        "added": "unique_added",
        "время ответа поисковой страницы, мс": "search_response_ms",
        "время ответа, мс": "search_response_ms",
        "search_response_ms": "search_response_ms",
        "elapsed_ms": "elapsed_ms",
        "elapsed ms": "elapsed_ms",
        "время, мс": "elapsed_ms",
        "время выполнения, мс": "elapsed_ms",
        "elapsed_seconds": "elapsed_seconds",
        "elapsed seconds": "elapsed_seconds",
        "elapsed": "elapsed_seconds",
        "время, сек": "elapsed_seconds",
        "время выполнения": "elapsed_seconds",
        "время выполнения, сек": "elapsed_seconds",
        "статус": "status",
        "status": "status",

        # Сводка запуска
        "парсер": "parser",
        "parser": "parser",
        "общее время, сек": "total_elapsed_seconds",
        "общее время выполнения, сек": "total_elapsed_seconds",
        "total_elapsed_seconds": "total_elapsed_seconds",
        "unique_vacancies": "unique_vacancies",
        "уникальных вакансий": "unique_vacancies",
        "search_pages": "search_pages",
        "поисковых страниц": "search_pages",
        "detail_requests": "detail_requests",
        "запросов к страницам вакансий": "detail_requests",
        "errors": "errors",
        "ошибок": "errors",

        # Вакансии
        "дата сбора": "date_collected",
        "date_collected": "date_collected",
        "date": "date_collected",
        "название": "title",
        "название вакансии": "title",
        "title": "title",
        "компания": "company",
        "company": "company",
        "город": "city",
        "city": "city",
        "зарплата": "salary",
        "salary": "salary",
        "уровень": "level",
        "level": "level",
        "формат работы": "work_format",
        "work format": "work_format",
        "work_format": "work_format",
        "навыки": "skills",
        "skills": "skills",
        "ссылка": "link",
        "link": "link",
    }
    return aliases.get(key, original)


def normalize_columns(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data
    result = data.copy()
    result.columns = [canonical_column(c) for c in result.columns]
    return result.loc[:, ~result.columns.duplicated()]


def clean_text_columns(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    for column in result.select_dtypes(include=["object"]).columns:
        result[column] = result[column].fillna("").astype(str).str.strip()
    return result


def numeric_columns(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = data.copy()
    for column in columns:
        if column in result.columns:
            result[column] = (
                result[column].astype(str)
                .str.replace(",", ".", regex=False)
                .str.strip()
            )
            result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def save_csv(data: pd.DataFrame, filename: str) -> None:
    data.to_csv(OUT / filename, index=False, encoding="utf-8-sig")
    print(f"Создана таблица: {OUT / filename}")


def save_bar_chart(series: pd.Series, title: str, xlabel: str, ylabel: str,
                   filename: str, rotation: int = 20) -> None:
    if series is None or series.empty:
        print(f"[ПРОПУСК] Нет данных для графика: {title}")
        return
    ax = series.plot(kind="bar", figsize=(9, 5))
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=rotation, ha="right")
    plt.tight_layout()
    plt.savefig(OUT / filename, dpi=180)
    plt.close()
    print(f"Создан график: {OUT / filename}")


def save_grouped_bar(pivot: pd.DataFrame, title: str, xlabel: str, ylabel: str,
                     filename: str, rotation: int = 20, ylim=None) -> None:
    if pivot is None or pivot.empty:
        print(f"[ПРОПУСК] Нет данных для графика: {title}")
        return
    ax = pivot.plot(kind="bar", figsize=(10, 6))
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(*ylim)
    plt.xticks(rotation=rotation, ha="right")
    plt.tight_layout()
    plt.savefig(OUT / filename, dpi=180)
    plt.close()
    print(f"Создан график: {OUT / filename}")


# ============================================================
# 4. ЗАГРУЗКА И АНАЛИЗ СТАТИСТИКИ СТРАНИЦ
# ============================================================
stats_parts = []
for path, parser_name in [
    (CSHARP_STATS, "C# HtmlAgilityPack"),
    (PYTHON_STATS, "Python Scrapy"),
]:
    part = normalize_columns(read_csv(path))
    if not part.empty:
        part["parser"] = parser_name
        stats_parts.append(part)

stats = pd.concat(stats_parts, ignore_index=True, sort=False) if stats_parts else pd.DataFrame()

if not stats.empty:
    stats = clean_text_columns(stats)
    stats = numeric_columns(
        stats,
        ["page", "found_links", "unique_added", "search_response_ms",
         "elapsed_ms", "elapsed_seconds", "status"],
    )

    # Единое поле времени ответа поисковой страницы в секундах.
    # C# «Время ответа поисковой страницы, мс» и Python search_response_ms
    # оба нормализуются в search_response_ms.
    stats["response_time_seconds"] = pd.NA
    if "search_response_ms" in stats.columns:
        stats["response_time_seconds"] = stats["search_response_ms"] / 1000.0

    # Резервные имена на случай другого формата файла.
    if "elapsed_ms" in stats.columns:
        mask = stats["response_time_seconds"].isna()
        stats.loc[mask, "response_time_seconds"] = stats.loc[mask, "elapsed_ms"] / 1000.0
    if "elapsed_seconds" in stats.columns:
        mask = stats["response_time_seconds"].isna()
        stats.loc[mask, "response_time_seconds"] = stats.loc[mask, "elapsed_seconds"]

    stats["response_time_seconds"] = pd.to_numeric(
        stats["response_time_seconds"], errors="coerce"
    )
    save_csv(stats, "combined_testing_stats.csv")

    print("\n=== Статистика страниц обоих парсеров ===")
    print(stats.head(12).to_string(index=False))

    # 4.1 Среднее время ответа поисковой страницы
    timing = stats.dropna(subset=["response_time_seconds"]).copy()
    timing = timing[timing["response_time_seconds"] >= 0]
    if not timing.empty:
        average_time = timing.groupby("parser")["response_time_seconds"].mean()
        save_csv(
            average_time.rename("Среднее время ответа, сек").reset_index(),
            "average_response_time.csv",
        )
        save_bar_chart(
            average_time,
            "Среднее время ответа поисковой страницы",
            "Парсер", "Время, секунды",
            "01_average_response_time.png",
        )

        # 4.2 Время ответа по номеру страницы
        if "page" in timing.columns:
            page_time = (
                timing.dropna(subset=["page"])
                .groupby(["parser", "page"])["response_time_seconds"]
                .mean()
                .reset_index()
            )
            save_csv(page_time, "response_time_by_page.csv")
            if not page_time.empty:
                for parser_name, group in page_time.groupby("parser"):
                    group = group.sort_values("page")
                    plt.plot(
                        group["page"], group["response_time_seconds"],
                        marker="o", label=parser_name,
                    )
                plt.title("Время ответа поисковой страницы по номеру страницы")
                plt.xlabel("Номер страницы")
                plt.ylabel("Время ответа, секунды")
                plt.legend()
                plt.tight_layout()
                plt.savefig(OUT / "02_response_time_by_page.png", dpi=180)
                plt.close()
                print(f"Создан график: {OUT / '02_response_time_by_page.png'}")
    else:
        print("[ПРЕДУПРЕЖДЕНИЕ] Не удалось найти числовые данные о времени ответа.")

    # 4.3 Найденные ссылки суммарно
    if "found_links" in stats.columns:
        found = stats.dropna(subset=["found_links"])
        if not found.empty:
            found_sum = found.groupby("parser")["found_links"].sum()
            save_csv(found_sum.rename("Сумма найденных ссылок").reset_index(),
                     "found_links_by_parser.csv")
            save_bar_chart(
                found_sum, "Суммарное количество найденных ссылок",
                "Парсер", "Количество ссылок", "03_found_links_by_parser.png",
            )

    # 4.4 Уникальные вакансии, добавленные на поисковых страницах.
    if "unique_added" in stats.columns:
        added = stats.dropna(subset=["unique_added"]).groupby("parser")["unique_added"].sum()
        if not added.empty:
            save_csv(added.rename("Добавлено уникальных по статистике страниц").reset_index(),
                     "unique_added_by_parser.csv")
            save_bar_chart(
                added, "Сумма уникальных добавлений по статистике страниц",
                "Парсер", "Количество", "04_unique_added_by_parser.png",
            )

    # 4.5 Статусы страниц
    if "status" in stats.columns:
        status_data = stats[stats["status"].astype(str).str.strip().ne("")]
        if not status_data.empty:
            status_table = (
                status_data.groupby(["parser", "status"])
                .size().reset_index(name="Количество страниц")
            )
            save_csv(status_table, "request_statuses.csv")
            pivot = status_table.pivot(
                index="status", columns="parser", values="Количество страниц"
            ).fillna(0)
            save_grouped_bar(
                pivot, "Статусы обработки поисковых страниц",
                "Статус", "Количество страниц", "05_request_statuses.png",
            )
else:
    print("[ПРЕДУПРЕЖДЕНИЕ] Статистика страниц не загружена. Проверьте пути и CSV.")


# ============================================================
# 5. СВОДКИ ЗАПУСКА ОБОИХ ПАРСЕРОВ
# ============================================================
summary_parts = []
for path, fallback_name in [
    (CSHARP_SUMMARY, "C# HtmlAgilityPack"),
    (PYTHON_SUMMARY, "Python Scrapy"),
]:
    part = normalize_columns(read_csv(path))
    if part.empty:
        continue
    if "parser" not in part.columns:
        part["parser"] = fallback_name
    else:
        part["parser"] = part["parser"].replace("", fallback_name)
    summary_parts.append(part)

summary = pd.concat(summary_parts, ignore_index=True, sort=False) if summary_parts else pd.DataFrame()

if not summary.empty:
    summary = clean_text_columns(summary)
    summary = numeric_columns(
        summary,
        ["total_elapsed_seconds", "unique_vacancies", "search_pages",
         "detail_requests", "errors"],
    )
    save_csv(summary, "combined_run_summary.csv")
    print("\n=== Общая сводка запусков обоих парсеров ===")
    print(summary.to_string(index=False))

    # Сравнение общего времени запуска строится только если время есть у обоих
    # либо хотя бы у одного парсера. Отсутствующие значения не подменяются нулём.
    if "total_elapsed_seconds" in summary.columns:
        runtime = summary.dropna(subset=["total_elapsed_seconds"])
        if not runtime.empty:
            runtime_series = runtime.groupby("parser")["total_elapsed_seconds"].mean()
            save_bar_chart(
                runtime_series,
                "Общее время выполнения парсеров",
                "Парсер", "Время выполнения, секунды", "06_total_runtime.png",
            )
else:
    print("[ИНФО] Не найдены сводки run_summary.csv. Сравнение общего времени пропущено.")


# ============================================================
# 6. ЗАГРУЗКА И СРАВНЕНИЕ СОБРАННЫХ ВАКАНСИЙ
# ============================================================
vacancy_parts = []
for path, parser_name in [
    (CSHARP_VACANCIES, "C# HtmlAgilityPack"),
    (PYTHON_VACANCIES, "Python Scrapy"),
]:
    part = normalize_columns(read_csv(path))
    if not part.empty:
        part["parser"] = parser_name
        vacancy_parts.append(part)

vacancies = pd.concat(vacancy_parts, ignore_index=True, sort=False) if vacancy_parts else pd.DataFrame()

if not vacancies.empty:
    vacancies = clean_text_columns(normalize_columns(vacancies))
    vacancies = vacancies.dropna(how="all")
    save_csv(vacancies, "vacancies_combined_all.csv")

    # 6.1 Число строк/вакансий в сохранённых файлах
    counts = vacancies.groupby("parser").size()
    save_csv(counts.rename("Количество записей").reset_index(), "vacancy_counts.csv")
    save_bar_chart(
        counts, "Количество собранных записей о вакансиях",
        "Парсер", "Количество записей", "07_vacancy_counts.png",
    )

    # 6.2 Полнота заполнения основных полей
    fields = [
        f for f in ["title", "company", "city", "salary", "level",
                    "work_format", "skills", "link"]
        if f in vacancies.columns
    ]
    completeness = []
    for parser_name, group in vacancies.groupby("parser"):
        for field in fields:
            values = group[field].fillna("").astype(str).str.strip()
            filled = int(values.ne("").sum())
            completeness.append({
                "Парсер": parser_name,
                "Поле": field,
                "Заполнено записей": filled,
                "Всего записей": len(group),
                "Заполнено, %": round(filled / len(group) * 100, 2) if len(group) else 0,
            })

    if completeness:
        completeness_df = pd.DataFrame(completeness)
        save_csv(completeness_df, "field_completeness.csv")
        pivot = completeness_df.pivot(
            index="Поле", columns="Парсер", values="Заполнено, %"
        )
        save_grouped_bar(
            pivot, "Полнота извлечения полей вакансий",
            "Поле", "Заполнено, %", "08_field_completeness.png",
            rotation=25, ylim=(0, 100),
        )

    # 6.3 Количество вакансий по сайтам-источникам
    if "source" in vacancies.columns:
        by_source = (
            vacancies[vacancies["source"].ne("")]
            .groupby(["parser", "source"])
            .size().reset_index(name="Количество записей")
        )
        save_csv(by_source, "vacancies_by_source_and_parser.csv")
        if not by_source.empty:
            source_pivot = by_source.pivot(
                index="source", columns="parser", values="Количество записей"
            ).fillna(0)
            save_grouped_bar(
                source_pivot, "Количество записей по сайтам-источникам",
                "Источник вакансий", "Количество записей",
                "09_vacancies_by_source.png", rotation=20,
            )

    # 6.4 Количество вакансий по поисковым запросам
    if "query" in vacancies.columns:
        by_query = (
            vacancies[vacancies["query"].ne("")]
            .groupby(["parser", "query"])
            .size().reset_index(name="Количество записей")
        )
        save_csv(by_query, "vacancies_by_query_and_parser.csv")

    # 6.5 Топ городов по всем загруженным записям
    if "city" in vacancies.columns:
        cities = vacancies["city"].replace("", pd.NA).dropna().value_counts().head(10)
        if not cities.empty:
            save_csv(
                cities.rename_axis("Город").rename("Количество записей").reset_index(),
                "vacancies_by_city.csv",
            )
            ax = cities.sort_values().plot(kind="barh", figsize=(9, 5))
            ax.set_title("Топ-10 городов по количеству записей обоих парсеров")
            ax.set_xlabel("Количество записей")
            ax.set_ylabel("Город")
            plt.tight_layout()
            plt.savefig(OUT / "10_top_cities.png", dpi=180)
            plt.close()
            print(f"Создан график: {OUT / '10_top_cities.png'}")

    # 6.6 Проверка повторов внутри файла каждого парсера по ссылке.
    if "link" in vacancies.columns:
        duplicate_rows = []
        for parser_name, group in vacancies.groupby("parser"):
            links = group["link"].astype(str).str.strip()
            nonempty_links = links[links.ne("")]
            duplicate_rows.append({
                "Парсер": parser_name,
                "Всего записей": len(group),
                "Записей с непустой ссылкой": int(links.ne("").sum()),
                "Уникальных непустых ссылок": int(nonempty_links.nunique()),
                "Повторных ссылок": int(nonempty_links.duplicated().sum()),
            })
        save_csv(pd.DataFrame(duplicate_rows), "vacancy_duplicates_by_parser.csv")
else:
    print("[ПРЕДУПРЕЖДЕНИЕ] Файлы вакансий не загружены. Проверьте пути и CSV.")


# ============================================================
# 7. ИТОГ
# ============================================================
print("\n========== АНАЛИЗ ЗАВЕРШЁН ==========")
print(f"Папка с результатами: {OUT.resolve()}")

print("\nСозданные графики:")
for file in sorted(OUT.glob("*.png")):
    print(f" - {file.name}")

print("\nСозданные таблицы:")
for file in sorted(OUT.glob("*.csv")):
    print(f" - {file.name}")

