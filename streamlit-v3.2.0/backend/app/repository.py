from collections import defaultdict
from sqlalchemy import text
from .optimization.model import Catalog, Meeting, Section, COMPONENTS, dates

def load_catalog(connection, term, code=None, *, occurrence_overrides=True):
    def query(sql, args=()):
        for i, value in enumerate(args):
            sql = sql.replace("?", f":p{i}", 1)
        return connection.execute(text(sql), {f"p{i}": value for i, value in enumerate(args)}).mappings()
    section_sql = "SELECT * FROM sections WHERE term=?"
    params = (term,)
    if code is not None:
        section_sql += " AND course_code=?"
        params += (code,)
    section_rows = list(query(section_sql + " ORDER BY course_code,section_code", params))
    offered_codes = {r["course_code"] for r in section_rows}
    courses = {r["code"]: dict(r) for r in query("SELECT * FROM courses") if r["code"] in offered_codes}
    meetings_by_section = defaultdict(list)
    teachers_by_meeting = defaultdict(set)
    for row in query("SELECT m.*,d.weekday FROM meetings m LEFT JOIN meeting_days d ON d.meeting_id=m.id "
                     f"WHERE m.section_id IN (SELECT id FROM ({section_sql}) AS selected) ORDER BY m.id,d.weekday", params):
        meetings_by_section[row["section_id"]].append(row)
    for row in query("SELECT mi.meeting_id,i.name FROM instructors i JOIN meeting_instructors mi ON i.id=mi.instructor_id "
                     "JOIN meetings m ON m.id=mi.meeting_id WHERE i.is_placeholder=0 "
                     f"AND m.section_id IN (SELECT id FROM ({section_sql}) AS selected)", params):
        teachers_by_meeting[row["meeting_id"]].add(row["name"])
    overrides = {row["meeting_id"]: tuple(row["occurrences"]) for row in query(
        "SELECT o.meeting_id,o.occurrences FROM meeting_occurrence_overrides o "
        "JOIN meetings m ON m.id=o.meeting_id "
        f"WHERE m.section_id IN (SELECT id FROM ({section_sql}) AS selected)", params)} if occurrence_overrides else {}
    raw_components = defaultdict(set)
    for row in section_rows:
        raw_components[row["course_code"]].add(row["component"])
    required={code:set() for code in courses}
    for r in query('SELECT * FROM course_components'):
        if r['course_code'] in required and r['requirement']=='\u5fc5\u9700':
            required[r['course_code']].add(COMPONENTS.get(r['component'],r['component']))
    sections={code:[] for code in courses}
    warnings=[]
    # CHI1000 is Lecture-only; the full SIS snapshot retains a stale Tutorial requirement.
    if 'CHI1000' in required:
        required['CHI1000'].discard('TUT')
    for s in section_rows:
        merged={}
        incomplete=False
        expanded = set()
        for r in meetings_by_section[s['id']]:
            actual = overrides.get(r['id'])
            if any(r[k] is None for k in ('start_time','end_time')) or (
                actual is None and any(r[k] is None for k in ('start_date','end_date','weekday'))
            ):
                incomplete=True
                continue
            try:
                start,end=r['start_time'].hour*60+r['start_time'].minute, r['end_time'].hour*60+r['end_time'].minute
                first,last=r['start_date'], r['end_date']
                if start >= end or (actual is None and first > last):
                    raise ValueError('Time or date range is reversed')
            except (TypeError,ValueError) as exc:
                raise ValueError(f"{s['course_code']} {s['section_code']} Invalid time data: {exc}") from exc
            teachers=teachers_by_meeting[r['id']]
            if actual is not None:
                if r['id'] in expanded:
                    continue
                expanded.add(r['id'])
                keys = [(d.isoweekday(),start,end,d,d,(d,)) for d in actual]
            else:
                keys = [(r['weekday'],start,end,first,last,None)]
            for key in keys:
                roomset,teachset=merged.setdefault(key,(set(),set()))
                if r['room']:
                    roomset.add(r['room'])
                teachset.update(teachers)
        meetings=tuple(Meeting(*key[:5],tuple(sorted(rooms)),tuple(sorted(teachers)),key[5])
                       for key,(rooms,teachers) in merged.items())
        if incomplete or not meetings or not any(list(dates(m)) for m in meetings):
            warnings.append(f"{s['course_code']} {s['section_code']} Unavailable for planning: meeting dates or times are incomplete. Verify in SIS.")
            continue
        teachers=tuple(sorted({t for m in meetings for t in m.teachers}))
        sections[s['course_code']].append(Section(s['course_code'],s['section_code'],s['component'],meetings,teachers))
        if any(len(m.rooms)>1 for m in meetings):
            warnings.append(f"{s['course_code']} {s['section_code']} Multiple rooms are listed for the same period. Records are merged into one meeting and all rooms are displayed; verify the original schedule.")
    for code,items in sections.items():
        if len({s.code for s in items})!=len(items): raise ValueError(f'{code} Section code is not unique')
        offered={s.component for s in items}
        if not required[code]:
            # Keep component requirements even when all their sections have unknown times.
            required[code]=raw_components[code].copy()
        if code=='CHI1000': required[code].discard('TUT')
        missing=required[code]-offered
        if missing: warnings.append(f'{code} Missing sections for required components: {", ".join(sorted(missing))}')
    bindings={}
    for row in query('SELECT course_code,lecture_section,tutorial_section FROM section_bindings WHERE term=?',(term,)):
        bindings.setdefault((row['course_code'],row['lecture_section']),set()).add(row['tutorial_section'])
    return Catalog(courses,sections,required,warnings,bindings)
