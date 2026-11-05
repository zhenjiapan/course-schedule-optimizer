# Course Schedule Optimizer v2.0.0

The application plans course schedules from the bundled semester snapshot. All sections participate regardless of enrollment availability. In the optimizer dataset, CHI1000 requires a Lecture only; its Tutorial requirement was removed following the original project confirmation.

## Setup and launch

Use Python 3.10 or later. Run from the project root, using the same virtual environment as your editor:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

`requirements.txt` lists dependencies and is not an executable Python script.

## Workflow

Select courses totaling 12–18 credits, configure preferences and blocked periods, and generate up to three recommendations. The archived UI has a separate manual section-validation area. Select a teaching week and export CSV or JSON. Changing inputs invalidates old results.

The command-line optimizer requires only the Python standard library:

```bash
python3 cli.py request.json > result.json
python3 cli.py --check result.json
python3 -m unittest test_optimizer -v
```

`request.json` is editable. Each blocked interval is `[weekday, start_minute, end_minute]`. For example, `[[3,1080,1260]]` blocks Wednesdays from 18:00 to 21:00. `example_result.json` is a preserved reference output, not a newly generated result.

## Modules

| File | Responsibility |
| --- | --- |
| `model.py` | Read-only database access, input structures, and merging duplicate room records for the same meeting |
| `optimizer.py` | Backtracking and branch-and-bound search for the top three plans |
| `checker.py` | Independent date-by-date validation of components, credits, overlaps, and blocked periods |
| `app.py` | Streamlit workflow and manual section editing |
| `timetable.py` | Date-aware weekly filtering and exact start/end boundary rendering |
| `query_courses.py` | Queries against the full course database without enrollment status fields |
| `cli.py` | Command-line optimization and validation |
| `test_optimizer.py` | Core regression tests |
| `test_ui.py` | Streamlit UI regression checks |

## Scoring

Early-class, weekday, and instructor categories have equal weight. Unconfigured categories are excluded. If no preferences are configured, every feasible plan scores 50; the search returns up to three plans in deterministic traversal order.

For early classes or a rated weekday, let `r` be a preference rating from 0 to 5. Let `N` be the plan's actual number of matching meetings over the semester. Let `M` be the sum, over required components, of the maximum matching-meeting count among each component's candidate sections after hard filtering. `M` is fixed for a request and does not depend on the selected plan. Set `q = N/M`, or `q = 0` if `M = 0`.

```text
Item score = 20 * ((5 - r) * (1 - q) + r * q)
```

A rating of 0 favors fewer occurrences; 5 favors more. The weekday category averages the rated weekdays. Use a whole-day block to require a completely free day. Because conflicts can prevent simultaneous attainment of all component maxima, 100 points may be unattainable. Scores from different requests are not directly comparable.

Instructor scoring includes only components with at least one rated candidate instructor. For a section with multiple instructors, their ratings are averaged. Unrated or unknown instructors receive 2.5. Included component scores are averaged and multiplied by 20. Instructor preferences are entered per course and mapped to its components. Category weights are not configurable.

A course meeting twice per week counts twice per teaching week. Actual meeting dates determine semester counts. Multiple rooms for the same section, weekday, time, and date interval are merged into a single meeting; all rooms are displayed.

## Correctness and limitations

- A completed search certifies the top-k scores only under the supplied candidates, constraints, and objective. Any k tied plans may be returned.
- A timeout with solutions returns the best plans found so far, without an optimality guarantee.
- A timeout without solutions does not establish infeasibility.
- Missing required components prevent automatic planning. The Python API has an explicit `allow_missing_components` override; the UI does not silently waive missing data.
- Each run reads the database again. Replacement data must preserve the expected schema and the CHI1000 component correction. The optimizer uses `freshman_term1_2026_2027.sqlite`; the archived query helper uses the bundled freshman database.
- The data does not provide Lecture/Tutorial bindings or personal prerequisite records. These rules cannot be verified. A generated plan does not enroll the user in SIS.
- Adjacent meetings with the same end/start time do not conflict. There is no travel buffer or separate holiday, rescheduling, or exceptional teaching-week data; weekday and date intervals determine meetings.
- Multiple rooms are displayed together with a warning; the app does not guess the correct room.
- This directory is the archived v2.0.0 version; launch the maintained v2.0.1 application from the project root.

## Validation history

The original development notes report 14 core tests, including 25 randomized preference comparisons against exhaustive top-three scoring, early-class and weekday preference reversal, instructor ratings, hard constraints, dates, timeout distinctions, room deduplication, and the real dataset. Original UI checks covered automatic planning, manual editing, invalidation after input changes, infeasibility, and credit errors.

The originally reported environment was Python 3.13, Streamlit 1.66.1, and Pandas 3.1.0. Dependency lower bounds were not tested individually. These are historical claims, not a statement that those versions are installed in the current validation environment. See the project-root documentation for current validation notes.

