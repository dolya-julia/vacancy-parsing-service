
from orchestrator import load_config, resolve_path
from database import connect
from processing import normalize_city


def update_regions(db_path):
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, region FROM vacancies"
        ).fetchall()

        changes = []

        for vacancy_id, old_region in rows:
            old_region = old_region or ""
            new_region = normalize_city(old_region)

            if new_region != old_region:
                changes.append((new_region, vacancy_id))

        conn.executemany(
            "UPDATE vacancies SET region = ? WHERE id = ?",
            changes
        )

    print(f"Обновлено записей: {len(changes)}")


if __name__ == "__main__":
    config = load_config()
    db_path = resolve_path(config["database_path"])
    update_regions(db_path)
