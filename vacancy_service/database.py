from pathlib import Path
import sqlite3
import json
from datetime import datetime


def connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path):
    with connect(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            url TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            region TEXT NOT NULL DEFAULT '',
            salary TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            skills TEXT NOT NULL DEFAULT '',
            query TEXT NOT NULL DEFAULT '',
            collected_at TEXT NOT NULL,
            parser TEXT NOT NULL DEFAULT '',
            UNIQUE(source, url)
        );

        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parser TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            message TEXT NOT NULL DEFAULT '',
            vacancies_saved INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS parsing_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            parser TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            query TEXT NOT NULL DEFAULT '',
            page INTEGER,
            found_links INTEGER,
            unique_added INTEGER,
            elapsed_ms REAL,
            status TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(run_id) REFERENCES runs(id)
        );

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            module TEXT NOT NULL,
            message TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_vacancies_source
            ON vacancies(source);
        CREATE INDEX IF NOT EXISTS idx_vacancies_title
            ON vacancies(title);
        CREATE INDEX IF NOT EXISTS idx_vacancies_region
            ON vacancies(region);
        CREATE INDEX IF NOT EXISTS idx_logs_run
            ON logs(run_id);
        """)


def log_event(db_path, level, module, message, run_id=None):
    with connect(db_path) as conn:
        conn.execute("""
            INSERT INTO logs(run_id, timestamp, level, module, message)
            VALUES (?, ?, ?, ?, ?)
        """, (
            run_id,
            datetime.now().isoformat(timespec="seconds"),
            level,
            module,
            str(message)
        ))


def create_run(db_path, parser):
    with connect(db_path) as conn:
        cur = conn.execute("""
            INSERT INTO runs(parser, started_at, status)
            VALUES (?, ?, 'Выполняется')
        """, (parser, datetime.now().isoformat(timespec="seconds")))
        return cur.lastrowid


def finish_run(db_path, run_id, status, message="", saved=0):
    with connect(db_path) as conn:
        conn.execute("""
            UPDATE runs
            SET finished_at = ?, status = ?, message = ?,
                vacancies_saved = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(timespec="seconds"),
            status, message, saved, run_id
        ))


def save_vacancies(db_path, records):
    saved = 0

    with connect(db_path) as conn:
        for row in records:
            source = str(row.get("source", "")).strip() or "Не указан"
            url = str(row.get("url", "")).strip()
            title = str(row.get("title", "")).strip()

            # Без ссылки невозможно надёжно определить уникальность.
            # Для таких записей создаём ключ по основным полям.
            if not url:
                url = "no-url:" + "|".join([
                    title,
                    str(row.get("company", "")).strip(),
                    str(row.get("region", "")).strip(),
                    str(row.get("query", "")).strip()
                ])

            values = (
                source, url, title,
                str(row.get("company", "")).strip(),
                str(row.get("region", "")).strip(),
                str(row.get("salary", "")).strip(),
                str(row.get("description", "")).strip(),
                str(row.get("skills", "")).strip(),
                str(row.get("query", "")).strip(),
                str(row.get("collected_at", "")).strip()
                    or datetime.now().isoformat(timespec="seconds"),
                str(row.get("parser", "")).strip()
            )

            cur = conn.execute("""
                INSERT INTO vacancies (
                    source, url, title, company, region, salary,
                    description, skills, query, collected_at, parser
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, url) DO UPDATE SET
                    title = CASE WHEN excluded.title != ''
                        THEN excluded.title ELSE vacancies.title END,
                    company = CASE WHEN excluded.company != ''
                        THEN excluded.company ELSE vacancies.company END,
                    region = CASE WHEN excluded.region != ''
                        THEN excluded.region ELSE vacancies.region END,
                    salary = CASE WHEN excluded.salary != ''
                        THEN excluded.salary ELSE vacancies.salary END,
                    description = CASE WHEN excluded.description != ''
                        THEN excluded.description
                        ELSE vacancies.description END,
                    skills = CASE WHEN excluded.skills != ''
                        THEN excluded.skills ELSE vacancies.skills END,
                    query = CASE WHEN excluded.query != ''
                        THEN excluded.query ELSE vacancies.query END
            """, values)

            # rowcount зависит от результата UPSERT; считаем только
            # новые записи отдельно по total_changes здесь не используем.
            if cur.rowcount > 0:
                saved += 1

    return saved


def save_stats(db_path, parser, stats, run_id=None):
    with connect(db_path) as conn:
        for row in stats:
            conn.execute("""
                INSERT INTO parsing_stats (
                    run_id, parser, source, query, page,
                    found_links, unique_added, elapsed_ms, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                parser,
                str(row.get("source", "")),
                str(row.get("query", "")),
                _int_or_none(row.get("page")),
                _int_or_none(row.get("found_links")),
                _int_or_none(row.get("unique_added")),
                _float_or_none(row.get("elapsed_ms")),
                str(row.get("status", ""))
            ))


def _int_or_none(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _float_or_none(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (ValueError, TypeError):
        return None
