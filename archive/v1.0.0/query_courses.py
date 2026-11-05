"""Read-only course database queries and scheduling helpers. Run this module to print sample queries."""
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).with_name('freshman_term1_2026_2027.sqlite')


WEEKDAY_LABELS = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'}


_COMPONENT_ORDER = ['LEC', 'TUT', 'SUP', 'LAB', 'SEM', 'REC', 'DIS', 'PRJ', 'STU', 'IND', 'FLD', 'CLN', 'EXM', 'FIN']

COMPONENT_LABEL = {
    'LEC': 'Lecture', 'TUT': 'Tutorial', 'SUP': 'Supervision', 'LAB': 'Laboratory', 'SEM': 'Seminar',
    'REC': 'Recitation', 'DIS': 'Discussion', 'PRJ': 'Project', 'STU': 'Independent study', 'IND': 'Individual instruction',
    'FLD': 'Fieldwork', 'CLN': 'Clinical', 'EXM': 'Examination', 'FIN': 'Final examination',
}


def connect():
    conn = sqlite3.connect(DB_PATH.as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
def get_course(code):
    """Return course details, or None if the course code is unknown."""
    with connect() as conn:
        row = conn.execute('SELECT * FROM courses WHERE code = ?', (code,)).fetchone()
        return dict(row) if row else None


def get_schedule(code):
    """Return all available sections for a course, not a personal enrolled timetable."""
    with connect() as conn:
        return [dict(row) for row in conn.execute(
            'SELECT * FROM schedule WHERE course_code = ? ORDER BY section_code, meeting_id',
            (code,))]


def find_by_weekday(weekday):
    """Return meetings on a weekday; Monday is 1 and Sunday is 7."""
    if weekday not in range(1, 8):
        raise ValueError('weekday must be 1 to 7')
    with connect() as conn:
        return [dict(row) for row in conn.execute('''
            SELECT s.* FROM schedule s JOIN meeting_days d ON d.meeting_id = s.meeting_id
            WHERE d.weekday = ? ORDER BY s.start_time, s.course_code, s.section_code
        ''', (weekday,))]


def find_by_instructor(name):
    """Find meetings by the exact instructor name stored in the database."""
    with connect() as conn:
        return [dict(row) for row in conn.execute('''
            SELECT s.* FROM schedule s
            JOIN meeting_instructors mi ON mi.meeting_id = s.meeting_id
            JOIN instructors i ON i.id = mi.instructor_id
            WHERE i.name = ? ORDER BY s.course_code, s.section_code
        ''', (name,))]


def check_conflict(course_a, section_a, course_b, section_b):
    """Return whether two sections overlap, together with conflict details."""
    times_a = _section_meetings(course_a, section_a)
    times_b = _section_meetings(course_b, section_b)

    conflicts = []
    for t_a in times_a:
        for t_b in times_b:
            if t_a['weekday'] == t_b['weekday']:
                
                if t_a['start_time'] < t_b['end_time'] and t_b['start_time'] < t_a['end_time']:
                    conflicts.append({
                        'weekday': t_a['weekday'],
                        'time_a': f"{t_a['start_time']} - {t_a['end_time']}",
                        'time_b': f"{t_b['start_time']} - {t_b['end_time']}",
                    })

    is_conflict = len(conflicts) > 0
    return is_conflict, conflicts


def get_all_course_codes():
    """Return sorted course codes for course selection."""
    with connect() as conn:
        rows = conn.execute('SELECT code FROM courses ORDER BY code').fetchall()
        return [row['code'] for row in rows]


# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
def _section_meetings(course_code, section_code):
    """Return meeting weekday, start time, end time, and room for a section."""
    with connect() as conn:
        rows = conn.execute('''
            SELECT d.weekday            AS weekday,
                   m.start_time         AS start_time,
                   m.end_time           AS end_time,
                   m.room               AS room
            FROM sections s
            JOIN meetings m      ON m.section_id = s.id
            JOIN meeting_days d  ON d.meeting_id = m.id
            WHERE s.course_code = ? AND s.section_code = ?
            ORDER BY d.weekday, m.start_time
        ''', (course_code, section_code)).fetchall()
        return [dict(r) for r in rows]


def get_course_components(course_code):
    """Return distinct course components in a stable display order."""
    with connect() as conn:
        rows = conn.execute(
            'SELECT DISTINCT component FROM sections WHERE course_code = ?',
            (course_code,)).fetchall()
    comps = [r['component'] for r in rows]
    comps.sort(key=lambda c: _COMPONENT_ORDER.index(c) if c in _COMPONENT_ORDER else len(_COMPONENT_ORDER))
    return comps


def get_sections_by_component(course_code, component):
    """Return section codes, enrollment statuses, and class numbers for a course component."""
    with connect() as conn:
        rows = conn.execute('''
            SELECT section_code, status, class_number
            FROM sections
            WHERE course_code = ? AND component = ?
            ORDER BY section_code
        ''', (course_code, component)).fetchall()
        return [dict(r) for r in rows]


def get_course_credits(course_code):
    """Return course credits, or 0.0 for an unknown course."""
    with connect() as conn:
        row = conn.execute('SELECT credits FROM courses WHERE code = ?', (course_code,)).fetchone()
        return float(row['credits']) if row else 0.0


def total_credits(course_codes):
    """Sum credits once per distinct course; selecting multiple components does not duplicate credits."""
    total = 0.0
    seen = set()
    with connect() as conn:
        for code in course_codes:
            if code in seen:
                continue
            seen.add(code)
            row = conn.execute('SELECT credits FROM courses WHERE code = ?', (code,)).fetchone()
            if row:
                total += float(row['credits'])
    return total


def check_conflicts_multi(selections):
    """Return pairwise time conflicts for (course_code, section_code) selections. Weekdays are numbered 1 to 7."""
    conflicts = []
    n = len(selections)
    for i in range(n):
        ca, sa = selections[i]
        times_a = _section_meetings(ca, sa)
        for j in range(i + 1, n):
            cb, sb = selections[j]
            times_b = _section_meetings(cb, sb)
            for ta in times_a:
                for tb in times_b:
                    if ta['weekday'] == tb['weekday']:
                        if ta['start_time'] < tb['end_time'] and tb['start_time'] < ta['end_time']:
                            conflicts.append({
                                'course_a': ca, 'section_a': sa,
                                'course_b': cb, 'section_b': sb,
                                'weekday': ta['weekday'],
                                'time_a': f"{ta['start_time']} - {ta['end_time']}",
                                'time_b': f"{tb['start_time']} - {tb['end_time']}",
                            })
    return conflicts


def build_weekly_schedule(selections):
    """Build timetable rows sorted by weekday and start time for the selected sections."""
    rows = []
    with connect() as conn:
        for code, sec in selections:
            name_row = conn.execute('SELECT name FROM courses WHERE code = ?', (code,)).fetchone()
            course_name = name_row['name'] if name_row else code
            comps = conn.execute('''
                SELECT s.component   AS component,
                       d.weekday     AS weekday,
                       m.start_time  AS start_time,
                       m.end_time    AS end_time,
                       m.room        AS room
                FROM sections s
                JOIN meetings m     ON m.section_id = s.id
                JOIN meeting_days d ON d.meeting_id = m.id
                WHERE s.course_code = ? AND s.section_code = ?
                ORDER BY d.weekday, m.start_time
            ''', (code, sec)).fetchall()
            for r in comps:
                rows.append({
                    'weekday': r['weekday'],
                    'Weekday': WEEKDAY_LABELS.get(r['weekday'], str(r['weekday'])),
                    'Start': r['start_time'],
                    'End': r['end_time'],
                    'Course code': code,
                    'Course name': course_name,
                    'Section': sec,
                    'Type': r['component'],
                    'Room': r['room'] or '',
                })
    rows.sort(key=lambda x: (x['weekday'], x['Start']))
    return rows


if __name__ == '__main__':
    with connect() as conn:
        for row in conn.execute('SELECT * FROM course_summary ORDER BY code'):
            print(dict(row))
    print('\nMAT1001 First three sections: ')
    for row in get_schedule('MAT1001')[:3]:
        print(row)
    print('\nNumber of Monday meeting records: ', len(find_by_weekday(1)))
    print('Pinjia HE meeting periods: ', find_by_instructor('Pinjia HE'))

    print("\n--- Testing time-conflict detection ---")
    test_course_1 = 'MAT1001'
    test_section_1 = 'L01'
    test_course_2 = 'CSC1001'
    test_section_2 = 'L01'

    has_conflict, details = check_conflict(test_course_1, test_section_1, test_course_2, test_section_2)
    if has_conflict:
        print(f"⚠️ Conflict detected！{test_course_1} and {test_course_2} Conflict: ")
        for c in details:
            print(f"Weekday{c['weekday']} Conflict: {c['time_a']} and {c['time_b']}")
    else:
        print(f"✅ {test_course_1} ({test_section_1}) and {test_course_2} ({test_section_2}) No time conflict, Both can be selected！")

    print("\n--- Multi-course helper self-check ---")
    print('MAT1001 components:', get_course_components('MAT1001'))
    print('MAT1001 TUT Section count:', len(get_sections_by_component('MAT1001', 'TUT')))
    print('Credit total [MAT1001, AIE1001, MAT1001]:', total_credits(['MAT1001', 'AIE1001', 'MAT1001']))
    print('Example timetable rows (MAT1001 L01):', build_weekly_schedule([('MAT1001', 'L01')]))
