"use client";

import {useEffect,useRef,useState} from "react";
import Calendar from "./calendar";
import {api,clock,download,minute,type Course,type Detail,type Progress,type Result,type Selection,type Validation} from "./api";
import {HardRules,Structure,TimePreferences,Weights,componentName,ruleNames} from "./v4-controls";
import {candidateMondays,categories,defaults,makePayload,periodNames,periods,validTime,weekdays,type Category,type Form} from "./v4-form";

const terms=[["2026-27 Term 1","2026–27 第一学期"],["2026-27 Term 2","2026–27 第二学期"]];
const modules=[
  ["A","课程与学分","确定修读课程、学分范围与组件"],
  ["B","排课硬约束","设置禁排、必须选、锁定和排除"],
  ["C","时间与教师","设置时间边界与 1–5 档喜好"],
  ["D","课表结构","设置空档、节数和周内分布"],
  ["E","偏好重要性","决定哪些类别计分以及各自重要性"],
  ["F","求解设置","设置搜索时间和查看推荐规则"],
];
const statuses:Record<string,string>={
  browser_complete:"搜索完成 · 浏览器评分排序",
  optimal:"搜索完成", feasible_unproven:"已找到可行方案 · 部分或全部名次未获证明",
  timeout_no_feasible:"搜索超时 · 尚未找到已验证的可行方案", infeasible_proven:"已证明无解",
  insufficient_data:"课程或校历资料不足", invalid:"输入需要修正", internal_error:"结果验证未完成",
};
const formatCount=(value:string|number)=>String(value).replace(/\B(?=(\d{3})+(?!\d))/g,",");
const progressPhases:Record<string,string>={
  counting_schedules:"正在统计全部合格课表",
  queued:"等待求解进程", preparing:"正在读取并筛选班次", feasibility:"正在寻找可行课表",
  model_build:"正在建立偏好评分模型", preference_calibration:"正在校准偏好评分",
  top_k_ranking:"正在优化并排序推荐课表", tie_breaking:"正在确定同分方案顺序",
  completed:"计算完成", timed_out:"请求超时", failed:"计算失败",
};
type Settings={timeout_limit:number;top_k:number;last_verified:string|null;data_source:string};
const errorText=(value:unknown)=>value instanceof Error?value.message:String(value);

function CourseDetails({detail}:{detail:Detail}) {
  const binding=Object.entries(detail.bindings??{});
  const hasPair=detail.required.includes("LEC")&&detail.required.includes("TUT");
  return <div className="v4-course-detail">
    <p><strong>{detail.code} · {detail.name}</strong> · {detail.credits} 学分</p>
    <p className="muted">必需组件：{detail.required.map(componentName).join("、")||"未核实"}</p>
    {binding.length>0?<details><summary>有限定 · 查看讲课与辅导课配对</summary>
      <ul className="details-list">{binding.map(([lec,tuts])=><li key={lec}>{lec} → {tuts.join("、")}</li>)}</ul>
    </details>:hasPair?<p className="muted">配对未核实，暂按可搭配处理。最终规则请在 SIS 核实。</p>:<p className="muted">必需组件中没有讲课与辅导课的配对要求。</p>}
    <details><summary>查看班次和教学时间</summary><ul className="details-list">
      {detail.sections.map(s=><li key={s.code}><strong>{s.code} · {componentName(s.component)}</strong>
        {s.meetings.map((m,i)=><p key={i}>{weekdays[m.weekday-1]} {clock(m.start)}–{clock(m.end)} · {m.first===m.last?m.first:`${m.first} 至 ${m.last}`} · {m.teachers.join(" / ")||"教师待定"}</p>)}</li>)}
    </ul></details>
    {detail.warnings.map(w=><p key={w} className="muted">{w}</p>)}
  </div>;
}

export default function Planner() {
  const [term,setTerm]=useState(terms[0][0]);
  const [courses,setCourses]=useState<Course[]>([]);
  const [settings,setSettings]=useState<Settings>();
  const [loading,setLoading]=useState(true);
  const [catalogError,setCatalogError]=useState("");
  const [query,setQuery]=useState("");
  const [codes,setCodes]=useState<string[]>([]);
  const [details,setDetails]=useState<Record<string,Detail>>({});
  const [view,setView]=useState("");
  const [step,setStep]=useState(0);
  const [form,setForm]=useState<Form>(defaults);
  const [result,setResult]=useState<Result>();
  const [index,setIndex]=useState(0);
  const [manual,setManual]=useState<Selection[]>();
  const [manualReport,setManualReport]=useState<Validation>();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [progress,setProgress]=useState<Progress|null>(null);
  const resultsRef=useRef<HTMLElement>(null);

  useEffect(()=>{
    let active=true;
    const search="?term="+encodeURIComponent(term);
    api<Course[]>("courses"+search).then(rows=>{if(active)setCourses(rows);})
      .catch(e=>{if(active)setCatalogError(errorText(e));}).finally(()=>{if(active)setLoading(false);});
    api<Settings>("v4/settings"+search).then(value=>{if(active)setSettings(value);}).catch(()=>{if(active)setSettings(undefined);});
    return ()=>{active=false;};
  },[term]);

  const invalidate=()=>{setResult(undefined);setManualReport(undefined);setError("");setProgress(null);};
  function update<K extends keyof Form>(key:K,value:Form[K]) {
    setForm(old=>({...old,[key]:value}));
    invalidate();
  }
  const detailFor=(code:string)=>details[term+":"+code];
  async function loadDetail(code:string){
    const key=term+":"+code;
    if(detailFor(code))return;
    try {
      const item=await api<Detail>("courses/"+encodeURIComponent(code)+"?term="+encodeURIComponent(term));
      setDetails(old=>({...old,[key]:item}));
    } catch(e){setError(errorText(e));}
  }
  function toggleCourse(code:string){
    invalidate();
    if(codes.includes(code)){
      setCodes(old=>old.filter(c=>c!==code));
      setManual(old=>old?.filter(([c])=>c!==code));
      setForm(old=>({...old,sectionRules:old.sectionRules.filter(r=>r.selection[0]!==code)}));
    }else{
      setCodes(old=>[...old,code]);
      void loadDetail(code);
    }
  }
  function changeTerm(value:string){
    setTerm(value);setCourses([]);setCodes([]);setView("");setQuery("");setStep(0);setSettings(undefined);
    setLoading(true);setCatalogError("");setManual(undefined);
    setForm(old=>({...old,sectionRules:[],teachers:{},weeks:[]}));
    invalidate();
  }

  const selected=courses.filter(c=>codes.includes(c.code));
  const selectedDetails=codes.flatMap(c=>detailFor(c)?[detailFor(c)]:[]);
  const teacherNames=[...new Set(selectedDetails.flatMap(d=>d.sections.flatMap(s=>s.teachers)))].sort();
  const weeks=candidateMondays(selectedDetails);
  const confirmedWeeks=form.weeks.filter(w=>weeks.includes(w));
  const needsWeeks=(!!form.distribution&&!form.disabled.includes("B"))||
    (form.freeDays>0&&(form.freeMode==="hard"||(form.freeMode==="soft"&&!form.disabled.includes("B"))));
  const payload=makePayload({...form,weeks:confirmedWeeks},term,codes,teacherNames);
  const credits=Math.round(selected.reduce((n,c)=>n+c.credits,0)*1e8)/1e8;
  const min=Number(form.creditMin||12),max=Number(form.creditMax||18);
  const badCredit=!Number.isFinite(min)||!Number.isFinite(max)||min<0||max<min;
  const badBlock=form.blocks.some(b=>b.kind==="custom"&&(!validTime(b.start)||!validTime(b.end,true)||b.start===b.end));
  const badBoundary=(!!form.earliest.mode&&!validTime(form.earliest.time))||
    (!!form.latest.mode&&!validTime(form.latest.time,true))||
    (form.earliest.mode==="hard"&&form.latest.mode==="hard"&&minute(form.earliest.time)>=minute(form.latest.time));
  const badCount=periods.some(k=>{
    const {target,comparison}=form.counts[k];
    return comparison&&(!/^\d+$/.test(target)||Number(target)>48);
  });
  const forced=new Map<string,string[]>();
  for(const rule of form.sectionRules.filter(r=>r.rule!=="excluded")){
    const [code,name]=rule.selection;
    const component=detailFor(code)?.sections.find(s=>s.code===name)?.component;
    if(component){
      const key=`${code} · ${componentName(component)}`;
      forced.set(key,[...(forced.get(key)??[]),name]);
    }
  }
  const duplicateForce=[...forced].find(([,names])=>names.length>1);
  const excludedComponent=selectedDetails.flatMap(d=>d.required.map(component=>({d,component,sections:d.sections.filter(s=>s.component===component)})))
    .find(({d,sections})=>sections.length&&sections.every(s=>form.sectionRules.some(r=>r.rule==="excluded"&&r.selection[0]===d.code&&r.selection[1]===s.code)));
  const invalid=loading?"正在加载课程…":catalogError?"暂时无法加载课程目录。":!codes.length?"请先选择课程。"
    :badCredit?"学分上下限必须为非负数，且最低值不能高于最高值。"
    :credits<min||credits>max?`已选 ${credits} 学分，允许范围是 ${min}–${max} 学分。`
    :selectedDetails.length<codes.length?"请等候课程详情加载，或重新打开未加载的课程。"
    :badBlock?"请修正自定义禁排时间。起止时间必须不同，结束可填 24:00。"
    :duplicateForce?`${duplicateForce[0]}只能保留一个班次。当前：${duplicateForce[1].join("、")}。`
    :excludedComponent?`${excludedComponent.d.code} 的${componentName(excludedComponent.component)}组件所有班次已被排除。`
    :badBoundary?"请修正上课时间边界。两项均为硬限制时，最早上课须早于最晚下课。"
    :badCount?"目标节数请输入 0–48 的整数。"
    :needsWeeks&&!confirmedWeeks.length?"启用周内规则后，请在「课表结构」中确认至少一个完整教学周。"
    :"";
  const shown=result?.solutions??progress?.preview??[];
  const plan=shown[Math.min(index,shown.length-1)];
  const report=manual?manualReport:plan?.validation;
  const searches=courses.filter(c=>!codes.includes(c.code)&&`${c.code} ${c.name}`.toLowerCase().includes(query.trim().toLowerCase()));

  async function generate(){
    setBusy(true);invalidate();setManual(undefined);
    if(window.matchMedia("(max-width: 950px)").matches)resultsRef.current?.scrollIntoView({block:"start",behavior:"smooth"});
    setIndex(0);
    try{
      const {job_id}=await api<{job_id:string}>("v4/optimize",payload,{"X-Search-Mode":"complete"});
      let nextPreview=performance.now()+10000;
      for(;;){
        const snapshot=await api<Progress>(`v4/progress/${job_id}`);
        const refreshPreview=performance.now()>=nextPreview;
        if(refreshPreview)nextPreview=performance.now()+10000;
        setProgress(previous=>({...snapshot,preview:refreshPreview?snapshot.preview:previous?.preview}));
        if(snapshot.result){setResult(snapshot.result);setIndex(0);break;}
        if(snapshot.state==="failed"||snapshot.state==="timed_out")throw new Error("浏览器搜索未能完成。");
        await new Promise(resolve=>setTimeout(resolve,1000));
      }
    }catch(e){setError(errorText(e));}finally{setBusy(false);}
  }
  async function validateManual(){
    if(!manual||invalid)return;
    setBusy(true);setError("");setManualReport(undefined);
    try{setManualReport(await api<Validation>("v4/validate",{...payload,selections:manual}));}
    catch(e){setError(errorText(e));}finally{setBusy(false);}
  }

  return <main className="v4-planner" lang="zh-CN">
    <header className="v4-header">
      <div><p className="v4-kicker">选课工具 <span>V4</span></p><h1>课表规划</h1></div>
      <label>学期<select value={term} disabled={busy} onChange={e=>changeTerm(e.target.value)}>{terms.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
    </header>
    <div className="v4-meta">
      <span>{settings?.data_source??"学校 SIS 课程快照"}{settings?.last_verified&&` · 最近核验 ${settings.last_verified.replace("T"," ").slice(0,16)}`}</span>
      <span>课表可行性以快照为准。实时余位、先修资格和注册结果请在 SIS 核实。</span>
    </div>
    <div className="v4-workspace">
      <aside className="v4-config" aria-label="排课参数">
        <nav className="v4-modules" aria-label="参数模块">{modules.map(([id,label],i)=><button key={id} aria-current={step===i?"step":undefined} disabled={busy} onClick={()=>setStep(i)}>
          <span aria-hidden="true">{id}</span>{label}
        </button>)}</nav>
        <fieldset className="v4-pane" disabled={busy}>
          <legend className="sr-only">{modules[step][1]}</legend>
          <div className="v4-pane-title"><h2>{modules[step][1]}</h2><p className="muted">{modules[step][2]}</p></div>
          {step===0&&<>
            <section className="v4-form-group"><h3>预选课程</h3>
              <label>搜索课程<input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="输入课程代码或名称"/></label>
              <div className="v4-picker">
                {loading&&<p role="status">正在加载课程…</p>}{catalogError&&<p role="alert">{catalogError}</p>}
                {!loading&&!catalogError&&!searches.length&&<p className="muted">没有匹配的课程。</p>}
                {searches.map(c=><div className="v4-course" key={c.code}>
                  <button className="v4-course-info" onClick={()=>{setView(c.code);void loadDetail(c.code);}}><strong>{c.code}</strong><span>{c.name}</span></button>
                  <span className="muted">{c.credits} 学分</span>
                  <button className="secondary" aria-pressed={codes.includes(c.code)} aria-label={`${codes.includes(c.code)?"移除":"选择"} ${c.code}`} onClick={()=>toggleCourse(c.code)}>{codes.includes(c.code)?"已选":"选择"}</button>
                </div>)}
              </div>
              {!!selected.length&&<ul className="selected">{selected.map(c=><li key={c.code}><button onClick={()=>{setView(c.code);void loadDetail(c.code);}}>{c.code}</button><button aria-label={`移除 ${c.code}`} onClick={()=>toggleCourse(c.code)}>×</button></li>)}</ul>}
              {view&&(detailFor(view)?<CourseDetails detail={detailFor(view)}/>:<p className="muted">等待课程详情…</p>)}
            </section>
            <section className="v4-form-group">
              <h3>学分范围 <span className="v4-inline-total">已选 {credits} 学分</span></h3>
              <div className="v4-row">
                <label>最低学分<input type="number" min={0} step="any" value={form.creditMin} placeholder="12" onChange={e=>update("creditMin",e.target.value)}/></label>
                <label>最高学分<input type="number" min={0} step="any" value={form.creditMax} placeholder="18" onChange={e=>update("creditMax",e.target.value)}/></label>
              </div>
              <p className="muted">留空时分别使用 12 和 18 学分。学分范围只用于校验，课程由你决定。</p>
            </section>
          </>}
          {step===1&&<HardRules key={term} form={form} update={update} details={selectedDetails}/>}
          {step===2&&<TimePreferences form={form} update={update} teachers={teacherNames}/>}
          {step===3&&<Structure form={{...form,weeks:confirmedWeeks}} update={update} weeks={weeks}/>}
          {step===4&&<Weights form={form} update={update}/>}
          {step===5&&<section className="v4-form-group"><h3>搜索与推荐</h3>
            <p>浏览器会搜索到枚举完成。每秒更新计数，评分阶段每 10 秒刷新暂列前三的课表。</p>
          </section>}
          <div className="v4-step-actions">
            {step>0&&<button className="secondary" onClick={()=>setStep(step-1)}>上一步</button>}
            {step<modules.length-1&&<button className="secondary" onClick={()=>setStep(step+1)}>下一步 · {modules[step+1][1]}</button>}
          </div>
        </fieldset>
      </aside>
      <section className="v4-results" ref={resultsRef} aria-label="推荐课表" aria-busy={busy}>
        <div className="v4-result-header">
          <div><h2>推荐课表</h2><p className="muted">{codes.length} 门已选课程 · {credits} 学分</p></div>
          <button className="primary" disabled={busy||!!invalid} aria-describedby="v4-generate-state" onClick={()=>void generate()}>{busy?"处理中…":"生成课表"}</button>
        </div>
        <p id="v4-generate-state" className="muted" aria-live="polite">{busy?"正在处理课表请求…":invalid}</p>
        {busy&&progress&&<div className="notice" role="status" aria-live="polite">
          <strong>{progressPhases[progress.phase]??"正在计算"}</strong>
          <p>本次已找到 {formatCount(progress.schedules_found??0)} 张不同课表</p>
          <p>本次已累计搜索 {progress.branches.toLocaleString()} 个分支</p>
          <p className="muted">每秒读取进度；计数按求解器报告更新。</p>
        </div>}
        {!result&&shown.length>0&&<div>
          <p className="muted">目前分数最高的课表 · 最终名次尚未证明</p>
          <div className="plan-tabs">{shown.map((solution,i)=><button key={i} className="secondary"
            aria-pressed={index===i} onClick={()=>setIndex(i)}>暂列 {i+1}{solution.score!==null?` · ${solution.score.toFixed(1)} 分`:""}</button>)}</div>
        </div>}
        {error&&<p className="notice error" role="alert">{error}</p>}
        {result&&<>
          <p className="notice" role="status">{statuses[result.status]??result.status}。{result.status==="optimal"&&(result.proof_scope==="reference"?"已证明推荐名次。":"已按硬约束和稳定顺序生成。")}</p>
          {!manual&&<p className="muted">返回 {result.solutions.length} 张 · {result.status==="browser_complete"?"已完成枚举":`已证明 ${result.certified_prefix??0} 个名次`} · {((result.elapsed_ms??0)/1000).toFixed(2)} 秒</p>}
          {result.search_summary&&<p className="muted">
            合格课表总数：{result.qualified_schedule_count!=null?formatCount(result.qualified_schedule_count):"未完成统计"}
            {" · "}搜索分支总数：{result.search_summary.branches.toLocaleString()}
          </p>}
          {result.search_summary&&<details className="v4-manual">
            <summary>浏览器搜索统计（诊断信息）</summary>
            <p className="muted">枚举遍历 {result.search_summary.solver_calls} 轮 · 累计分支 {result.search_summary.branches} · 冲突 {result.search_summary.conflicts} · 求解器耗时 {result.search_summary.solver_wall_seconds.toFixed(2)} 秒</p>
            {result.search_model&&<p className="muted">课程评分组合：兼容 {result.search_model.course_patterns_kept} / 原始笛卡尔积 {result.search_model.course_pattern_space}</p>}
            <ul>{result.solver_runs?.map((run,i)=><li key={`${run.phase}-${i}`}>{run.phase}：{run.status}，分支 {run.branches}，冲突 {run.conflicts}，{run.wall_time_seconds.toFixed(2)} 秒</li>)}</ul>
          </details>}
          {result.errors.map(e=><p className="notice error" key={e}>{e}</p>)}
          {!result.solutions.length&&result.warnings?.map(w=><p key={w} className="muted">{w}</p>)}
          <div className="plan-tabs">{result.solutions.map((s,i)=><button key={i} className="secondary" disabled={busy} aria-pressed={i===index&&!manual} onClick={()=>{setIndex(i);setManual(undefined);}}>{(s.proven||result.status==="browser_complete")?`方案 ${i+1}`:`可行方案 ${i+1} · 名次未证`}{s.score!==null?` · ${s.score.toFixed(1)} 分`:""}</button>)}</div>
        </>}
        {(plan||manual)&&<div className="plan-tabs">
          <button className="secondary" disabled={busy} onClick={()=>{setManual(manual?undefined:(plan?.selections??[]));setManualReport(undefined);}}>{manual?"返回推荐":"手动调班"}</button>
          {manual&&<button className="secondary" disabled={busy||!!invalid} onClick={()=>void validateManual()}>检验课表</button>}
          {report?.passed&&<button className="secondary" onClick={()=>download(JSON.stringify({version:"V4",request:payload,section_rules:form.sectionRules,solution:manual?{selections:manual,validation:report}:plan},null,2),"schedule-v4.json","application/json")}>导出方案</button>}
        </div>}
        {manual&&selectedDetails.map(course=><details className="v4-manual" key={course.code} open>
          <summary>{course.code} · {course.name}</summary>
          {course.required.map(component=>{
            const options=course.sections.filter(s=>s.component===component);
            const fixed=form.sectionRules.find(r=>r.rule!=="excluded"&&r.selection[0]===course.code&&options.some(s=>s.code===r.selection[1]));
            const current=manual.find(([c,s])=>c===course.code&&options.some(item=>item.code===s));
            return <label key={component}>{componentName(component)}{fixed&&` · ${ruleNames[fixed.rule]}`}
              <select disabled={!!fixed||busy} value={current?.[1]??""} onChange={e=>{
                const next=manual.filter(([c,s])=>c!==course.code||!options.some(item=>item.code===s));
                if(e.target.value)next.push([course.code,e.target.value]);
                setManual(next);setManualReport(undefined);
              }}><option value="">请选择班次</option>{options.filter(s=>!form.sectionRules.some(r=>r.rule==="excluded"&&r.selection[0]===course.code&&r.selection[1]===s.code)).map(s=><option key={s.code} value={s.code}>{s.code} · {s.teachers.join(" / ")||"教师待定"}</option>)}</select>
            </label>;
          })}
        </details>)}
        {!!plan&&!manual&&<ul className="v4-selected-sections">{plan.selections.map(([code,sec])=>{
          const rule=form.sectionRules.find(r=>r.selection[0]===code&&r.selection[1]===sec);
          return <li key={`${code}/${sec}`} data-protected={!!rule}>{code} {sec}{rule&&` · ${ruleNames[rule.rule]}`}</li>;
        })}</ul>}
        {report&&<details open={!report.passed}>
          <summary>{report.passed?"独立可行性检验通过":"查看检验问题"}</summary>
          <ul className="details-list">{[...report.errors,...report.warnings].map(w=><li key={w}>{w}</li>)}</ul>
        </details>}
        {report?.passed?<Calendar meetings={report.meetings} empty="所选教学周没有课程。"/>:
          <div className="v4-empty"><div className="v4-calendar-icon" aria-hidden="true"><span/><span/><span/><span/><span/><span/></div><h3>{result&&!result.solutions.length?"本次没有可显示的方案":manual?"检验调班后的课表":"等待生成课表"}</h3><p className="muted">{result&&!result.solutions.length?"请查看上方的搜索状态和提示。":manual?"通过独立检验后，这里会显示调班结果。":"选择课程并按需设置约束，然后点击「生成课表」。"}</p></div>}
        {!!plan&&!manual&&<details className="v4-explanation"><summary>评分与安排依据</summary>
          {plan.score===null&&<p className="muted">此次方案没有可显示的偏好匹配分。</p>}
          <dl>{(Object.entries(plan.breakdown) as [Category,number][]).map(([key,loss])=><div key={key}><dt>{categories[key]}</dt><dd>损失 {(loss*100).toFixed(1)}% · 重要性 {form.weights[key]??3}</dd></div>)}</dl>
          {report?.metrics&&<div className="v4-metrics">
            <p>08:30 开始的课程 {report.metrics.early_sessions} 节 · 课间总空档 {report.metrics.gap_minutes} 分钟</p>
            {report.metrics.unknown_teacher_sessions>0&&<p>教师待定 {report.metrics.unknown_teacher_sessions} 节 · 按中立处理</p>}
            {periods.map(k=>{const value=report.metrics?.period_counts[k];return value&&<p key={k}>{periodNames[k]}节数规则：{value.applicable_days?`${value.matching_days} / ${value.applicable_days} 天达标`:"不适用（该时段无课）"}</p>;})}
            {Object.entries(report.metrics.weeks).map(([day,row])=><p key={day}>{day} 起 · 周一至周五有 {row.free_weekdays} 个无课日</p>)}
          </div>}
        </details>}
      </section>
    </div>
  </main>;
}
