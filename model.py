"""Read-only SQLite adapter and explicit input contract. Python 3.10+."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
import sqlite3

DB = Path(__file__).resolve().parent / 'data' / 'freshman_term1_2026_2027.sqlite'
COMPONENTS = {'\u8bb2\u6f14':'LEC','\u6307\u5bfc\u6559\u5b66':'TUT','\u76d1\u7763':'SUP','\u5b9e\u9a8c':'LAB'}  # Original SIS component labels.

@dataclass(frozen=True)
class Meeting:
    weekday: int
    start: int
    end: int
    first: date
    last: date
    rooms: tuple = ()
    teachers: tuple = ()

@dataclass(frozen=True)
class Section:
    course: str
    code: str
    component: str
    meetings: tuple
    teachers: tuple

@dataclass
class Preferences:
    early: float | None = None
    weekdays: dict = field(default_factory=dict)
    teachers: dict = field(default_factory=dict)  # course -> {exact teacher name: rating}
    ban_early: bool = False
    banned_days: tuple = ()
    blocked: tuple = ()  # (weekday, start minute, end minute)
    allow_missing_components: bool = False

@dataclass
class Catalog:
    courses: dict
    sections: dict
    required: dict
    warnings: list


def minutes(value):
    h,m = map(int,value.split(':'))
    if not (0 <= h <= 23 and 0 <= m < 60):
        raise ValueError(f'Invalid time: {value}')
    return h*60+m


def dates(m):
    d=m.first+timedelta(days=(m.weekday-1-m.first.weekday())%7)
    while d<=m.last:
        yield d
        d+=timedelta(days=7)


def load_catalog(path=DB):
    con=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    con.row_factory=sqlite3.Row
    try:
        courses={r['code']:dict(r) for r in con.execute('SELECT * FROM courses')}
        required={code:set() for code in courses}
        for r in con.execute('SELECT * FROM course_components'):
            if r['requirement']=='\u5fc5\u9700':
                required[r['course_code']].add(COMPONENTS.get(r['component'],r['component']))
        sections={code:[] for code in courses}
        warnings=[]
        terms={r[0] for r in con.execute('SELECT DISTINCT term FROM sections')}
        if len(terms)>1:
            raise ValueError('The database contains multiple semesters. Provide data for a single semester.')
        for s in con.execute('SELECT * FROM sections ORDER BY course_code,section_code'):
            merged={}
            for r in con.execute('SELECT m.*,d.weekday FROM meetings m JOIN meeting_days d ON d.meeting_id=m.id WHERE m.section_id=?',(s['id'],)):
                try:
                    start,end=minutes(r['start_time']),minutes(r['end_time'])
                    first,last=date.fromisoformat(r['start_date']),date.fromisoformat(r['end_date'])
                    if start>=end or first>last: raise ValueError('Time or date range is reversed')
                except (TypeError,ValueError) as exc:
                    raise ValueError(f"{s['course_code']} {s['section_code']} Invalid time data: {exc}") from exc
                teachers={x[0] for x in con.execute('SELECT i.name FROM instructors i JOIN meeting_instructors mi ON mi.instructor_id=i.id WHERE mi.meeting_id=? AND i.is_placeholder=0',(r['id'],))}
                key=(r['weekday'],start,end,first,last)
                roomset,teachset=merged.setdefault(key,(set(),set()))
                if r['room']: roomset.add(r['room'])
                teachset.update(teachers)
            meetings=tuple(Meeting(*key,tuple(sorted(rooms)),tuple(sorted(teachers))) for key,(rooms,teachers) in merged.items())
            if not meetings or not any(list(dates(m)) for m in meetings):
                raise ValueError(f"{s['course_code']} {s['section_code']} No valid meeting schedule")
            teachers=tuple(sorted({t for m in meetings for t in m.teachers}))
            sections[s['course_code']].append(Section(s['course_code'],s['section_code'],s['component'],meetings,teachers))
            if any(len(m.rooms)>1 for m in meetings):
                warnings.append(f"{s['course_code']} {s['section_code']} Multiple rooms are listed for the same period. Records are merged into one meeting and all rooms are displayed; verify the original schedule.")
        for code,items in sections.items():
            if len({s.code for s in items})!=len(items): raise ValueError(f'{code} Section code is not unique')
            offered={s.component for s in items}
            if not required[code]: required[code]=offered
            missing=required[code]-offered
            if missing: warnings.append(f'{code} Missing sections for required components: {", ".join(sorted(missing))}')
        return Catalog(courses,sections,required,warnings)
    finally:
        con.close()


def validate_request(cat,codes,p):
    errors=[]
    if not codes: return ['Select courses.']
    if len(set(codes))!=len(codes): errors.append('Duplicate course codes.')
    for code in codes:
        if code not in cat.courses: errors.append(f'Unknown course: {code}')
    if errors: return errors
    credits=sum(float(cat.courses[c]['credits']) for c in codes)
    if not 12<=credits<=18: errors.append(f'Total credits {credits:g}, must be between 12 and 18.')
    values=([p.early] if p.early is not None else [])+list(p.weekdays.values())
    for code,ratings in p.teachers.items():
        if code not in codes: errors.append(f'Instructor preferences refer to an unselected course: {code}')
        names={t for s in cat.sections.get(code,[]) for t in s.teachers}
        for name,v in ratings.items():
            if name not in names: errors.append(f'{code} Instructor not found: {name}')
            values.append(v)
    if any(not isinstance(v,(float,int)) or not 0<=v<=5 for v in values): errors.append('Preference ratings must be 0–5.')
    if any(d not in range(1,8) for d in list(p.weekdays)+list(p.banned_days)): errors.append('Weekday must be 1–7.')
    for d,a,b in p.blocked:
        if d not in range(1,8) or not 0<=a<b<=1440: errors.append('Invalid blocked-time interval.')
    return errors
