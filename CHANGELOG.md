# Changelog

## v3.0.0 — November 13, 2026

- Archived the previous working version and its databases in `archive/v2.0.1/`.
- Added semester selection for 2026-27 Terms 1 and 2. The default remains Term 1 for existing command-line requests.
- Added verified Term 2 course and section data to the existing multi-term SQLite database. The historical database filename remains unchanged.
- Updated the spring course guide, database documentation, and example queries for the new term.

### Semester selector and further Term 2 courses

- Added all SIS-listed Term 2 sections for MAT1002 (50), STA2001 (10), ENG1002 (62), and PED1214 (3) to a copy of the existing database. Total Term 2 sections: 213.
- Checked AIE1901 in SIS; its term selector only lists Term 1, so no Term 2 sections were added.
- Added a Term 1 / Term 2 selector to the Streamlit app, semester-specific course choices, and a `term` field for CLI requests and JSON exports.
- Appended verified course details and all 125 new sections to the user's original seven-page spring course guide PDF. The original seven pages are preserved.

### Term 2 section verification

- Verified all displayed sections and meeting times in SIS for CSC3001 (3), DDA2001 (11), CSC3200 (4), PHY1001 (16), GFN1000 (42), and CEC2000 (12). Added 88 Term 2 sections to a new database copy.
- Updated the spring course guide PDF and documented that the bundled database contains both terms. The app and CLI continue to default to Term 1; the query helper accepts an optional term filter.
- New totals: 494 courses, 1,564 sections, 1,605 meetings, 1,944 weekday associations. The original repository was not changed.

## H-prefix data refresh — November 9, 2026

- Checked all HKSL, HSS, and HST catalog codes in SIS. Added HSS1004, HSS1006, HSS1010, and HSS1011 with all eight target-term sections and meetings. HKSL had no target-term offering and HST entries were unscheduled.
- Default database now contains 493 courses, 1,476 sections, 1,517 meetings, and 1,846 weekday associations. Integrity and foreign-key checks passed.

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
