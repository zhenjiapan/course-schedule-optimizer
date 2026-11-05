"""App.py."""
import math
import sys
from datetime import date, timedelta
from html import escape
from pathlib import Path

import streamlit as st
import pandas as pd

# ---------------------------------------------------------------------------

#


#


# ---------------------------------------------------------------------------
_APP_DIR = str(Path(__file__).resolve().parent)
if _APP_DIR in sys.path:
    sys.path.remove(_APP_DIR)
sys.path.insert(0, _APP_DIR)
sys.modules.pop('query_courses', None)   

try:
    from query_courses import (
        get_all_course_codes,
        get_course_components,
        get_sections_by_component,
        total_credits,
        check_conflicts_multi,
        build_weekly_schedule,
        COMPONENT_LABEL,
    )
except ImportError as exc:
    st.error(
        f'Import query_courses Failed: {exc}\n\n'
        f'Please verify query_courses.py and app.py are in the same directory, and query_courses.py already includes '
        f'get_course_components / total_credits / check_conflicts_multi / build_weekly_schedule and related functions.'
    )
    st.stop()


REQUIRED_FIXED = ['AIE1001', 'AIE1901', 'MAT1001', 'ENG1001', 'CHI1000']

REQUIRED_PED_PREFIX = 'PED11'
CREDIT_MIN, CREDIT_MAX = 12, 18


def comp_label(comp: str) -> str:
    """Return the English display label for a component code."""
    return COMPONENT_LABEL.get(comp, comp)


WEEKDAY_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTH_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
TYPE_EN = {
    'LEC': 'Lecture', 'TUT': 'Tutorial', 'SUP': 'Supervision', 'LAB': 'Laboratory',
    'SEM': 'Seminar', 'REC': 'Recitation', 'DIS': 'Discussion', 'PRJ': 'Project',
    'STU': 'Studio', 'IND': 'Independent Study', 'FLD': 'Fieldwork', 'CLN': 'Clinic',
}

TIMETABLE_CSS = """
<style>
.tt-wrap { width: 100%; overflow-x: auto; }
table.tt { border-collapse: collapse; width: 100%; table-layout: fixed;
           font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; }
table.tt th, table.tt td { border: 1px solid #B4C6E7; }
table.tt th.tt-head { background: #D9D9D9; color: #1F3864; font-weight: 700;
                      font-size: 13px; padding: 6px 2px; text-align: center; line-height: 1.3; }
table.tt th.tt-head-time { width: 52px; background: #D9D9D9; color: #1F3864;
                           font-size: 12px; font-weight: 700; text-align: center; }
table.tt td.tt-time { background: #FFFFFF; color: #1F3864; font-size: 12px;
                      text-align: center; height: 36px; }
table.tt td.tt-slot { background: #FFFCDB; height: 36px; }
table.tt td.tt-class { background: #C3D69B; color: #1F3864; font-size: 12px; font-weight: 700;
                       text-align: center; vertical-align: middle; line-height: 1.35;
                       padding: 4px 2px; }
table.tt td.tt-class .tt-code { font-size: 13px; }
</style>
"""


def _to_min(t: str) -> int:
    """Convert an HH:MM time string to minutes after midnight."""
    h, m = str(t).split(':')
    return int(h) * 60 + int(m)


def _hhmm(mins: int) -> str:
    """Format minutes after midnight as HH:MM."""
    return f'{mins // 60:02d}:{mins % 60:02d}'


def build_timetable_html(rows, week_monday: date) -> str:
    """Render a weekly grid with duration-based row spans and an English date header."""
    if not rows:
        return '<p style="color:#888;">No classes to display.</p>'

    
    starts = [_to_min(r['Start']) for r in rows]
    ends = [_to_min(r['End']) for r in rows]
    grid_start = (min(starts) // 30) * 30          
    grid_end = ((max(ends) // 30) + 1) * 30        
    n_rows = max(1, math.ceil((grid_end - grid_start) / 60))

    
    placed = {}    
    occupied = set()   

    for r in sorted(rows, key=lambda x: (x['weekday'], _to_min(x['Start']))):
        st_min, et_min = _to_min(r['Start']), _to_min(r['End'])
        row = (st_min - grid_start) // 60
        span = max(1, math.ceil((et_min - st_min) / 60))   
        wd = r['weekday']

        
        while row < n_rows and ((row, wd) in placed or (row, wd) in occupied):
            row += 1
        if row >= n_rows:
            continue
        span = min(span, n_rows - row)

        type_en = TYPE_EN.get(r['Type'], r['Type'])
        
        code = escape(str(r['Course code']))
        section = escape(str(r['Section']))
        time_range = escape('{} - {}'.format(r['Start'], r['End']))
        room = escape(str(r['Room']))
        placed[(row, wd)] = (
            '<td class="tt-class" rowspan="%d">' % span
            + '<div class="tt-code">%s - %s</div>' % (code, section)
            + '<div>%s</div>' % escape(type_en)
            + '<div>%s</div>' % time_range
            + '<div>%s</div>' % room
            + '</td>'
        )
        for k in range(1, span):
            occupied.add((row + k, wd))

    
    head = ['<th class="tt-head-time">Time</th>']
    for i in range(7):
        d = week_monday + timedelta(days=i)
        head.append(f'<th class="tt-head">{WEEKDAY_EN[i]}<br>{MONTH_EN[d.month - 1]} {d.day}</th>')

    
    body = []
    for row in range(n_rows):
        t = grid_start + row * 60
        cells = [f'<td class="tt-time">{_hhmm(t)}</td>']
        for wd in range(1, 8):
            if (row, wd) in occupied:
                continue                       
            if (row, wd) in placed:
                cells.append(placed[(row, wd)])
            else:
                cells.append('<td class="tt-slot"></td>')
        body.append('<tr>' + ''.join(cells) + '</tr>')

    return (
        TIMETABLE_CSS
        + '<div class="tt-wrap"><table class="tt"><thead><tr>'
        + ''.join(head)
        + '</tr></thead><tbody>'
        + ''.join(body)
        + '</tbody></table></div>'
    )


def render_html(html: str):
    """Display timetable HTML using the supported Streamlit rendering API."""
    if hasattr(st, 'html'):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


st.set_page_config(page_title='Intelligent Course Planner', page_icon='📅', layout='wide')
st.title('📅 Intelligent Course Planner')
st.caption('Hard-constraint validation: Required courses · Credits 12–18 · Time conflict')


try:
    all_courses = get_all_course_codes()
except Exception as e:
    st.error(f'Failed to read the database, Ensure this file and freshman_term1_2026_2027.sqlite in the same directory.Error messages: {e}')
    st.stop()


with st.sidebar:
    st.header('① Select courses')
    selected_courses = st.multiselect('Select courses to take (Multiple selections allowed)', all_courses, key='courses')

    selections = []   
    missing = []      

    if selected_courses:
        st.header('② Select sections')
        st.caption('Each component of every course (Lecture / Tutorial / Supervision) requires one section; Closed sections are also listed and labeled.')
        for code in selected_courses:
            for comp in get_course_components(code):
                opts = get_sections_by_component(code, comp)
                option_labels = [
                    f"{o['section_code']}  ·  {'Open' if o['status'] == '\u5f00\u653e' else 'Closed'}"
                    for o in opts
                ]
                choice = st.selectbox(
                    f'{code} · {comp_label(comp)} ({comp})',
                    ['— Please select —'] + option_labels,
                    key=f'sel_{code}_{comp}',
                )
                if choice != '— Please select —':
                    sec = choice.split('  ·  ')[0].strip()
                    selections.append((code, sec))
                else:
                    missing.append((code, comp))

    st.header('③ Display week')
    st.caption('Choose any date in the desired week (The timetable displays a full week).')
    picked_date = st.date_input('Week start (Choose any date in the desired week)', value=date.today(), key='week_date')
    week_monday = picked_date - timedelta(days=picked_date.weekday())   


st.header('③ Generate timetable')
st.write('After selecting courses and sections, Click to validate hard constraints and generate a weekly timetable.')


with st.expander('Preview selected sections', expanded=False):
    if selections:
        for code, sec in selections:
            st.write(f'- {code} · {sec}')
    else:
        st.write(' (No sections have been selected)')

if st.button('Generate a weekly timetable', type='primary', width='stretch', key='gen_btn'):
    errors = []
    conflict_lines = []

    
    if missing:
        miss_txt = ', '.join(f'{c} of {comp_label(comp)}' for c, comp in missing)
        errors.append(f'⚠️ Section selections are incomplete for these courses: {miss_txt}')

    
    missing_required = [c for c in REQUIRED_FIXED if c not in selected_courses]
    ped_ok = any(c.startswith(REQUIRED_PED_PREFIX) for c in selected_courses)
    if missing_required:
        errors.append(f'❌ Missing required courses: {", ".join(missing_required)}')
    if not ped_ok:
        errors.append('❌ Missing a physical education course: Please use PED1101–PED1123 Select at least one from')

    
    total = total_credits(selected_courses)
    if total < CREDIT_MIN or total > CREDIT_MAX:
        errors.append(f'❌ Total credits {total:.1f} not in 12–18 within the interval (requires {CREDIT_MIN}–{CREDIT_MAX})')

    
    conflict_flag = False
    if not missing:
        conflicts = check_conflicts_multi(selections)
        if conflicts:
            conflict_flag = True
            for c in conflicts:
                conflict_lines.append(
                    f'{c["course_a"]} {c["section_a"]} ({c["time_a"]})and '
                    f'{c["course_b"]} {c["section_b"]} ({c["time_b"]})on weekday{c["weekday"]}Conflict'
                )

    
    if errors or conflict_flag:
        for e in errors:
            st.error(e)
        if conflict_flag:
            st.error('❌ A time conflict exists: ')
            for line in conflict_lines:
                st.write(f'  - {line}')
    else:
        st.success(
            f'✅ Validation passed！Total {len(selected_courses)} courses, '
            f'Total credits {total:.1f} (Interval {CREDIT_MIN}–{CREDIT_MAX}).'
        )
        rows = build_weekly_schedule(selections)

        
        st.subheader(f'Weekly timetable ({week_monday.strftime("%Y-%m-%d")} Current week)')
        render_html(build_timetable_html(rows, week_monday))

        
        with st.expander('Detailed list (Text view)', expanded=False):
            df = pd.DataFrame(rows)
            col_order = ['Weekday', 'Start', 'End', 'Course code', 'Course name', 'Section', 'Type', 'Room']
            st.dataframe(df[col_order], width='stretch', hide_index=True)

        st.metric('Total credits', f'{total:.1f} / {CREDIT_MAX}')
