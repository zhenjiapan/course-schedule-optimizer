# Course Database: 2026–27 Term 1

The source is authenticated SIS course-detail and full section-list pages. Initial collection took place on October 25–26, 2026. The table below is the original 34-course baseline, not an inventory of later expansions. Course names remain in their original Chinese form.

| Course code | Course name | Sections |
|---|---|---:|
|ACT2111|财务会计导论|24|
|AIE1001|人工智能编程导论|6|
|AIE1901|人工智能探索（一）|11|
|CEC1000|思想道德与法治|18|
|CHI1000|大学中文|29|
|CHM1001|普通化学|18|
|CHM1011|普通化学荣誉课程|2|
|CSC1001|计算机科学导论：程序设计方法|17|
|CSC1003|计算机科学与Java 程序设计导论|4|
|CSC1005|计算机工程导论：程序设计与应用|10|
|DAI1000|人工智能与数字素养|15|
|ECO2011|微观经济学导论|33|
|ENG1001|基础英语|63|
|MAT1001|微积分（一）|55|
|MAT1011|微积分荣誉课程（一）|7|
|MAT2040|线性代数|15|
|MAT2042|线性代数荣誉课程|3|
|PED1101|羽毛球|4|
|PED1102|把杆训练|2|
|PED1103|篮球|6|
|PED1104|地壶|10|
|PED1105|飞盘|5|
|PED1106|高尔夫|2|
|PED1109|定向越野|2|
|PED1110|匹克球|4|
|PED1113|足球|1|
|PED1116|乒乓球|2|
|PED1117|跆拳道|3|
|PED1118|太极拳|3|
|PED1119|网球|2|
|PED1121|排球|4|
|PED1122|武术散打|4|
|PED1123|瑜伽|2|
|PHY1001|力学|16|

The baseline contains 34 courses, 402 sections, 405 raw meeting records, and 553 weekday associations. A section can contain multiple meetings, and a meeting can occur on multiple weekdays; each record is retained.

## Querying the database

The current query module reads `data/term1_2026_2027.sqlite` relative to its source location. Run the following from the project root.

```bash
python3 query_courses.py
```

```python
from query_courses import get_course, get_schedule, find_by_weekday
course = get_course('MAT1001')
sections = get_schedule('MAT1001')
monday = find_by_weekday(1)
```

A direct standard-library query is also possible:

```python
import sqlite3

with sqlite3.connect('data/term1_2026_2027.sqlite') as conn:
    rows = conn.execute(
        'SELECT section_code, days_raw, start_time, end_time, room '
        'FROM schedule WHERE course_code = ?', ('AIE1001',)
    ).fetchall()
```

With Pandas installed, use `pd.read_sql_query('SELECT * FROM schedule', conn)` for analysis.

## Tables and views

| Table or view | Contents |
| --- | --- |
| `courses` | Course codes, names, academic career, credits, grading basis, campus, offering unit, academic organization, enrollment requirements, and full descriptions |
| `course_components` | Components such as Lecture and Tutorial, with requirement flags |
| `course_attributes` | Course-page attributes such as teaching language |
| `sections` | Course, term, section code, component abbreviation, class number, and session |
| `meetings` | Each meeting, its section ID, and original weekday, time, date, and instructor text |
| `meeting_days` | Weekday associations; Monday = 1 and Sunday = 7 |
| `instructors`, `meeting_instructors` | Instructors and meeting associations, supporting multiple instructors |
| `sources` | Collection timestamps, sources, raw course fields, page-archive checksums, and page section totals |
| `schedule` | Convenient course, section, and meeting query view |
| `course_summary` | Course details and section counts |

Times use 24-hour `HH:MM`; dates use `YYYY-MM-DD`, interpreted in Asia/Shanghai. Original source values are retained in `_raw` fields. TBA-only entries have NULL normalized times or dates while retaining the source text. Optional fields absent from SIS remain NULL; missing requirements are never invented.

The database contains available candidate sections, not personal enrollment records. Unspecified staff entries retain their original source text and are marked `is_placeholder=1` rather than treated as named instructors.

Collection covered course details and section meeting lists. It did not additionally extract `View Course Outline` documents or each class's expanded detail page. The data is a snapshot at collection time.

The original baseline verification checked the target term, agreement between stored section counts and page totals, retention of all raw meetings, SQLite integrity, foreign keys, and validity of normalized date and time intervals.

## Collection and schema history

### October 26, 2026

Added PHY1001, ECO2011, ACT2111, CEC1000, CHM1001, CHM1011, CSC1001, CSC1003, CSC1005, and DAI1000: 10 courses, 157 sections, and 157 meetings. PHY1011 offered only 2025–26 Term 2 in the displayed term list and was excluded. All existing records were retained and checked.

### October 27, 2026

Removed `sections.status` and the corresponding `schedule` view column. The updated database does not include open, closed, or waitlist status. Other course, section, and meeting information was retained. Query results no longer include a `status` field.

### October 30, 2026: initial expansion

The SIS route was Browse Course Catalog → Subject → Course Details → View Class Sections → 2026–27 Term 1 → View All. Undergraduate, graduate, and research courses were included. The first additions were AIE1101 (2 sections), AIE1903 (8), and AIE2001 (4), with full details, components, attributes, descriptions, and meetings. AIE1902 offered only 2025–26 Term 2; ACM1001 and AIE1904 were unscheduled; CEC1001 had no target term. These entries were excluded. This was an intermediate checkpoint, not completion of A–F. Only the original catalog route was used to confirm entries. The original database folder was not writable, so expansion used a separate copy.

### October 30, 2026: A-prefix completion

Checked all course levels under ACM, ACT, AIE, AIR, AIS, AIT, and ART. Saved all sections and meetings for courses offering 2026–27 Term 1. Collection stopped at A at the user's request; B–F had not yet been checked at this checkpoint.

Added 50 courses, 98 sections, 103 raw meetings, and 112 weekday associations. Additions by subject were:

- ACT: 2121, 3011, 3141, 3154, 3161, 3311, 4111, 4131, 4244, 4253, 4262, 4321, 5003, 5005, 6111, 6121, 6151, 6161, 6212, 6242, 6244, 6271, 6290, 6291, 6305, 8003, 8004, 8012.
- AIE: 1101, 1903, 2001, 2040, 3001, 3005, 3905, 6001, 6008, 6016, 8201, 8301, 8401.
- AIR: 5011, 5023, 5050, 5052, 5058, 5059, 5064, 5212, 5213.
- AIS: 5007, 5008, 6002.

Totals at this checkpoint were 87 courses, 514 sections, 523 raw meetings, and 683 weekday associations. A-prefix totals were 56 courses and 153 sections. All sections belonged to `2026-27 Term 1`. The 53 saved A-prefix course archives were represented in the database; ACT2111, AIE1001, and AIE1901 came from the baseline. Unscheduled courses and courses without the target term were excluded. SQLite integrity returned `ok`; foreign-key checks found no errors. No section availability or Lecture/Tutorial binding was inferred.

### October 30, 2026: B-prefix completion

Checked BGE, BIM, BIO, BMA, BME, and BSC across all course levels. BGE4010 was unscheduled; other courses without target-term sections were also excluded.

Added 57 courses, 81 sections, 84 raw meetings, and 97 weekday associations. Course additions by subject: BIM 6, BIO 18, BMA 1, BME 13, and BSC 19. Totals became 144 courses, 595 sections, 607 raw meetings, and 780 weekday associations. All 57 saved course archives were represented. All sections belonged to the target term, integrity and foreign-key checks passed, and availability and section bindings were still not inferred.

### October 31, 2026: C- and D-prefix verification

Checked CBH, CEC, CHI, CHM, CIE, CLC, CLCC, CSC, CSS, DAI, DDA, DME, DMS, and DUM. Saved subject totals were CBH 3, CEC 7, CHI 9, CHM 22, CIE 15, CLC 4, CSC 49, CSS 18, DAI 1, DDA 26, and DMS 1. No target-term courses were confirmed for CLCC, DME, or DUM. Unscheduled entries and entries without target-term sections were excluded.

Added 147 courses, 291 sections, 300 raw meetings, and 363 weekday associations relative to the B checkpoint. Totals became 291 courses, 886 sections, 907 raw meetings, and 1,143 weekday associations. Every section belonged to `2026-27 Term 1`; integrity and foreign-key checks passed. Open, closed, and waitlist status and Lecture/Tutorial bindings were not recorded or inferred.

DDA5002 and DDA5003 had multiple-offering selection links, but SIS did not display confirmable details correctly. Unconfirmed variants were excluded and need later review when SIS recovers. E and F had not yet been checked at this checkpoint.

### November 1, 2026: E-prefix completion

Checked ECE, ECO, EIE, ENB, ENE, ENG, ENL, EPB, ERG, EXFE, EXGA, EXGB, EXGBE, EXGBI, EXGC, EXGD, EXGSCLM, EXME, EXNE, and EXSE across all course levels. Unscheduled courses and entries without target-term sections were excluded.

Added 87 courses, 232 sections, 245 raw meetings, and 337 weekday associations to a copy. Final reported totals were 378 courses, 1,118 sections, 1,152 raw meetings, and 1,480 weekday associations. There were 89 E-prefix courses, including existing ECO2011 and ENG1001: ECE 16, ECO 35, ENB 6, ENE 13, ENG 7, EPB 6, and ERG 6. No target-term sections were confirmed for EIE, ENL, or EX-prefix subjects.

All 87 saved E-prefix course archives were represented with all target-term sections and meetings. Every section belonged to `2026-27 Term 1`; integrity returned `ok` and foreign-key checks passed. Availability status and Lecture/Tutorial bindings were not inferred. The original database was unchanged. F-prefix collection remained incomplete.


### November 8–9, 2026: F- and G-prefix completion

Checked all catalog codes at all course levels for FEMBA, FEX, FIN, FMA, FREN, FRN, FTE, GBI, GEA, GEB, GEC, GED, GER, GERM, GEW, GFH, GFN, GGE, GLB, and GNB. For each target-term offering, the SIS route was Browse Course Catalog → Subject → Course Details → View Class Sections → 2026–27 Term 1 → View Sections → View All. Unscheduled courses and those without the target term were excluded. Earlier statements that F or G remained unchecked describe historical checkpoints.

F-prefix totals: 47 courses, 101 sections, and 105 meetings (FEX 11 courses, FIN 35, FRN 1). G-prefix totals: 64 courses, 249 sections, and 252 meetings (GEA 1, GEB 9, GEC 15, GED 13, GEW 2, GFH 1, GFN 1, GGE 2, GLB 20). GBI, GER, GERM, and GNB had no confirmed target-term offerings. The completed database has **489 courses, 1,468 sections, 1,509 raw meetings, and 1,834 weekday associations**. All stored sections belong to `2026-27 Term 1`; SQLite integrity and foreign-key checks passed. The database excludes enrollment availability and does not infer Lecture/Tutorial bindings.

## Language and data preservation

Documentation, interface labels, comments, and export headers are in English. Chinese course names are preserved. Raw SIS data, including original source fields, is retained without translation to preserve provenance and database compatibility. Source enum matching remains exact.
