"""Run with python -m streamlit run app.py."""
from datetime import date, timedelta, time
from dataclasses import asdict
import hashlib
import json
import pandas as pd
import streamlit as st
from model import DB, Preferences, load_catalog
from optimizer import solve
from checker import check
from timetable import DAYS, weekly_rows, render, hhmm

st.set_page_config(page_title='Course Planner', page_icon='📅', layout='wide')
st.markdown('''<style>
.block-container{max-width:1440px;padding-top:2rem}
h1{letter-spacing:-.04em} [data-testid="stMetricValue"]{font-size:1.65rem}
[data-testid="stSidebar"]{border-right:1px solid #dce5eb}
.stDownloadButton button{width:100%}
</style>''', unsafe_allow_html=True)
st.title('Course Planner')
term = st.sidebar.selectbox('Semester', ['2026-27 Term 1', '2026-27 Term 2'], key='semester')
st.caption(f'{term} / Select courses → Set preferences → Compare and edit')
try:
    cat = load_catalog(term=term)
except Exception as exc:
    st.error(f'Unable to read course data: {exc}')
    st.stop()

with st.sidebar:
    st.header('Courses this semester')
    codes = st.multiselect('Select courses to take', sorted(cat.courses),
        format_func=lambda c: f"{c} · {cat.courses[c]['name']}", key=f'courses_{term}')
    credits = sum(cat.courses[c]['credits'] for c in codes)
    st.metric('Selected credits', f'{credits:g}', help='Every selected course must be scheduled. Total credits must be at least 12; the planner has no maximum.')
    if not codes:
        st.info('Select courses first. Start with your required courses.')
    elif credits < 12:
        st.warning(f'You need at least {12-credits:g} more credits.')
    else:
        st.caption(f'Selected {len(codes)} courses · Minimum 12 credits met')
    with st.expander('Search settings and instructions'):
        timeout = st.number_input('Maximum search time (seconds)', 1, 120, 15, key='timeout')
        st.caption('If the search times out, increase the time limit and retry.Scores compare recommendations under the same settings only.')
        st.caption('Lecture/Tutorial bindings and personal prerequisites cannot be verified. Check SIS before enrolling.')

with st.expander('Scheduling preferences and unavailable times', expanded=True):
    time_tab, teacher_tab = st.tabs(['Time preferences', 'Instructor preferences'])
    with time_tab:
        left, right = st.columns(2)
        with left:
            early_mode = st.selectbox('Early classes (08:30)', ['No preference', 'Avoid where possible', 'Prefer', 'Prohibit'], key='early_mode')
            early = {'Avoid where possible': 0, 'Prefer': 5}.get(early_mode)
            ban_early = early_mode == 'Prohibit'
        with right:
            banned = st.multiselect('Entire day unavailable', range(1, 8), format_func=lambda d: DAYS[d-1], key='banned_days')
        weekdays = {}
        with st.expander('Weekly scheduling preferences (Optional)'):
            days = st.multiselect('Weekdays to rate', [d for d in range(1, 8) if d not in banned],
                format_func=lambda d: DAYS[d-1], key='rated_days')
            cols = st.columns(3)
            for i, d in enumerate(days):
                weekdays[d] = cols[i % 3].slider(DAYS[d-1], 0, 5, 0, key=f'day_{d}')
            st.caption('0 = fewer occurrences; 5 = more occurrences. Use “Entire day unavailable” to keep a day completely free.')
        with st.expander('Add recurring unavailable periods (Optional)'):
            st.caption('For example, club activities or recurring meetings. Identical periods are deduplicated automatically.')
            # Editable rows allow adding/removing periods without a separate quantity control.
            frame = st.data_editor(pd.DataFrame(columns=['Weekday', 'Start', 'End']), num_rows='dynamic',
                hide_index=True, key='blocked_editor', column_config={
                    'Weekday': st.column_config.SelectboxColumn('Weekday', options=DAYS, required=True),
                    'Start': st.column_config.TimeColumn('Start', format='HH:mm', required=True),
                    'End': st.column_config.TimeColumn('End', format='HH:mm', required=True)})
            blocked = []
            bad_block = False
            for _, row in frame.iterrows():
                d, a, b = row['Weekday'], row['Start'], row['End']
                try:
                    a = time.fromisoformat(a) if isinstance(a, str) else a
                    b = time.fromisoformat(b) if isinstance(b, str) else b
                except ValueError:
                    bad_block = True
                    continue
                if d not in DAYS or not isinstance(a, time) or not isinstance(b, time) or a >= b:
                    bad_block = True
                    continue
                blocked.append((DAYS.index(d)+1, a.hour*60+a.minute, b.hour*60+b.minute))
            blocked = sorted(set(blocked))
            if bad_block:
                st.error('Complete the weekday and times in each row, and ensure the end time is later than the start time; delete unused rows.')
    with teacher_tab:
        teachers = {}
        if not codes:
            st.info('Select courses to search for and rate their instructors.')
        for code in codes:
            names = sorted({t for s in cat.sections[code] for t in s.teachers})
            selected = st.multiselect(f"{code} · {cat.courses[code]['name']}", names, key=f'teachers_{code}')
            if selected:
                teachers[code] = {t: st.slider(f'{code} · {t}', 0, 5, 5, key=f'teacher_{code}_{t}') for t in selected}
        st.caption('0 = Least preferred, 5 = Most preferred; unrated instructors receive a neutral rating; courses without instructor preferences are excluded from instructor scoring.')

p = Preferences(early, weekdays, teachers, ban_early, tuple(banned), tuple(blocked))
db_hash = hashlib.sha256(DB.read_bytes()).hexdigest()
signature = hashlib.sha256((db_hash+json.dumps([term, codes, asdict(p)], sort_keys=True)).encode()).hexdigest()
ready = bool(codes) and credits >= 12 and not bad_block


def seed_manual(selections):
    for code in codes:
        for comp in cat.required[code]:
            options = [s.code for s in cat.sections[code] if s.component == comp]
            st.session_state[f'manual_{signature}_{code}_{comp}'] = next(
                (sec for c, sec in selections if c == code and sec in options), '— Not selected —')


if st.button('Generate recommendations', type='primary', key='generate', disabled=not ready):
    with st.spinner('Searching combinations and checking conflicts…'):
        result = solve(cat, codes, p, timeout=timeout)
        reports = [check(cat, codes, s['selections'], p) for s in result.solutions]
    st.session_state['result'] = (signature, result, reports)
    st.session_state['solution'] = 0
    st.session_state['editing'] = False
    if result.solutions:
        seed_manual(result.solutions[0]['selections'])

saved = st.session_state.get('result')
current = saved is not None and saved[0] == signature
if saved and not current:
    st.info('Semester, courses, preferences, or the database have changed. Regenerate the timetable. Previous plans are hidden.')

st.divider()
st.subheader('My timetable')
selections = None
report = None
sol = None
idx = 0
result = saved[1] if current else None
status = 'manual'
if result:
    labels = {'optimal': 'Search completed · Found the best schedules under the current scoring rules',
        'infeasible': 'No feasible schedule satisfies the selected courses and blocked times, Reduce blocked-time restrictions or change courses.',
        'invalid': 'Correct the input',
        'timeout_feasible': 'Search time limit reached · You may use the current plan, or increase the search time to keep searching',
        'timeout_no_solution': 'No plan has been found yet · Increase the search time; This does not prove infeasibility'}
    st.info(labels[result.status])
    for error in result.errors:
        st.error(error)
    if result.solutions:
        idx = st.radio('Recommended plans', range(len(result.solutions)), horizontal=True,
            format_func=lambda i: f'Plan {i+1} · {result.solutions[i]["score"]:.1f} points', key='solution')
        sol = result.solutions[idx]
        selections = sol['selections']
        report = saved[2][idx]
        status = result.status
        if st.button('Edit sections using this plan', key='load_manual'):
            seed_manual(selections)
            st.session_state['editing'] = True
        with st.expander('Scoring and search details'):
            st.caption(f'Search elapsed time {result.elapsed:.2f} seconds · Visited {result.nodes:,} nodes')
            if sol['breakdown']:
                st.write({{'early': 'Early classes', 'weekdays': 'Weekday', 'teachers': 'Instructor'}.get(k,k): round(v,2) for k,v in sol['breakdown'].items()})
            st.caption('Early-class, weekday, and instructor categories have equal weight; unconfigured categories are excluded. Time preferences count actual semester meetings. Scores are not satisfaction percentages.')

# One shared preview/export area for recommended and edited selections.
editing = st.toggle('Edit sections manually', key='editing', disabled=not ready)
if editing and ready:
    st.caption('Each section change is validated automatically. Turn this off to return to recommendations; manual selections are retained.')
    selections = []
    for code in codes:
        with st.expander(f"{code} · {cat.courses[code]['name']}", expanded=True):
            cols = st.columns(max(1, len(cat.required[code])))
            for i, comp in enumerate(sorted(cat.required[code])):
                opts = {s.code: s for s in cat.sections[code] if s.component == comp}
                def label(sec, opts=opts):
                    if sec not in opts:
                        return sec
                    s = opts[sec]
                    times = ' / '.join(dict.fromkeys(f'{DAYS[m.weekday-1]} {hhmm(m.start)}–{hhmm(m.end)}' for m in s.meetings))
                    return f'{sec} · {" / ".join(s.teachers) or "Instructor TBA"} · {times}'
                value = cols[i].selectbox({'LEC':'Lecture','TUT':'Tutorial'}.get(comp,comp),
                    ['— Not selected —']+list(opts), format_func=label, key=f'manual_{signature}_{code}_{comp}')
                if value in opts:
                    selections.append((code, value))
    report = check(cat, codes, selections, p)
    status = 'manual'
    sol = {'selections': selections}

if selections is not None and report is not None:
    if report['passed'] and not bad_block:
        st.success('Independent validation passed · Components, credits, teaching dates, and blocked times satisfy the requirements')
        meetings = [m for code, sec in selections for s in cat.sections[code] if s.code == sec for m in s.meetings]
        first, last = min(m.first for m in meetings), max(m.last for m in meetings)
        weeks = []
        cursor = first-timedelta(days=first.weekday())
        while cursor <= last:
            weeks.append(cursor)
            cursor += timedelta(days=7)
        default = max(weeks[0], min(date.today()-timedelta(days=date.today().weekday()), weeks[-1]))
        monday = st.selectbox('Teaching week to display', weeks, index=weeks.index(default),
            format_func=lambda d: f'Week {weeks.index(d)+1} · {d:%m/%d} – {d+timedelta(days=6):%m/%d}', key='week')
        rows = weekly_rows(cat, selections, monday)
        metrics = st.columns(3)
        metrics[0].metric('Class meetings this week', len(rows))
        metrics[1].metric('Early-class meetings', sum(r['start'] == 510 for r in rows))
        metrics[2].metric('Class-free days', sum(not any(r['weekday'] == d for r in rows) for d in range(1,8)))
        st.markdown(render(rows), unsafe_allow_html=True)
        visible = [{k:v for k,v in r.items() if k not in ('weekday','start','end')} for r in rows]
        with st.expander('Class details for this week'):
            st.dataframe(pd.DataFrame(visible), hide_index=True)
        downloads = st.columns(2)
        downloads[0].download_button('Export weekly CSV', pd.DataFrame(visible).to_csv(index=False).encode('utf-8-sig'),
            f'timetable_{monday}.csv', 'text/csv', key='csv', disabled=not rows)
        payload = {'term': term, 'courses': codes, 'preferences': asdict(p), 'solution': sol, 'validation': report,
            'status': status, 'database_sha256': db_hash}
        downloads[1].download_button('Export the complete semester plan', json.dumps(payload, ensure_ascii=False, indent=2),
            'schedule.json', 'application/json', key='json')
        st.caption('CSV covers the displayed week. The complete plan contains section selections for the entire semester.')
    else:
        st.warning('The current plan failed validation. Adjust it before previewing or exporting.')
        for error in report['errors']:
            st.error(error)
    with st.expander('Verify before enrollment'):
        for warning in report['warnings']:
            st.warning(warning)
elif not saved:
    st.info('Select at least 12 credits, then click “Generate recommendations”, or enable manual section editing.')
