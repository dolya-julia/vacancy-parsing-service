
import json
import subprocess
import time
from pathlib import Path

import pandas as pd

from database import (
    init_db, create_run, finish_run, log_event,
    save_vacancies, save_stats
)
from processing import preprocess_vacancies, preprocess_stats


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_path(value):
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


def read_csv_safe(path):
    path = Path(path)

    if not path.exists():
        return pd.DataFrame()

    # sep=None позволяет pandas определить разделитель.
    # Если автоматическое определение не сработало, пробуем
    # стандартные варианты вручную.
    try:
        return pd.read_csv(
            path, sep=None, engine="python",
            encoding="utf-8-sig", on_bad_lines="warn"
        )
    except Exception:
        for sep in (";", ",", "\t"):
            try:
                return pd.read_csv(
                    path, sep=sep, encoding="utf-8-sig",
                    on_bad_lines="warn"
                )
            except Exception:
                pass

    raise ValueError(f"Не удалось прочитать CSV: {path}")


def run_command(command, parser_name, db_path, run_id):
    if not command:
        return True, "Команда запуска не настроена"

    if not isinstance(command, list):
        raise ValueError(
            f"{parser_name}: команда должна быть списком аргументов"
        )

    log_event(
        db_path, "INFO", "orchestrator",
        f"Запуск команды: {command}", run_id
    )

    start = time.perf_counter()

    try:
        result = subprocess.run(
            command,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=1800,
            check=False
        )

        elapsed = round(time.perf_counter() - start, 2)

        if result.stdout:
            log_event(
                db_path, "INFO", parser_name,
                result.stdout[-5000:], run_id
            )

        if result.stderr:
            log_event(
                db_path,
                "ERROR" if result.returncode else "WARNING",
                parser_name, result.stderr[-5000:], run_id
            )

        if result.returncode != 0:
            message = (
                f"Код завершения: {result.returncode}; "
                f"время: {elapsed} с"
            )
            log_event(db_path, "ERROR", parser_name, message, run_id)
            return False, message

        return True, f"Команда выполнена за {elapsed} с"

    except subprocess.TimeoutExpired:
        message = "Превышено время ожидания запуска парсера"
        log_event(db_path, "ERROR", parser_name, message, run_id)
        return False, message

    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        log_event(db_path, "ERROR", parser_name, message, run_id)
        return False, message


def import_parser_files(parser_name, vacancies_path,
                        stats_path, db_path, run_id):
    vacancy_df = read_csv_safe(vacancies_path)
    stats_df = read_csv_safe(stats_path)

    records = preprocess_vacancies(vacancy_df, parser_name)
    stats = preprocess_stats(stats_df)

    saved = save_vacancies(db_path, records)
    save_stats(db_path, parser_name, stats.to_dict("records"), run_id)

    log_event(
        db_path, "INFO", "preprocessing",
        f"Обработано вакансий: {len(records)}; "
        f"обработано строк статистики: {len(stats)}",
        run_id
    )

    return saved, len(records), len(stats)


def run_parser(parser_name):
    config = load_config()
    db_path = resolve_path(config["database_path"])
    init_db(db_path)

    run_id = create_run(db_path, parser_name)
    start = time.perf_counter()

    try:
        prefix = "csharp" if parser_name == "C#" else "python"
        command = config.get(f"{prefix}_command", [])

        ok, message = run_command(
            command, parser_name, db_path, run_id
        )

        if not ok:
            finish_run(db_path, run_id, "Ошибка", message, 0)
            return {
                "ok": False, "message": message, "saved": 0
            }

        vacancies_path = resolve_path(
            config[f"{prefix}_csv"]
        )
        stats_path = resolve_path(
            config[f"{prefix}_stats_csv"]
        )

        saved, processed, stats_count = import_parser_files(
            parser_name, vacancies_path, stats_path,
            db_path, run_id
        )

        elapsed = round(time.perf_counter() - start, 2)
        message = (
            f"{message}; обработано строк вакансий: {processed}; "
            f"строк статистики: {stats_count}; "
            f"время общего процесса: {elapsed} с"
        )

        finish_run(db_path, run_id, "Успешно", message, saved)
        log_event(db_path, "INFO", "orchestrator", message, run_id)

        return {"ok": True, "message": message, "saved": saved}

    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        finish_run(db_path, run_id, "Ошибка", message, 0)
        log_event(db_path, "ERROR", "orchestrator", message, run_id)
        return {"ok": False, "message": message, "saved": 0}


def import_existing_csv(parser_name):
    """Импортирует уже сформированные CSV без запуска парсера."""
    config = load_config()
    db_path = resolve_path(config["database_path"])
    init_db(db_path)

    run_id = create_run(db_path, f"Импорт {parser_name}")

    try:
        prefix = "csharp" if parser_name == "C#" else "python"
        saved, processed, stats_count = import_parser_files(
            parser_name,
            resolve_path(config[f"{prefix}_csv"]),
            resolve_path(config[f"{prefix}_stats_csv"]),
            db_path, run_id
        )

        message = (
            f"Импорт завершён. Обработано вакансий: {processed}; "
            f"строк статистики: {stats_count}"
        )
        finish_run(db_path, run_id, "Успешно", message, saved)
        log_event(db_path, "INFO", "orchestrator", message, run_id)

        return {"ok": True, "message": message, "saved": saved}

    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        finish_run(db_path, run_id, "Ошибка", message, 0)
        log_event(db_path, "ERROR", "orchestrator", message, run_id)
        return {"ok": False, "message": message, "saved": 0}
