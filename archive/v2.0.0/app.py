"""Run: python -m streamlit run app.py"""
from datetime import date,timedelta,time
from dataclasses import asdict
import hashlib,json
import pandas as pd
import streamlit as st
from model import DB,Preferences,load_catalog,minutes
from optimizer import solve
from checker import check
from timetable import DAYS,weekly_rows,render

st.set_page_config(page_title='Course Schedule Optimizer v2.0.0',page_icon='📅',layout='wide')
st.title('📅 Course Schedule Optimizer v2.0.0')
st.caption('Select courses, Set preferences, Select sections automatically and validate independently.12–18 Credits; All sections are considered for planning.')
try:cat=load_catalog()
except Exception as exc:st.error(f'Unable to read the database: {exc}');st.stop()
with st.sidebar:
    codes=st.multiselect('Courses to take',list(cat.courses),format_func=lambda c:f"{c} · {cat.courses[c]['name']}",key='courses')
    credits=sum(cat.courses[c]['credits'] for c in codes)
    st.metric('Total credits',f'{credits:g} / 12–18')
    picked=st.date_input('Display week (Any date)',date.today(),key='week')
    monday=picked-timedelta(days=picked.weekday())
    timeout=st.number_input('Search time limit (seconds)',min_value=1,max_value=120,value=15,key='timeout')

st.subheader('Preference settings')
st.caption('0 = Least preferred, 5 = Most preferred.Unchecked categories are excluded from scoring; 0 points does not mean prohibited.')
early=None
if st.checkbox('Set early-class preferences',key='rate_early'):
    early=st.slider('08:30 classes starting at',0,5,0,key='early')
weekdays={}
with st.expander('Preferred weekdays for classes'):
    days=st.multiselect('Weekdays to rate',range(1,8),format_func=lambda d:DAYS[d-1],key='rated_days')
    for d in days:weekdays[d]=st.slider(f'{DAYS[d-1]}Scheduling preferences',0,5,0,key=f'day_{d}')
teachers={}
with st.expander('Preferred instructors (Search by name)'):
    for code in codes:
        names=sorted({t for s in cat.sections[code] for t in s.teachers})
        selected=st.multiselect(f'{code} Instructor name',names,key=f'teachers_{code}')
        if selected:
            teachers[code]={t:st.slider(f'{code} · {t}',0,5,5,key=f'teacher_{code}_{t}') for t in selected}
    st.caption('Unrated instructors are neutral 2.5 points; The system matches instructors to their sections.')
with st.expander('Hard constraints: Strictly unavailable times'):
    ban_early=st.checkbox('Block all 08:30 classes starting at',key='ban_early')
    banned=st.multiselect('Weekdays with no availability',range(1,8),format_func=lambda d:DAYS[d-1],key='banned_days')
    blocked=[];bad_block=False
    count=st.number_input('Number of additional blocked periods',0,10,0,key='block_count')
    for i in range(count):
        cols=st.columns(3)
        d=cols[0].selectbox(f'Period {i+1} Weekday',range(1,8),format_func=lambda d:DAYS[d-1],key=f'block_day_{i}')
        a=cols[1].time_input('Start',value=time(18),key=f'block_a_{i}')
        b=cols[2].time_input('End',value=time(21),key=f'block_b_{i}')
        if a>=b:bad_block=True;st.error('A blocked period must end after it starts.')
        blocked.append((d,a.hour*60+a.minute,b.hour*60+b.minute))
p=Preferences(early,weekdays,teachers,ban_early,tuple(banned),tuple(blocked))
signature=hashlib.sha256(DB.read_bytes()+json.dumps([codes,asdict(p)],sort_keys=True).encode()).hexdigest()

if st.button('Generate timetable automatically',type='primary',key='generate',disabled=bad_block):
    with st.spinner('Search section combinations and validate independently…'):
        result=solve(cat,codes,p,timeout=timeout)
        reports=[check(cat,codes,s['selections'],p) for s in result.solutions]
        st.session_state['result']=(signature,result,reports)
        if result.solutions:
            for code,sec in result.solutions[0]['selections']:
                comp=next(s.component for s in cat.sections[code] if s.code==sec)
                st.session_state[f'manual_{signature}_{code}_{comp}']=sec


def show(selections,key):
    rows=weekly_rows(cat,selections,monday)
    st.markdown(render(rows),unsafe_allow_html=True)
    visible=[{k:v for k,v in r.items() if k not in ('weekday','start','end')} for r in rows]
    if visible:
        st.dataframe(pd.DataFrame(visible),hide_index=True)
        csv=pd.DataFrame(visible).to_csv(index=False).encode('utf-8-sig')
        st.download_button('Download weekly CSV',csv,f'timetable_{monday}.csv','text/csv',key=f'csv_{key}')
    st.caption(f'Early classes this week {sum(r["start"]==510 for r in rows)} occurrences; Class-free days: '+ ', '.join(DAYS[d-1] for d in range(1,8) if not any(r['weekday']==d for r in rows)))

saved=st.session_state.get('result')
if saved and saved[0]!=signature:st.info('Course, Preferences or the database have changed, Regenerate the timetable.')
if saved and saved[0]==signature:
    _,result,reports=saved
    labels={'optimal':'Search completed: Found the highest-ranked schedules under the current scoring rules','infeasible':'No feasible schedule exists under the current data and constraints','invalid':'Correct the input','timeout_feasible':'Search time limit reached: Show the best plan found so far, Optimality has not been proved','timeout_no_solution':'Search time limit reached, No plan has been found yet; This does not prove infeasibility'}
    st.info(labels[result.status])
    st.caption(f'Visited {result.nodes:,} search nodes, Elapsed time {result.elapsed:.2f} seconds.')
    for error in result.errors:st.error(error)
    if result.solutions:
        idx=st.selectbox('View plan',range(len(result.solutions)),format_func=lambda i:f'Plan {i+1} · {result.solutions[i]["score"]:.1f} points',key='solution')
        sol=result.solutions[idx];report=reports[idx]
        if st.button('Load this plan into the manual validation area',key='load_manual'):
            for code,sec in sol['selections']:
                comp=next(s.component for s in cat.sections[code] if s.code==sec)
                st.session_state[f'manual_{signature}_{code}_{comp}']=sec
        if report['passed']:
            st.success('Independent validation passed: Course, Component, Credits, Teaching dates and blocked times.')
            if sol['breakdown']:st.write({k:round(v,2) for k,v in sol['breakdown'].items()})
            show(sol['selections'],'auto')
        else:
            st.error('Independent validation failed, Not displayed as a feasible timetable.')
            for error in report['errors']:st.error(error)
        with st.expander('Data notes and validation scope'):
            for warning in report['warnings']:st.warning(warning)
        payload={'courses':codes,'preferences':asdict(p),'solution':sol,'validation':report,'status':result.status,'database_sha256':hashlib.sha256(DB.read_bytes()).hexdigest()}
        st.download_button('Download the complete plan JSON',json.dumps(payload,ensure_ascii=False,indent=2),'schedule.json','application/json',key='json')

with st.expander('Manual section selection／Independent feasibility check'):
    selections=[]
    defaults=saved[1].solutions[0]['selections'] if saved and saved[0]==signature and saved[1].solutions else []
    for code in codes:
        for comp in sorted(cat.required[code]):
            opts=[s.code for s in cat.sections[code] if s.component==comp]
            options=['— Not selected —']+opts
            seed=next((sec for c,sec in defaults if c==code and sec in opts),options[0])
            value=st.selectbox(f'{code} {comp}',options,index=options.index(seed),key=f'manual_{signature}_{code}_{comp}')
            if value!=options[0]:selections.append((code,value))
    if st.button('Validate the manual plan',key='check_manual'):
        report=check(cat,codes,selections,p)
        if report['passed']:st.success('Manual plan passed validation');show(selections,'manual')
        else:
            for error in report['errors']:st.error(error)
        for warning in report['warnings']:st.warning(warning)
with st.expander('Scoring rules'):
    st.write('Early classes, Weekday, Instructor categories have equal weight, Unconfigured categories are excluded.Early classes mean exactly 08:30 Start.Time preferences count actual semester occurrences; 0 points favors fewer occurrences, 5 points favors more occurrences.The weekday score averages the rated weekdays.Instructor scoring includes only components with rated instructors, Unrated instructors are neutral.Scores compare schedules within this request, Not an absolute satisfaction percentage; Scores should not be compared across requests with different hard constraints.')
