"""Adapt SQLite result types to the shared course repository."""
import json
from datetime import date, time
from pathlib import Path

from sqlalchemy import create_engine, inspect

from backend.app.repository import load_catalog


class SQLiteCatalogConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, parameters):
        return SQLiteRows(self.connection.execute(statement, parameters).mappings())

    
class SQLiteRows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        for source in self.rows:
            row = dict(source)
            for key, parser in (("start_date", date), ("end_date", date),
                                ("start_time", time), ("end_time", time)):
                if isinstance(row.get(key), str):
                    row[key] = parser.fromisoformat(row[key])
            if isinstance(row.get("occurrences"), str):
                row["occurrences"] = [date.fromisoformat(value) for value in json.loads(row["occurrences"])]
            yield row


def catalog_from_snapshot(path: Path, term: str):
    engine = create_engine(f"sqlite:///{path.resolve().as_uri()}?mode=ro&uri=true")
    try:
        with engine.connect() as connection:
            return load_catalog(
                SQLiteCatalogConnection(connection), term,
                occurrence_overrides=inspect(connection).has_table("meeting_occurrence_overrides"),
            )
    finally:
        engine.dispose()
