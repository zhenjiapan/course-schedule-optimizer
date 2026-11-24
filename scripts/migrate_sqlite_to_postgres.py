"""Import and verify a local SIS snapshot in one database transaction."""
import argparse
from datetime import date, time
from pathlib import Path
import sqlite3
import sys

from sqlalchemy import MetaData, Table, select, text
from sqlalchemy.dialects.postgresql import insert

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.db import engine

TABLES = ("sources", "courses", "course_components", "course_attributes", "sections",
          "meetings", "meeting_days", "instructors", "meeting_instructors", "collection_runs")

def migrate(path):
    path = path.resolve(strict=True)
    if not path.is_relative_to(ROOT / "private"):
        raise ValueError("Place the copied snapshot inside private/ first")
    metadata = MetaData()
    from contextlib import closing
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as source, engine.begin() as target:
        source.row_factory = sqlite3.Row
        if source.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Source contains broken foreign keys")
        target.execute(text("SELECT pg_advisory_xact_lock(42399731)"))
        has_bindings = source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='section_bindings'"
        ).fetchone()
        for name in TABLES + (("section_bindings",) if has_bindings else ()):
            rows = [dict(row) for row in source.execute(f"SELECT * FROM {name}")]
            if name == "meetings":
                for row in rows:
                    for key, parse in (("start_date", date.fromisoformat), ("end_date", date.fromisoformat),
                                       ("start_time", time.fromisoformat), ("end_time", time.fromisoformat)):
                        if row[key] is not None:
                            row[key] = parse(row[key])
            table = Table(name, metadata, autoload_with=target)
            keys = [column.name for column in table.primary_key]
            existing = {tuple(row[k] for k in keys): dict(row) for row in target.execute(select(table)).mappings()}
            for row in rows:
                pk = tuple(row[k] for k in keys)
                if pk in existing and existing[pk] != row:
                    raise ValueError(f"{name}: existing row differs at primary key {pk}")
            if rows:
                target.execute(insert(table).on_conflict_do_nothing(index_elements=keys), rows)
            imported = {tuple(row[k] for k in keys): dict(row) for row in target.execute(select(table)).mappings()}
            if any(imported.get(tuple(row[k] for k in keys)) != row for row in rows):
                raise ValueError(f"{name}: verification failed")
            print(f"{name}: verified {len(rows)} source rows")
    print("Import committed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    migrate(parser.parse_args().snapshot)
