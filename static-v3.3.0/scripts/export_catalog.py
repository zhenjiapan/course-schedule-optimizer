"""Extract the planner's public-facing catalog fields into a separate SQLite file."""
import argparse
import sqlite3
from pathlib import Path

COLUMNS = {
    "courses": "code,name,credits",
    "sections": "id,term,course_code,section_code,component",
    "meetings": "id,section_id,start_time,end_time,start_date,end_date,room",
    "meeting_days": "meeting_id,weekday",
    "instructors": "id,name,is_placeholder",
    "meeting_instructors": "meeting_id,instructor_id",
    "course_components": "course_code,component,requirement",
    "section_bindings": "term,course_code,lecture_section,tutorial_section",
}
INDEXES = {
    "courses": "code", "sections": "term,course_code", "meetings": "section_id",
    "meeting_days": "meeting_id", "instructors": "id",
    "meeting_instructors": "meeting_id", "section_bindings": "term",
}


def export(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb"):
        pass
    try:
        with sqlite3.connect(output, uri=True) as db:
            db.execute("ATTACH DATABASE ? AS source", (source.resolve().as_uri() + "?mode=ro",))
            for name, columns in COLUMNS.items():
                db.execute(f"CREATE TABLE main.{name} AS SELECT {columns} FROM source.{name}")
            db.execute("CREATE TABLE meeting_occurrence_overrides (meeting_id INTEGER PRIMARY KEY, occurrences TEXT NOT NULL)")
            if db.execute("SELECT 1 FROM source.sqlite_master WHERE type='table' AND name='meeting_occurrence_overrides'").fetchone():
                db.execute("INSERT INTO main.meeting_occurrence_overrides SELECT meeting_id, occurrences FROM source.meeting_occurrence_overrides")
            for name, columns in INDEXES.items():
                db.execute(f"CREATE INDEX main.idx_{name} ON {name} ({columns})")
            if not db.execute("SELECT 1 FROM main.sections WHERE course_code='FIN2010' AND term='2026-27 Term 2'").fetchone():
                raise ValueError("The snapshot must contain FIN2010 in 2026–27 Term 2")
    except BaseException:
        output.unlink()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export(args.source, args.output)
