# Reorganization and Language Update

Current version: **v2.0.1**. Historical directories are `archive/v1.0.0/` and `archive/v2.0.0/`. Original version names 1.0, 2.0, and 2.1 map to v1.0.0, v2.0.0, and v2.0.1 respectively.

The current application's source files are at the root; databases, examples, tests, and documentation are grouped separately. Database paths are resolved relative to source files. Duplicate full-database materials were consolidated. macOS metadata, compiled Python caches, and old development-tool records were excluded.

## File mapping

The original database guide had a Chinese filename; `[original database guide]` below identifies it. New filenames are English.

| Original location | New location |
| --- | --- |
| `Course Schedule Optimization_2.0/freshman_term1_2026_2027.sqlite` | `archive/v2.0.0/freshman_term1_2026_2027.sqlite` |
| `Course Schedule Optimization_2.0/requirements.txt` | `archive/v2.0.0/requirements.txt` |
| `Course Schedule Optimization_2.0/query_courses.py` | `archive/v2.0.0/query_courses.py` |
| `Course Schedule Optimization_2.0/optimizer.py` | `archive/v2.0.0/optimizer.py` |
| `Course Schedule Optimization_2.0/timetable.py` | `archive/v2.0.0/timetable.py` |
| `Course Schedule Optimization_2.0/test_optimizer.py` | `archive/v2.0.0/test_optimizer.py` |
| `Course Schedule Optimization_2.0/request.json` | `archive/v2.0.0/request.json` |
| `Course Schedule Optimization_2.0/example_result.json` | `archive/v2.0.0/example_result.json` |
| `Course Schedule Optimization_2.0/test_ui.py` | `archive/v2.0.0/test_ui.py` |
| `Course Schedule Optimization_2.0/checker.py` | `archive/v2.0.0/checker.py` |
| `Course Schedule Optimization_2.0/cli.py` | `archive/v2.0.0/cli.py` |
| `Course Schedule Optimization_2.0/[original database guide]` | `archive/v2.0.0/database-guide.md` |
| `Course Schedule Optimization_2.0/README.md` | `archive/v2.0.0/README.md` |
| `Course Schedule Optimization_2.0/app.py` | `archive/v2.0.0/app.py` |
| `Course Schedule Optimization_2.0/model.py` | `archive/v2.0.0/model.py` |
| `Courses Database/query_courses.py` | `query_courses.py (duplicate of current-version content; merged)` |
| `Courses Database/term1_2026_2027.sqlite` | `data/term1_2026_2027.sqlite (duplicate of current-version content; merged)` |
| `Courses Database/[original database guide]` | `docs/database-guide.md (duplicate of current-version content; merged)` |
| `Courses Database/REDME.rtf` | `docs/database-notes.md (duplicate of current-version content; merged)` |
| `Course Schedule Optimization_1.0/freshman_term1_2026_2027.sqlite` | `archive/v1.0.0/freshman_term1_2026_2027.sqlite` |
| `Course Schedule Optimization_1.0/test_app.py` | `archive/v1.0.0/test_app.py` |
| `Course Schedule Optimization_1.0/requirements.txt` | `archive/v1.0.0/requirements.txt` |
| `Course Schedule Optimization_1.0/query_courses.py` | `archive/v1.0.0/query_courses.py` |
| `Course Schedule Optimization_1.0/check_timetable.py` | `archive/v1.0.0/check_timetable.py` |
| `Course Schedule Optimization_1.0/app.py` | `archive/v1.0.0/app.py` |
| `Course Schedule Optimization_1.0/_timetable_preview.html` | `archive/v1.0.0/_timetable_preview.html` |
| `Course Schedule Optimization_2.1/freshman_term1_2026_2027.sqlite` | `data/freshman_term1_2026_2027.sqlite` |
| `Course Schedule Optimization_2.1/requirements.txt` | `requirements.txt` |
| `Course Schedule Optimization_2.1/query_courses.py` | `query_courses.py` |
| `Course Schedule Optimization_2.1/optimizer.py` | `optimizer.py` |
| `Course Schedule Optimization_2.1/timetable.py` | `timetable.py` |
| `Course Schedule Optimization_2.1/test_optimizer.py` | `tests/test_optimizer.py` |
| `Course Schedule Optimization_2.1/request.json` | `examples/request.json` |
| `Course Schedule Optimization_2.1/example_result.json` | `examples/example_result.json` |
| `Course Schedule Optimization_2.1/test_ui.py` | `tests/test_ui.py` |
| `Course Schedule Optimization_2.1/checker.py` | `checker.py` |
| `Course Schedule Optimization_2.1/cli.py` | `cli.py` |
| `Course Schedule Optimization_2.1/term1_2026_2027.sqlite` | `data/term1_2026_2027.sqlite` |
| `Course Schedule Optimization_2.1/[original database guide]` | `docs/database-guide.md` |
| `Course Schedule Optimization_2.1/REDME.rtf` | `docs/database-notes.md` |
| `Course Schedule Optimization_2.1/README.md` | `docs/usage-and-model.md` |
| `Course Schedule Optimization_2.1/app.py` | `app.py` |
| `Course Schedule Optimization_2.1/model.py` | `model.py` |

## English-language update

Documentation, comments, docstrings, interface labels, validation messages, exported table headers, and reference output labels were converted to English. Course names remain in Chinese. Raw SIS database contents were preserved, including source records and schema enum values. Enum comparisons still use the original exact values. Example result files remain historical references rather than new search runs.

The original RTF database notes were converted into `database-notes.md`. Chinese explanatory development comments were replaced by English module/function documentation where appropriate. Archived versions now include English documentation and UI labels; they are no longer byte-identical source snapshots. Their scheduling logic and database contents are retained.

The scheduling objective and constraints were not changed. Consumers of CSV/table rows or score breakdowns should use the new English labels. Existing JSON structural fields such as `courses`, `selections`, and `score` are unchanged.

## Validation

- All 14 current-version core tests passed.
- All 14 archived v2.0.0 core tests passed.
- Current CLI plan generation and independent validation passed; all three generated plans passed validation.
- The same request retained the original selected sections and scores after translation.
- Full-database queries ran successfully.
- Every Python file parsed successfully; JSON files and local Markdown links were checked.
- A text scan found Chinese only in course-name table cells; all filenames are English.
- All bundled database files are byte-identical to the original upload.
- Streamlit was not installed in this environment, so UI regression tests and browser visual checks were not rerun.
