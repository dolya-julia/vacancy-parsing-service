
import re
import pandas as pd

from database import connect


def get_table(db_path, table):
    allowed = {"vacancies", "runs", "parsing_stats", "logs"}
    if table not in allowed:
        raise ValueError("Недопустимая таблица")

    with connect(db_path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)


def get_vacancies(db_path):
    return get_table(db_path, "vacancies")


def get_runs(db_path):
    return get_table(db_path, "runs")


def get_stats(db_path):
    return get_table(db_path, "parsing_stats")


def get_logs(db_path):
    return get_table(db_path, "logs")


def source_summary(vacancies):
    if vacancies.empty:
        return pd.DataFrame(columns=["source", "count"])

    return (
        vacancies.groupby("source", dropna=False)
        .size().reset_index(name="count")
        .sort_values("count", ascending=False)
    )


def region_summary(vacancies):
    if vacancies.empty:
        return pd.DataFrame(columns=["region", "count"])

    data = vacancies.copy()
    data["region"] = data["region"].replace("", "Не указан")

    return (
        data.groupby("region", dropna=False)
        .size().reset_index(name="count")
        .sort_values("count", ascending=False)
    )


def skill_summary(vacancies):
    """Частота слов из поля навыков и описания вакансий."""
    if vacancies.empty:
        return pd.DataFrame(columns=["skill", "mentions"])

    text = (
        vacancies["skills"].fillna("").astype(str) + " " +
        vacancies["description"].fillna("").astype(str)
    ).str.lower()

    # Частоты считаются по словарю навыков.
    # Словарь можно расширять под направления исследования.
    dictionary = [
        "python", "sql", "pandas", "numpy", "scikit-learn",
        "machine learning", "deep learning", "pytorch",
        "tensorflow", "docker", "git", "linux", "java",
        "c#", "c++", "computer vision", "nlp", "statistics",
        "data analysis", "power bi", "tableau", "spark"
    ]

    rows = []
    for skill in dictionary:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        mentions = int(text.str.count(pattern).sum())
        if mentions:
            rows.append({"skill": skill, "mentions": mentions})

    return pd.DataFrame(rows).sort_values(
        "mentions", ascending=False
    ) if rows else pd.DataFrame(columns=["skill", "mentions"])


def field_completeness(vacancies):
    fields = [
        "title", "company", "region", "salary",
        "description", "skills", "url"
    ]

    rows = []
    total = len(vacancies)

    for field in fields:
        if total == 0:
            filled = 0
        else:
            filled = int(
                vacancies[field].fillna("").astype(str)
                .str.strip().ne("").sum()
            )

        rows.append({
            "field": field,
            "filled": filled,
            "missing": total - filled,
            "completeness_percent": (
                round(filled / total * 100, 2) if total else 0
            )
        })

    return pd.DataFrame(rows)


def stats_summary(stats):
    if stats.empty:
        return pd.DataFrame()

    data = stats.copy()
    data["elapsed_ms"] = pd.to_numeric(
        data["elapsed_ms"], errors="coerce"
    )
    data["found_links"] = pd.to_numeric(
        data["found_links"], errors="coerce"
    )
    data["unique_added"] = pd.to_numeric(
        data["unique_added"], errors="coerce"
    )

    return (
        data.groupby("parser", dropna=False)
        .agg(
            pages=("page", "count"),
            avg_elapsed_ms=("elapsed_ms", "mean"),
            total_found_links=("found_links", "sum"),
            total_unique_added=("unique_added", "sum")
        )
        .reset_index()
    )
