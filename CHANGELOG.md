# Changelog

## Data refresh — November 9, 2026

- Replaced the default 2026–27 Term 1 database with the completed A–G SIS snapshot: 489 courses, 1,468 sections, 1,509 meetings, and 1,834 weekday associations.
- Finished checking all F- and G-prefix subjects at every course level using the SIS course catalog and full section view. Courses without target-term sections were excluded.
- Preserved the schema, original course details, and the earlier 34-course reference database. SQLite integrity and foreign-key checks passed. Enrollment availability and Lecture/Tutorial bindings are not stored.

## v2.0.1

### Features

- A shared weekly timetable, validation report, and export area for recommended and manually edited schedules.
- Section labels showing instructors and meeting times.
- Persistent manual selections and invalidation of recommendations when inputs change.

### Data compatibility

- The app, CLI, optimizer, and query helper use the full `term1_2026_2027.sqlite` snapshot containing 387 courses at the v2.0.1 checkpoint (now refreshed to 489 courses).
- The read-only adapter preserves the CHI1000 Lecture-only correction without editing the database.
- Expanded SIS component labels map to matching section codes.
- Sections with incomplete meeting dates or times are excluded with warnings; required components remain enforced.

### Repository

- Current source files at the root, with dedicated data, examples, tests, and documentation directories.
- Historical versions retained in `archive/v1.0.0/` and `archive/v2.0.0/`.
- English documentation and interface text; original Chinese course names and raw SIS data retained.
- A linked live demo, cloud deployment settings, and a core-test workflow for Python 3.10 and 3.13.
- macOS metadata removed and ignored.

### Validation and limitations

- The 16-test core suite passed locally on Python 3.12 before this update.
- Automated core checks run in GitHub Actions. Their results are available on the Actions page.
- Streamlit UI regression tests and browser visual acceptance were not rerun during this repository documentation update.
- The data is a static snapshot. Prerequisites and Lecture/Tutorial bindings absent from the source data cannot be verified. The application does not perform enrollment in SIS.

## v2.0.0

Historical preference-based optimizer with backtracking, branch-and-bound search, an independent checker, and a Streamlit interface.

## v1.0.0

Historical manual course-selection and hard-constraint validation application.
