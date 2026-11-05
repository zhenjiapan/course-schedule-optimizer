# Database Collection Notes

This Markdown file replaces the original RTF notes. See [database guide](database-guide.md) for the complete collection history and schema.

| Date | Recorded work |
| --- | --- |
| 2026-10-25 | Created the 2026–27 Term 1 freshman SQLite dataset with MAT1001, AIE1001, ENG1001, and CHI1000. |
| 2026-10-26 | Added MAT1011, MAT2040, MAT2042, AIE1901, and PED11-prefix courses. Further requested additions were PHY1001, PHY1011, ECO2011, ACT2111, CEC1000, CHM1001, CHM1011, CSC1001, CSC1003, CSC1005, and DAI1000. PHY1011 was requested but not imported because the target term was unavailable. |
| 2026-10-27 | Removed enrollment status fields and updated the query views. |
| 2026-10-30, initial checkpoint | Added AIE1101 (2 sections), AIE1903 (8), and AIE2001 (4). Totals were 37 courses and 416 sections. ACM1001 and AIE1904 were unscheduled; AIE1902 and CEC1001 lacked the target term. The original location was not writable, so expansion used a copy. |
| 2026-10-30, A complete | Checked ACM, ACT, AIE, AIR, AIS, AIT, and ART at all course levels. Added 50 courses and 98 sections. Totals: 87 courses, 514 sections, 523 meetings, and 683 weekday associations. All saved A-prefix pages were represented; integrity and foreign-key checks passed. B–F remained unchecked at this checkpoint. |
| 2026-10-30, B complete | Checked BGE, BIM, BIO, BMA, BME, and BSC. Added 57 courses, 81 sections, 84 meetings, and 97 weekday associations. Totals: 144 courses, 595 sections, 607 meetings, and 780 weekday associations. Integrity and foreign-key checks passed; C–F remained unchecked. |
| 2026-10-31, C/D complete | Added 147 courses, 291 sections, 300 meetings, and 363 weekday associations. Totals: 291 courses and 886 sections. Integrity passed. Unconfirmed DDA5002/DDA5003 multiple-offering variants remained pending; E/F remained unchecked. |
| 2026-11-01, E complete | Added 87 courses, 232 sections, 245 meetings, and 337 weekday associations to a copy. Totals: 378 courses, 1,118 sections, 1,152 meetings, and 1,480 weekday associations. E-prefix totals: 89 courses (ECE 16, ECO 35, ENB 6, ENE 13, ENG 7, EPB 6, ERG 6), including existing ECO2011 and ENG1001. All 87 saved E-prefix course archives were represented. Integrity and foreign-key checks passed. F remained unchecked. |

Only confirmed target-term offerings were imported. The data is a collection-time snapshot; it does not include live enrollment availability or inferred section bindings.
