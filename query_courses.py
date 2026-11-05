"""Read-only course database queries and scheduling helpers. Run this module to print sample queries."""
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent / 'data' / 'term1_2026_2027.sqlite'

def connect():
    conn = sqlite3.connect(DB_PATH.as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn

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

if __name__ == '__main__':
    with connect() as conn:
        for row in conn.execute('SELECT * FROM course_summary ORDER BY code'):
            print(dict(row))
    print('\nMAT1001 First three sections: ')
    for row in get_schedule('MAT1001')[:3]:
        print(row)
    print('\nNumber of Monday meeting records: ', len(find_by_weekday(1)))
    print('Pinjia HE meeting periods: ', find_by_instructor('Pinjia HE'))
