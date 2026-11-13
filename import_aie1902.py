"""Import the SIS-verified 2026-27 Term 2 AIE1902 offering once."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

DB = Path(__file__).parent / 'data' / 'term1_2026_2027.sqlite'
TERM = '2026-27 Term 2'
CODE = 'AIE1902'
DATES = '01/11/2027 - 05/14/2027'
DESCRIPTION = ('本课程系列（AIE1901-AIE1904）以"项目实践"为核心教学模式，通过阶梯式项目设计满足学生在不同学习阶段对人工智能技术的需求，旨在培养学生对AI的兴趣及使用AI工具解决具体问题的能力。'
               '在14周系统化学习中，学生将在导师指导下初步了解人工智能技术的基本原理和工具使用，初步掌握人工智能技术在多个领域的应用场景和可以赋能解决的实际问题。'
               '课程深度融合前沿技术案例与科研实践课题，着力培养学生的跨学科思维与创新能力。针对编程零基础学生，课程特别设置"零代码AI开发"相关的项目，'
               '帮助学生在无需编写代码的前提下，掌握AI工具的实践应用，使所有学生都能将人工智能技术有效融入日常学习与研究实践。AIE1902是该系列课程的第二门。')
# section number, weekday (Mon=1), start, end, all rooms shown by SIS
SECTIONS = [
    (2478, 4, '3:30PM', '5:20PM', ['Teaching C Bldg 203']),
    (2479, 2, '8:30AM', '10:20AM', ['Teaching Complex C501']),
    (2480, 1, '8:30AM', '10:20AM', ['Teaching Complex C501']),
    (2481, 3, '8:30AM', '10:20AM', ['Teaching D Bldg 202']),
    (2482, 2, '8:30AM', '10:20AM', ['Teaching D Bldg 303']),
    (2483, 5, '8:30AM', '10:20AM', ['Teaching A Bldg 313']),
    (2484, 2, '10:30AM', '12:20PM', ['Teaching C Bldg 301', 'Teaching C Bldg 311']),
    (2485, 3, '1:30PM', '3:20PM', ['Teaching C Bldg 112']),
    (2486, 2, '10:30AM', '12:20PM', ['Teaching A Bldg 314']),
    (2487, 2, '3:30PM', '5:20PM', ['Teaching D Bldg 211']),
    (2488, 5, '8:30AM', '10:20AM', ['Teaching C Bldg 109']),
]

def normalized_time(raw):
    return datetime.strptime(raw, '%I:%M%p').strftime('%H:%M')

def main():
    con = sqlite3.connect(DB)
    con.execute('PRAGMA foreign_keys=ON')
    with con:
        if con.execute('SELECT 1 FROM courses WHERE code=?', (CODE,)).fetchone():
            raise RuntimeError('AIE1902 already exists; check before importing again')
        if not con.execute('SELECT id FROM instructors WHERE name=?', ('员工',)).fetchone():
            raise RuntimeError('Placeholder instructor 员工 missing')
        source = con.execute('INSERT INTO sources(course_code,term,collected_at,source_url,archive_sha256,expected_sections,raw_course_text) VALUES(?,?,?,?,?,?,?)',
            (CODE, TERM, datetime.now(timezone(timedelta(hours=8))).isoformat(), 'https://sis.cuhk.edu.cn/', None, 11,
             'SIS 浏览目录; 2026-27 Term 2; 11 Sxx-SUP sections, 12 meeting rows; 01/11/2027 - 05/14/2027; S07 has two room rows; instructor 员工.')).lastrowid
        con.execute('INSERT INTO courses VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (CODE, '人工智能探索（二）', '本科', 2.0, '2.00', '已评分', 'Main Campus', '人工智能学院', '人工智能学院', 'Prerequisite: AIE1901', DESCRIPTION, source))
        con.execute('INSERT INTO course_attributes VALUES(?,?)', (CODE, 'Medium of Instruction: English'))
        con.execute('INSERT INTO course_components VALUES(?,?,?)', (CODE, '监督', '必需'))
        for i, (number, day, start, end, rooms) in enumerate(SECTIONS, 1):
            label = f'S{i:02}-SUP ({number})'
            sid = con.execute('INSERT INTO sections(course_code,term,section_code,component,class_number,session,label_raw,source_id) VALUES(?,?,?,?,?,?,?,?)',
                (CODE, TERM, f'S{i:02}', 'SUP', str(number), '1', label, source)).lastrowid
            for sequence, room in enumerate(rooms, 1):
                mid = con.execute('INSERT INTO meetings(section_id,sequence,days_raw,start_time,end_time,room,start_date,end_date,start_time_raw,end_time_raw,dates_raw,instructors_raw) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                    (sid, sequence, '星期' + '一二三四五六日'[day-1], normalized_time(start), normalized_time(end), room,
                     '2027-01-11', '2027-05-14', start, end, DATES, '员工')).lastrowid
                con.execute('INSERT INTO meeting_days VALUES(?,?)', (mid, day))
                con.execute('INSERT INTO meeting_instructors VALUES(?,(SELECT id FROM instructors WHERE name=?))', (mid, '员工'))
        con.execute('INSERT INTO collection_runs VALUES(?,?,?,?,?,?)',
            (CODE, TERM, '2026-11-13', 'SIS 浏览目录 > 课程详细信息 > 显示时段 > 查看全部', 11,
             '11 个 SUP 区段，S07 同时段显示两个教室并分别保存；未保存开放/关闭状态'))
    assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert con.execute('SELECT count(*) FROM sections WHERE course_code=? AND term=?', (CODE, TERM)).fetchone()[0] == 11
    assert con.execute('SELECT count(*) FROM meetings m JOIN sections s ON s.id=m.section_id WHERE s.course_code=? AND s.term=?', (CODE, TERM)).fetchone()[0] == 12
    print('Imported AIE1902: 11 sections, 12 meeting rows')
    con.close()

if __name__ == '__main__':
    main()
