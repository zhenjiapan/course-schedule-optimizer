# Course Schedule Optimizer

A Python and Streamlit application for planning CUHK-Shenzhen course schedules under credit requirements, timetable constraints, and personal preferences. The current working version is **v2.0.1**.

## Quick start

Use Python 3.10 or later. Run these commands from the project root:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

The core optimizer and command-line checker use the Python standard library:

```bash
python3 cli.py examples/request.json > result.json
python3 cli.py --check result.json
python3 -m unittest tests.test_optimizer -v
```

Run UI regression checks after installing the dependencies:

```bash
python3 tests/test_ui.py
```

## Features

- Course selection with credit validation and date-aware conflict detection
- Preferences for early classes, weekdays, and instructors
- Backtracking and branch-and-bound search for up to three recommendations
- An independent feasibility checker
- Manual section changes, weekly timetable previews, and CSV/JSON export

## Repository layout

| Path | Purpose |
| --- | --- |
| `app.py` | Streamlit interface |
| `model.py` | Read-only database adapter and input structures |
| `optimizer.py` | Search and preference scoring |
| `checker.py` | Independent schedule validation |
| `timetable.py` | Weekly timetable rendering |
| `cli.py` | Command-line optimization and validation |
| `query_courses.py` | Queries against the full course database |
| `data/` | Current databases |
| `examples/` | Request and reference result JSON files |
| `tests/` | Core and UI regression checks |
| `docs/` | Usage, scoring model, and database documentation |
| `archive/` | Historical v1.0.0 and v2.0.0 versions |

## Data

`data/freshman_term1_2026_2027.sqlite` is the optimizer's default dataset. It contains the existing CHI1000 component correction. `data/term1_2026_2027.sqlite` is the full dataset used by `query_courses.py`. These datasets have different scopes and are not interchangeable without checking their schema and component requirements.

Database content is unchanged by this reorganization. Example outputs are preserved reference files, not newly generated results. The database guide and collection notes in `docs/` document the source history; executable paths now resolve relative to the source file.

## Model and limitations

See [usage and scoring](docs/usage-and-model.md) for the objective, hard constraints, timeout behavior, and manual selection workflow, and [database guide](docs/database-guide.md) for source data details.

An optimal status applies only to the supplied candidate data, constraints, and objective. Timed-out results are not certified optimal. The app does not register courses in the university enrollment system and cannot verify prerequisites or section bindings absent from the data.

## Historical versions

`archive/v1.0.0/` and `archive/v2.0.0/` preserve previous layouts and databases, with English documentation and interface labels. Start the maintained application from the project root. Future changes can be recorded using Git commits and release tags.

Maintained by [Zhenjia Pan](https://github.com/zhenjiapan).

## Language

Documentation and interface text are in English. Original Chinese course names are retained. Raw SIS database data is preserved for source fidelity and exact enum matching. Exported table headers and score breakdown labels are English. See [reorganization notes](docs/reorganization.md) for the language update and validation scope.
