"""Export only the catalog fields consumed by the public planner."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.main import catalog

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()
terms = {}
for term in ("2026-27 Term 1", "2026-27 Term 2"):
    cat = catalog(term)
    terms[term] = {
        code: {
            **cat.courses[code],
            "required": sorted(cat.required[code]),
            "sections": [asdict(section) for section in cat.sections[code]],
            "warnings": [warning for warning in cat.warnings if warning.startswith(code + " ")],
            "bindings": {lecture: sorted(tutorials) for (c, lecture), tutorials in cat.bindings.items() if c == code},
        }
        for code in sorted(cat.courses)
    }
assert "FIN2010" in terms["2026-27 Term 2"]
args.output.write_text(json.dumps(terms, default=str, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
