# Changelog

## v2.0.1

### Features

- A shared weekly timetable, validation report, and export area for recommended and manually edited schedules.
- Section labels showing instructors and meeting times.
- Persistent manual selections and invalidation of recommendations when inputs change.

### Data compatibility

- The app, CLI, optimizer, and query helper use the full `term1_2026_2027.sqlite` snapshot containing 387 courses.
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
