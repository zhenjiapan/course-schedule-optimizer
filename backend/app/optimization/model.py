"""Framework-independent optimization domain. Python 3.10+."""
from dataclasses import dataclass, field
from datetime import date, timedelta

COMPONENTS = {"\u8bb2\u6f14": "LEC", "\u6307\u5bfc\u6559\u5b66": "TUT", "\u76d1\u7763": "SUP", "\u5b9e\u9a8c": "LAB", "\u5b9e\u9a8c\u5ba4": "LAB", "\u5b9e\u4e60": "PRA", "\u8bba\u9898\u7814\u7a76": "THE", "\u7814\u8ba8\u4f1a": "SEM", "\u7814\u7a76": "RSC", "\u81ea\u4e3b\u5b66\u4e60": "IND"}  # Original SIS labels mapped to section codes.

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
    bindings: dict = field(default_factory=dict)


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


def validate_request(cat,codes,p):
    errors=[]
    if not codes: return ['Select courses.']
    if len(set(codes))!=len(codes): errors.append('Duplicate course codes.')
    for code in codes:
        if code not in cat.courses: errors.append(f'Unknown course: {code}')
    if errors: return errors
    credits=sum(float(cat.courses[c]['credits']) for c in codes)
    if credits < 12: errors.append(f'Total credits {credits:g}, must be at least 12.')
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
