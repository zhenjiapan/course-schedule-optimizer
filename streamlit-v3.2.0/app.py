"""Streamlit entry point for Course Schedule Optimizer v3.2.0."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import timedelta
from io import StringIO
from pathlib import Path
import csv
import json
import os
from time import monotonic

import plotly.graph_objects as go
import streamlit as st

from backend.app.optimization.model import dates
from backend.app.optimization.v4.policy import Policy
from backend.app.optimization.v4.solve import solve, validate
from streamlit_catalog import catalog_from_snapshot

ROOT = Path(__file__).resolve().parent
SNAPSHOT = Path(os.environ.get("COURSE_SNAPSHOT", ROOT / "private/sis-2026-11-24-fin2010.sqlite"))
DAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
PERIODS = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}
CATEGORIES = {"T": "教师", "W": "星期", "H": "时间", "D": "每日结构", "B": "周内分布"}

st.set_page_config(page_title="课表规划 v3.2.0", layout="wide")


@st.cache_resource
def workers():
    return ThreadPoolExecutor(max_workers=2)


@st.cache_data
def load(term, snapshot_version):
    return catalog_from_snapshot(SNAPSHOT, term)


def clock(value):
    return f"{value // 60:02d}:{value % 60:02d}"


def minute(value):
    hour, minutes = map(int, value.split(":"))
    if not 0 <= minutes < 60 or not 0 <= 60 * hour + minutes <= 1440:
        raise ValueError("时间须在 00:00 至 24:00 之间")
    return hour * 60 + minutes


def rating(label, key):
    return st.select_slider(label, [1, 2, 3, 4, 5], value=3, key=key)


def boundary(label, default):
    mode = st.selectbox(label, ["", "hard", "soft"], format_func=lambda s: {"": "不限", "hard": "硬约束", "soft": "偏好"}[s])
    return {"mode": mode, "minute": st.text_input(label + "时间", default)} if mode else None


def work(cat, codes, policy, progress):
    return solve(cat, codes, policy, timeout=None, progress_store=progress, progress_job_id="run")


def show_schedule(cat, selections, policy, term, report=None):
    sections = [next(section for section in cat.sections[code] if section.code == name)
                for code, name in selections]
    rows = [{"course": section.course, "section": section.code, "date": day,
             "start": clock(meeting.start), "end": clock(meeting.end),
             "room": " / ".join(meeting.rooms), "teacher": " / ".join(meeting.teachers)}
            for section in sections for meeting in section.meetings for day in dates(meeting)]
    weeks = sorted({row["date"] - timedelta(days=row["date"].weekday()) for row in rows})
    if weeks:
        week = st.selectbox("查看教学周", weeks)
        fig = go.Figure()
        for row in rows:
            offset = (row["date"] - week).days
            if 0 <= offset < 7:
                start, end = minute(row["start"]), minute(row["end"])
                fig.add_trace(go.Bar(x=[offset], y=[end-start], base=[start], width=.92,
                                     text=[f"{row['course']} {row['section']}"],
                                     customdata=[[row["start"], row["end"], row["room"], row["teacher"]]],
                                     hovertemplate="%{text}<br>%{customdata[0]}–%{customdata[1]}<br>%{customdata[2]}<br>%{customdata[3]}<extra></extra>"))
        fig.update_layout(barmode="overlay", showlegend=False, height=520)
        fig.update_xaxes(tickvals=list(range(7)), ticktext=list(DAYS), range=[-.5, 6.5])
        fig.update_yaxes(autorange="reversed", tickvals=list(range(0, 1441, 60)),
                         ticktext=[clock(i) for i in range(0, 1441, 60)])
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(rows, hide_index=True)
    csv_file = StringIO()
    writer = csv.DictWriter(csv_file, fieldnames=["course", "section", "date", "start", "end", "room", "teacher"])
    writer.writeheader()
    writer.writerows(rows)
    st.download_button("导出 CSV", csv_file.getvalue(), "schedule.csv", "text/csv")
    st.download_button("导出 JSON", json.dumps({"term": term, "selections": selections,
                       "preferences": policy.model_dump(mode="json"), "validation": report,
                       "meetings": [asdict(meeting) for section in sections for meeting in section.meetings]},
                       ensure_ascii=False, default=str), "schedule.json", "application/json")


st.title("课表规划 v3.2.0")
st.caption("课程与班次以学校 SIS 快照为准。实时余位、先修资格及注册结果请在 SIS 核实。")
term = st.selectbox("学期", ["2026-27 Term 1", "2026-27 Term 2"])
if not SNAPSHOT.is_file():
    st.error("课程快照不存在。请设置 COURSE_SNAPSHOT 或查看 README。")
    st.stop()
cat = load(term, SNAPSHOT.stat().st_mtime_ns)
codes = st.multiselect("搜索并选择课程", sorted(cat.courses),
                       format_func=lambda code: f"{code} · {cat.courses[code]['name']}")
sections = {code: cat.sections[code] for code in codes}
credits = sum(float(cat.courses[code]["credits"]) for code in codes)
st.caption(f"已选 {len(codes)} 门 · {credits:g} 学分")
with st.expander("班次、教学时间与配对"):
    for code, items in sections.items():
        st.write(code, "必需组件", ", ".join(sorted(cat.required[code])))
        st.dataframe([{"班次": s.code, "组件": s.component, "星期": DAYS[m.weekday-1],
                       "时间": f"{clock(m.start)}–{clock(m.end)}", "教师": " / ".join(m.teachers),
                       "教室": " / ".join(m.rooms), "开始日期": m.first, "结束日期": m.last}
                      for s in items for m in s.meetings], hide_index=True)
        bindings = {lecture: sorted(tutorials) for (course, lecture), tutorials in cat.bindings.items() if course == code}
        if bindings:
            st.write(bindings)
        for warning in cat.warnings:
            if warning.startswith(code + " "):
                st.caption(warning)

with st.container():
    limits, hard, times, structure, weights = st.tabs(["学分", "硬约束", "时间与教师", "课表结构", "偏好权重"])
    with limits:
        minimum = st.number_input("最低学分", min_value=0.0, value=12.0)
        maximum = st.number_input("最高学分", min_value=0.0, value=18.0)
    with hard:
        options = [(code, s.code) for code, items in sections.items() for s in items]
        rules = {key: st.multiselect(label, options) for key, label in
                 (("required", "必须选的班次"), ("locked", "锁定班次"), ("excluded", "排除班次"))}
        banned = st.multiselect("全天不可用", range(1, 8), format_func=lambda day: DAYS[day-1])
        ban_early = st.checkbox("禁止早八")
        preset_day = st.selectbox("快捷禁排星期", range(1, 8), format_func=lambda day: DAYS[day-1])
        presets = st.multiselect("快捷禁排时段", list(PERIODS), format_func=PERIODS.get)
        blocked = st.text_area("自定义不可用时间，每行填写：星期数字,开始,结束", placeholder="1,08:30,12:00")
    with times:
        earliest, latest = boundary("最早上课", "10:00"), boundary("最晚下课", "18:00")
        early = rating("早八偏好", "early")
        weekday_ratings = {i: rating(day, f"day-{i}") for i, day in enumerate(DAYS, 1)}
        period_ratings = {key: rating(label, key) for key, label in PERIODS.items()}
        teachers = sorted({name for items in sections.values() for section in items for name in section.teachers})
        with st.expander("教师偏好"):
            teacher_ratings = {name: rating(name, f"teacher-{name}") for name in teachers}
    with structure:
        gaps = st.selectbox("课间空档", [None, "compact", "balanced", "spacious"],
                            format_func=lambda s: {None:"不限", "compact":"紧凑", "balanced":"均衡", "spacious":"宽松"}[s])
        distribution = st.selectbox("周内分布", [None, "concentrated", "distributed"],
                                    format_func=lambda s: {None:"不限", "concentrated":"集中", "distributed":"分散"}[s])
        free_mode = st.selectbox("空闲天数规则", [None, "hard", "soft"])
        free_days = st.number_input("最少空闲工作日", 0, 5, 2)
        mondays = sorted({day-timedelta(days=day.weekday()) for items in sections.values()
                          for section in items for meeting in section.meetings for day in dates(meeting)})
        weeks = st.multiselect("教学周（启用周内分布或空闲天数规则时请选择）", mondays)
        counts = {}
        for period, label in PERIODS.items():
            comparison = st.selectbox(label + "课程数量规则", [None, "exactly", "at_most", "at_least"])
            target = st.number_input(label + "目标节数", 0, 48, 2)
            if comparison:
                counts[period] = {"comparison": comparison, "target": target}
    with weights:
        disabled = st.multiselect("关闭的评分项", CATEGORIES, format_func=CATEGORIES.get)
        importance = {key: rating(label + "重要性", f"weight-{key}") for key, label in CATEGORIES.items()}
    submitted = st.button("搜索课表", type="primary")

if submitted:
    current = st.session_state.get("search")
    if current and not current[0].done():
        st.warning("已有搜索正在进行。")
    elif not codes:
        st.warning("请先选择课程。")
    else:
        try:
            slot_times = {"morning": (0, 720), "afternoon": (720, 1080), "evening": (1080, 1440)}
            blocks = [(preset_day, *slot_times[slot]) for slot in presets]
            for line in blocked.splitlines():
                if line.strip():
                    day, start, end = (part.strip() for part in line.split(","))
                    blocks.append((int(day), minute(start), minute(end)))
            for rule in (earliest, latest):
                if rule:
                    rule["minute"] = minute(rule["minute"])
            policy = Policy(credit_min=minimum, credit_max=maximum, **rules, banned_days=banned,
                            blocked=blocks, ban_early=ban_early, earliest=earliest, latest=latest,
                            early=early if early != 3 else None,
                            weekdays=weekday_ratings if any(v != 3 for v in weekday_ratings.values()) else {},
                            periods=period_ratings if any(v != 3 for v in period_ratings.values()) else {},
                            teachers={name: value for name, value in teacher_ratings.items() if value != 3},
                            gaps=gaps, counts=counts, distribution=distribution, teaching_weeks=weeks,
                            free_days={"mode": free_mode, "minimum": free_days} if free_mode else None,
                            weights=importance, disabled=disabled)
        except ValueError as error:
            st.error(str(error))
        else:
            progress = {}
            future = workers().submit(work, cat, codes, policy, progress)
            st.session_state.search = (future, progress, cat, codes, policy, term)
            st.session_state.pop("preview", None)
            st.session_state.pop("preview_at", None)


@st.fragment(run_every=1)
def results():
    current = st.session_state.get("search")
    if not current:
        return
    future, progress, search_cat, search_codes, search_policy, search_term = current
    st.subheader("搜索结果")
    st.caption(f"{search_term} · {', '.join(search_codes)}")
    answer = None
    if future.done():
        try:
            answer = future.result()
        except Exception as error:
            st.error(f"搜索失败：{error}")
            return
        stats = answer["search_summary"]
        total = answer.get("qualified_schedule_count")
        st.metric("合格课表总数", total if total is not None else "未完成统计")
        st.metric("搜索分支总数", f"{stats['branches']:,}")
        labels = {"optimal": "已完成搜索", "infeasible_proven": "已证明无可行课表",
                  "feasible_unproven": "已有可行课表，未完成排名证明",
                  "timeout_no_feasible": "未找到可行课表"}
        st.write(labels.get(answer["status"], answer["status"]))
        st.caption(f"已证明名次：{answer['certified_prefix']}")
        for error in answer["errors"]:
            st.error(error)
        for warning in answer["warnings"]:
            st.warning(warning)
        with st.expander("求解统计与评分校准"):
            st.json({"统计": stats, "评分校准": answer.get("calibration", {}),
                     "目标界": answer.get("objective_bound")})
        leaders = answer["solutions"]
    else:
        snapshot = progress.get("run", {})
        phases = {"preparing": "正在准备模型", "counting_schedules": "正在枚举合格课表"}
        st.info(phases.get(snapshot.get("phase"), "正在搜索"))
        st.metric("已找到的课表", snapshot.get("schedules_found", "0"))
        st.metric("已搜索的分支", f"{snapshot.get('branches', 0):,}")
        now = monotonic()
        if now - st.session_state.get("preview_at", 0) >= 10:
            st.session_state.preview = snapshot.get("preview", [])
            st.session_state.preview_at = now
        leaders = st.session_state.get("preview", [])
    if not leaders:
        return
    index = st.selectbox("选择推荐方案", list(range(len(leaders))), format_func=lambda i: f"方案 {i+1}")
    solution = leaders[index]
    score = solution.get("score")
    if score is not None:
        st.write(f"评分 {score:.2f}")
    st.json(solution.get("breakdown", {}), expanded=False)
    selections = solution["selections"]
    report = solution.get("validation")
    if answer and st.checkbox("手动调整班次"):
        picks = []
        for course, old_code in selections:
            old = next(section for section in search_cat.sections[course] if section.code == old_code)
            alternatives = [s.code for s in search_cat.sections[course] if s.component == old.component]
            updated = st.selectbox(f"{course} · {old.component}", alternatives,
                                   index=alternatives.index(old_code),
                                   key=f"{id(future)}-{index}-{course}-{old_code}")
            picks.append((course, updated))
        selections = picks
        report = validate(search_cat, search_codes, search_policy, selections)
        if report["passed"]:
            st.success("调整后的课表通过独立校验。")
        else:
            st.error("调整后的课表未通过独立校验。")
    if report:
        with st.expander("独立校验"):
            st.json(report, expanded=False)
        if not report["passed"]:
            return
    show_schedule(search_cat, selections, search_policy, search_term, report)


results()
