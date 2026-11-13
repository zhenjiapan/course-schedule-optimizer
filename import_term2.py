"""Import SIS-verified 2026-27 Term 2 offerings into the copied database."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3

DB = Path(__file__).parent / 'data' / 'term1_2026_2027.sqlite'
TERM = '2026-27 Term 2'
FIRST, LAST = '2027-01-11', '2027-05-14'
RAW_DATES = '01/11/2027 - 05/14/2027'
COURSES = {
 'MAT1002': ('微积分（二）', 3, '理工学院', 'Students must take MAT1001 or MAT1010 or MAT1011 first. Students who have taken MAT1012 cannot take this course.', '本课程是微积分（一）之延续，将覆盖级数与多元微积分。本课强调对微积分的直观和概念性的理解，培养学生的计算能力和应用微积分解决数学与实际问题的意识和能力。', 'Medium of Instruction: English', ('讲演','指导教学'), 50),
 'STA2001': ('概率及统计（一）', 3, '数据科学学院', 'Prerequisite: MAT1001 or MAT1011 or MAT1003 or MAT1010 Exclusion: ECO2121 or STA2003 or STA2001H or ECO2121H', '本课程的目的是学习概率统计的基本概念。主题包括初等概率论，随机变量，概率分布，数学期望，条件分布，独立性，相关性，一些使用广泛的单变量和双变量随机分布，随机变量变换，抽样分布，动差生成函数，大数定律和中心极限定理。', 'Medium of Instruction: English', ('讲演','指导教学'), 10),
 'ENG1002': ('学术英语（一）', 3, '人文社科学院', 'Pre-requisite: ENG1001/ENG1001T/ENG1001K/ENG1001M', '学术英语(一)是两门学术英语课程中的第一门，面向除语言专业、临床医学专业、及音乐学院学生之外的所有本科生开放，课程将继续培养学生的英语听说读写能力。学生将从ENG1001课程中学习的个人表达性文章转向学习更加复杂的第三人称文章，包括因果论文和议论文。课程将继续提高学生的语法、标点、拼写和词汇知识，同时也会关注更为复杂的知识点，包括内段衔接、段落之间和段落内观点之间的衔接、细节的运用、引用和示例、学术研究以及逻辑和信息逻辑应用。课程还将提高学生英语阅读和听力理解能力、口语能力和学习能力。', 'Medium of Instruction: English', ('讲演',), 62),
 'PED1214': ('蛙泳', 1, '人文社科学院', '1. Students who have taken PED1002 and PED2005 cannot take this course. 2. Students can only choose one course from the PED12XX series. 3. Students cannot choose the same sports item.', '体育与健康是香港中文大学（深圳）的核心课程之一。它由两部分组成，即：(i) 体育；(ii) 适能与健康。蛙泳是适能与健康模块中的课程之一。蛙泳是一种对称的游泳方式，以其独特的节奏感而闻名，虽然入门相对简单，但要达到精通的水平却颇具挑战性。本课程将融入体适能理论的相关内容，包括身体成分等，同时结合运动学原理和水上安全技能进行教学。学生将掌握基本的水中技术动作，规范标准的蛙泳泳姿，提升水中生存技能。此外，课程还将注重培养学生的水中自我保护意识和终身锻炼的习惯。', 'Medium of Instruction: Chinese & English', ('讲演',), 3),
}
ENG = '''MW 1:30PM 108;MW 3:30PM 108;TT 1:30PM 108;TT 3:30PM 108;MW 1:30PM 110;MW 3:30PM 110;TT 1:30PM 110;TT 3:30PM 110;MW 8:30AM 108;MW 10:30AM 108;TT 8:30AM 108;TT 10:30AM 108;MW 3:30PM 109;TT 1:30PM 109;TT 3:30PM 109;MW 8:30AM 110;MW 10:30AM 110;TT 8:30AM 110;TT 10:30AM 110;MW 1:30PM 111;MW 3:30PM 111;TT 1:30PM 111;TT 3:30PM 111;MW 8:30AM 111;MW 10:30AM 111;TT 8:30AM 111;TT 10:30AM 111;MW 1:30PM 113;MW 3:30PM 113;TT 1:30PM 113;TT 3:30PM 113;MW 8:30AM 113;MW 10:30AM 113;TT 8:30AM 113;TT 10:30AM 113;MW 1:30PM 114;MW 3:30PM 114;TT 1:30PM 310;TT 3:30PM 310;MW 1:30PM 115;MW 3:30PM 115;TT 1:30PM 115;TT 3:30PM 115;MW 8:30AM 114;MW 10:30AM 114;TT 8:30AM 107;TT 10:30AM 114;MW 1:30PM 202;MW 3:30PM 202;TT 1:30PM 202;MW 8:30AM 115;MW 10:30AM 115;TT 8:30AM 115;TT 10:30AM 115;MW 8:30AM 201;MW 10:30AM 201;TT 8:30AM 201;TT 10:30AM 201;MW 1:30PM 201;TT 1:30PM 201;TT 3:30PM 201;MW 10:30AM 202'''.split(';')

def stamp(value):
    return datetime.strptime(value, '%I:%M%p')

def add_section(cur, source, code, section, number, days, start, end, room):
    component = 'TUT' if section.startswith('T') else 'LEC'
    label = f'{section}-{component} ({number})'
    sid = cur.execute('INSERT INTO sections(course_code,term,section_code,component,class_number,session,label_raw,source_id) VALUES(?,?,?,?,?,?,?,?)', (code, TERM, section, component, str(number), '1', label, source)).lastrowid
    raw_days = ''.join('星期'+'一二三四五六日'[d-1] for d in days)
    mid = cur.execute('INSERT INTO meetings(section_id,sequence,days_raw,start_time,end_time,room,start_date,end_date,start_time_raw,end_time_raw,dates_raw,instructors_raw) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (sid,1,raw_days,stamp(start).strftime('%H:%M'),stamp(end).strftime('%H:%M'),room,FIRST,LAST,start,end,RAW_DATES,'员工')).lastrowid
    for day in days: cur.execute('INSERT INTO meeting_days VALUES(?,?)',(mid,day))
    cur.execute('INSERT INTO meeting_instructors VALUES(?,(SELECT id FROM instructors WHERE name=?))',(mid,'员工'))

def main():
    con = sqlite3.connect(DB)
    con.execute('PRAGMA foreign_keys=ON')
    with con:
        for code, (name,credits,group,prereq,description,attr,components,count) in COURSES.items():
            if con.execute('SELECT 1 FROM sections WHERE course_code=? AND term=?',(code,TERM)).fetchone():
                raise RuntimeError(f'{code} already has Term 2 sections')
            raw = f'SIS verified: {code} {name}; {TERM}; {count} sections; {RAW_DATES}; all instructors shown as 员工. AIE1901 has no Term 2 option in SIS.'
            cur=con.execute('INSERT INTO sources(course_code,term,collected_at,source_url,archive_sha256,expected_sections,raw_course_text) VALUES(?,?,?,?,?,?,?)',(code,TERM,datetime.now(timezone(timedelta(hours=8))).isoformat(),'https://sis.cuhk.edu.cn/',None,count,raw))
            src=cur.lastrowid
            con.execute('INSERT INTO courses VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(code,name,'本科',float(credits),f'{credits:.2f}','已评分','Main Campus',group,group,prereq,description,src))
            con.execute('INSERT INTO course_attributes VALUES(?,?)',(code,attr))
            for comp in components: con.execute('INSERT INTO course_components VALUES(?,?,?)',(code,comp,'必需'))
            if code=='MAT1002':
                lectures=[('TT','10:30AM','12:20PM','Teaching Complex A402'),('TT','3:30PM','5:20PM','Teaching Complex A402'),('TT','3:30PM','5:20PM','Teaching B Bldg 103'),('MW','10:30AM','12:20PM','Teaching B Bldg 201'),('MW','10:30AM','12:20PM','Teaching Complex A401'),('MW','3:30PM','5:20PM','Teaching B Bldg 103'),('TT','1:30PM','3:20PM','Teaching B Bldg 103'),('MW','8:30AM','10:20AM','Teaching B Bldg 103'),('MW','1:30PM','3:20PM','Teaching Complex A402'),('TT','8:30AM','10:20AM','Teaching B Bldg 103')]
                for n,(days,a,b,room) in enumerate(lectures,1): add_section(con,src,code,f'L{n:02}',1356+n, (1,3) if days=='MW' else (2,4),a,b,room)
                times=[('6:00PM','7:20PM'),('6:30PM','7:50PM'),('7:00PM','8:20PM'),('7:30PM','8:50PM')]
                blocks=[(2,['Teaching A Bldg 308','Teaching A Bldg 317','Teaching A Bldg 318','Teaching A Bldg 308']),(3,['Teaching A Bldg 308','Teaching A Bldg 317','Teaching A Bldg 318','Teaching A Bldg 308']),(5,['Teaching A Bldg 308','Teaching A Bldg 317','Teaching A Bldg 318','Teaching A Bldg 308']),(1,['Teaching A Bldg 308','Teaching A Bldg 317','Teaching A Bldg 318','Teaching A Bldg 308']),(4,['Teaching A Bldg 308','Teaching A Bldg 317','Teaching A Bldg 318','Teaching A Bldg 308']),(2,['Teaching A Bldg 316','Teaching B Bldg 301','Teaching B Bldg 303','Teaching A Bldg 316']),(4,['Teaching A Bldg 316','Teaching B Bldg 301','Teaching B Bldg 303','Teaching A Bldg 316']),(2,['Teaching A Bldg 304','Teaching B Bldg 305','Teaching B Bldg 306','Teaching A Bldg 304']),(5,['Teaching A Bldg 316','Teaching B Bldg 301','Teaching A Bldg 304','Teaching B Bldg 303']),(2,['Teaching B Bldg 307','Teaching B Bldg 311','Teaching B Bldg 312','Teaching C Bldg 108'])]
                for n in range(1,41):
                    day,rooms=blocks[(n-1)//4];a,b=times[(n-1)%4]
                    add_section(con,src,code,f'T{n:02}',1366+n,(day,),a,b,rooms[(n-1)%4])
            elif code=='STA2001':
                rows=[('L01',1539,(2,4),'8:30AM','9:50AM','Teaching B Bldg 201'),('L02',1540,(1,3),'10:30AM','11:50AM','Teaching B Bldg 202'),('L03',1541,(1,3),'8:30AM','9:50AM','Administration Bldg E101'),('T01',1542,(4,),'8:00PM','8:50PM','Teaching C Bldg 206'),('T02',1543,(2,),'8:00PM','8:50PM','Teaching C Bldg 206'),('T03',1544,(3,),'6:00PM','6:50PM','Teaching C Bldg 206'),('T04',1545,(4,),'7:00PM','7:50PM','Teaching C Bldg 206'),('T05',1546,(5,),'6:00PM','6:50PM','Teaching C Bldg 206'),('T06',1547,(2,),'7:00PM','7:50PM','Teaching C Bldg 206'),('T07',1548,(3,),'8:00PM','8:50PM','Teaching C Bldg 206')]
                for sec,num,days,a,b,room in rows:add_section(con,src,code,sec,num,days,a,b,room)
            elif code=='ENG1002':
                ends={'1:30PM':'2:50PM','3:30PM':'4:50PM','8:30AM':'9:50AM','10:30AM':'11:50AM'}
                for n,row in enumerate(ENG,1):
                    days,a,room=row.strip().split()
                    add_section(con,src,code,f'L{n:02}',1047+n,(1,3) if days=='MW' else (2,4),a,ends[a],f'Teaching D Bldg {room}')
            else:
                for n,(a,b) in enumerate([('1:30PM','3:20PM'),('3:30PM','5:20PM'),('6:00PM','7:50PM')],1):
                    add_section(con,src,code,f'L{n:02}',2439+n,(3,),a,b,'Swimming Pool, Sports Hall')
            actual=con.execute('SELECT count(*) FROM sections WHERE course_code=? AND term=?',(code,TERM)).fetchone()[0]
            assert actual==count,(code,actual,count)
            con.execute('INSERT INTO collection_runs VALUES(?,?,?,?,?,?)',
                        (code, TERM, '2026-11-13', 'SIS 浏览目录 > 课程详细信息 > 显示时段 > 查看全部', count,
                         '讲师显示为员工；未记录开放/关闭状态或推断讲演与指导教学绑定'))
    assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    print('Imported',[(c,con.execute('SELECT count(*) FROM sections WHERE course_code=? AND term=?',(c,TERM)).fetchone()[0]) for c in COURSES])
    con.close()

if __name__=='__main__':main()
