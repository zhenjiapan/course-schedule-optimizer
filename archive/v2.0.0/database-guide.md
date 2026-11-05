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

The archived query module and `freshman_term1_2026_2027.sqlite` remain in this directory. Run commands from this archived directory.

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

with sqlite3.connect('freshman_term1_2026_2027.sqlite') as conn:
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

## v2.0.0 component correction

On October 27, 2026, following the original project confirmation, the bundled optimizer database's required Tutorial record for CHI1000 was removed. CHI1000 requires Lecture only. Other course and meeting data was unchanged.
