import {useState} from "react";
import {clock,type Detail} from "./api";
import {blockLabel,categories,periodNames,periods,slots,weekdays,type BlockRule,type Category,type Form,type Mode,type Rule} from "./v4-form";

const levels=["完全避免","倾向避免","中立","比较喜欢","强烈喜欢"];
const importance=["较低","偏低","中等","偏高","非常重要"];
const blockNames={all:"全天",morning:"上午",afternoon:"下午",evening:"晚上",custom:"自定义"};
export const ruleNames={required:"必须选",locked:"已选上 · 锁定",excluded:"排除"};
export const componentName=(name:string)=>({LEC:"讲课",TUT:"辅导课",LAB:"实验课",SEM:"研讨课"}[name]??name);
type Update = <K extends keyof Form>(field:K,value:Form[K])=>void;
type Props={form:Form;update:Update};

function Rating({label,value,onChange,weight=false}:{label:string;value:number;onChange:(n:number)=>void;weight?:boolean}) {
  return <label>{label}<select value={value} onChange={e=>onChange(Number(e.target.value))}>
    {(weight?importance:levels).map((name,i)=><option key={name} value={i+1}>{i+1} · {name}</option>)}
  </select></label>;
}

function Toggle({label,checked,onChange}:{label:string;checked:boolean;onChange:(v:boolean)=>void}) {
  return <label className="v4-check"><input type="checkbox" checked={checked} onChange={e=>onChange(e.target.checked)}/>{label}</label>;
}

function ModeSelect({label,value,onChange,free=false}:{label:string;value:Mode;onChange:(v:Mode)=>void;free?:boolean}) {
  return <label>{label}<select value={value} onChange={e=>onChange(e.target.value as Mode)}>
    <option value="">不启用</option><option value="soft">{free?"尽量达到":"尽量满足"}</option>
    <option value="hard">{free?"必须达到":"必须遵守"}</option>
  </select></label>;
}

export function HardRules({form,update,details}:Props&{details:Detail[]}) {
  const [filter,setFilter]=useState("");
  const [chosen,setChosen]=useState<string[]>([]);
  const [action,setAction]=useState<Rule>("required");
  const [reason,setReason]=useState("已满");
  const sections=details.flatMap(d=>d.sections.map(s=>({course:d.code,section:s,id:JSON.stringify([d.code,s.code])})));
  const matches=sections.filter(({course,section})=>`${course} ${section.code} ${section.component} ${section.teachers.join(" ")}`.toLowerCase().includes(filter.trim().toLowerCase()));
  const targets=sections.filter(item=>chosen.includes(item.id));
  function applyRules(){
    const keys=new Set(targets.map(item=>item.id));
    update("sectionRules",[
      ...form.sectionRules.filter(item=>!keys.has(JSON.stringify(item.selection))),
      ...targets.map(({course,section})=>({selection:[course,section.code] as [string,string],rule:action,reason:action==="excluded"?reason:""})),
    ]);
    setChosen([]);
  }
  return <>
    <section className="v4-form-group">
      <h3>统一禁排时段</h3><p className="muted">选择星期与时段。全天、预设时段和自定义时间都会按实际教学日期检查。</p>
      {form.blocks.map((rule,i)=>{
        const edit=(patch:Partial<BlockRule>)=>update("blocks",form.blocks.map((r,j)=>i===j?{...r,...patch}:r));
        return <div className="v4-block" key={i}>
          <label>星期<select value={rule.day} onChange={e=>edit({day:Number(e.target.value)})}>{weekdays.map((name,j)=><option key={name} value={j+1}>{name}</option>)}</select></label>
          <label>禁排范围<select value={rule.kind} onChange={e=>edit({kind:e.target.value as BlockRule["kind"]})}>{Object.entries(blockNames).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
          {rule.kind==="custom"?<>
            <label>开始<input value={rule.start} placeholder="14:30" onChange={e=>edit({start:e.target.value})}/></label>
            <label>结束<input value={rule.end} placeholder="17:00 或 24:00" onChange={e=>edit({end:e.target.value})}/></label>
          </>:<span className="v4-time">{blockLabel(rule)}</span>}
          <button className="secondary" aria-label={`移除第 ${i+1} 条禁排规则`} onClick={()=>update("blocks",form.blocks.filter((_,j)=>i!==j))}>移除</button>
          {rule.kind==="custom"&&blockLabel(rule)&&<p className="v4-full muted">{blockLabel(rule)}</p>}
        </div>;
      })}
      <button className="secondary" disabled={form.blocks.length>=100} onClick={()=>update("blocks",[...form.blocks,{day:1,kind:"all",start:"14:30",end:"17:00"}])}>添加禁排时段</button>
    </section>
    <section className="v4-form-group">
      <h3>班次要求与排除</h3><p className="muted">必须选表示本次排课要保留该班次。已选上锁定表示已有选课进度，后续方案会保留它。</p>
      {sections.length>0&&<>
        <label>搜索已选课程的班次<input type="search" value={filter} onChange={e=>setFilter(e.target.value)} placeholder="课程代码、班次或教师"/></label>
        <div className="v4-picker">
          {matches.map(({course,section,id})=><Toggle key={id} label={`${course} · ${section.code} · ${componentName(section.component)} · ${section.teachers.join(" / ")||"教师待定"}`}
            checked={chosen.includes(id)} onChange={v=>setChosen(v?[...chosen,id]:chosen.filter(k=>k!==id))}/>)}
          {!matches.length&&<p className="muted">没有匹配的班次。</p>}
        </div>
        <div className="v4-row">
          <label>批量设置<select value={action} onChange={e=>setAction(e.target.value as Rule)}>{Object.entries(ruleNames).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
          {action==="excluded"&&<label>排除原因<select value={reason} onChange={e=>setReason(e.target.value)}><option>已满</option><option>不喜欢教师</option><option>其他</option><option value="">不记录</option></select></label>}
          <button className="secondary" disabled={!targets.length} onClick={applyRules}>应用到 {targets.length} 个班次</button>
        </div>
      </>}
      {!sections.length&&<p className="muted">选择课程后可设置其班次。</p>}
      {form.sectionRules.length>0&&<ul className="v4-rule-list">{form.sectionRules.map((r,i)=><li key={r.selection.join("/")}>
        <span><strong>{r.selection.join(" ")}</strong> · {ruleNames[r.rule]}{r.reason&&`（${r.reason}）`}</span>
        <button className="secondary" onClick={()=>update("sectionRules",form.sectionRules.filter((_,j)=>i!==j))}>撤销</button>
      </li>)}</ul>}
    </section>
  </>;
}

export function TimePreferences({form,update,teachers}:Props&{teachers:string[]}) {
  const [search,setSearch]=useState("");
  const found=teachers.filter(name=>name.toLowerCase().includes(search.trim().toLowerCase()));
  return <>
    <section className="v4-form-group"><h3>上课时间边界</h3>
      {(["earliest","latest"] as const).map((k)=><div className="v4-row" key={k}>
        <ModeSelect label={k==="earliest"?"最早上课":"最晚下课"} value={form[k].mode} onChange={mode=>update(k,{...form[k],mode})}/>
        {form[k].mode&&<label>{k==="earliest"?"开始下限":"结束上限"}<input value={form[k].time} placeholder={k==="earliest"?"08:30":"18:00"} onChange={e=>update(k,{...form[k],time:e.target.value})}/></label>}
      </div>)}
    </section>
    <section className="v4-form-group"><h3>喜好等级</h3><p className="muted">评分 1 仍允许该安排。必须避开的时间请加入禁排。</p>
      <Toggle label="启用早八偏好（08:30 开始）" checked={!!form.early} onChange={v=>update("early",v?3:0)}/>
      {!!form.early&&<Rating label="早八喜好" value={form.early} onChange={v=>update("early",v)}/>}
      <Toggle label="启用分时段偏好" checked={form.ratePeriods} onChange={v=>update("ratePeriods",v)}/>
      {form.ratePeriods&&<div className="v4-grid-three">{periods.map(k=><div key={k}><Rating label={periodNames[k]} value={form.periods[k]??3} onChange={v=>update("periods",{...form.periods,[k]:v})}/><small className="muted">{slots[k].map(clock).join("–")}</small></div>)}</div>}
      <Toggle label="启用星期偏好" checked={form.rateWeekdays} onChange={v=>update("rateWeekdays",v)}/>
      {form.rateWeekdays&&<><div className="v4-week-ratings">{weekdays.map((d,i)=><div key={d}>
        <Rating label={d} value={form.weekdays[i+1]??3} onChange={v=>update("weekdays",{...form.weekdays,[i+1]:v})}/>
        <button className="v4-text-button" disabled={form.blocks.length>=100||form.blocks.some(b=>b.day===i+1&&b.kind==="all")} onClick={()=>update("blocks",[...form.blocks,{day:i+1,kind:"all",start:"00:00",end:"24:00"}])}>{form.blocks.some(b=>b.day===i+1&&b.kind==="all")?"已禁排全天":"禁排全天"}</button>
      </div>)}</div><button className="secondary" onClick={()=>update("weekdays",{})}>恢复中立</button></>}
    </section>
    <section className="v4-form-group"><h3>教师偏好</h3>
      <Toggle label="启用教师评分" checked={form.rateTeachers} onChange={v=>update("rateTeachers",v)}/>
      {form.rateTeachers&&<>
        <label>搜索教师<input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="输入教师姓名"/></label>
        <div className="v4-picker">{found.map(t=><Rating key={t} label={t} value={form.teachers[t]??3} onChange={n=>update("teachers",{...form.teachers,[t]:n})}/>)}{!found.length&&<p className="muted">{teachers.length?"没有匹配的教师。":"已选课程暂无可评分教师。"}</p>}</div>
        {teachers.some(t=>form.teachers[t]&&form.teachers[t]!==3)&&<p className="muted">已评分：{teachers.filter(t=>form.teachers[t]&&form.teachers[t]!==3).map(t=>`${t} ${form.teachers[t]} 分`).join("、")}</p>}
        <p className="muted">未评分和未知教师按 3 分中立处理。</p>
      </>}
    </section>
  </>;
}

export function Structure({form,update,weeks}:Props&{weeks:string[]}) {
  const needWeeks=!!form.distribution||(!!form.freeMode&&form.freeDays>0);
  return <>
    <section className="v4-form-group"><h3>课间空档</h3>
      <div className="v4-mode-grid">{[["","不启用",""],["compact","紧凑","偏好短间隔"],["balanced","均衡","偏好适度间隔"],["spacious","宽松","偏好较长间隔"]].map(([k,name,desc])=>
        <button key={k} className="v4-mode" aria-pressed={form.gaps===k} onClick={()=>update("gaps",k)}><strong>{name}</strong>{desc&&<small>{desc}</small>}</button>)}</div>
    </section>
    <section className="v4-form-group"><h3>时段内课程数量</h3><p className="muted">按每个教学日的实际节次统计。该时段没有课时，结果显示不适用。</p>
      {periods.map(k=><div className="v4-row" key={k}>
        <label>{periodNames[k]}节数规则<select value={form.counts[k].comparison} onChange={e=>update("counts",{...form.counts,[k]:{...form.counts[k],comparison:e.target.value as Form["counts"][typeof k]["comparison"]}})}>
          <option value="">不启用</option><option value="exactly">恰好</option><option value="at_most">不超过</option><option value="at_least">不少于</option>
        </select></label>
        {form.counts[k].comparison&&<label>目标节数<input type="number" min={0} max={48} step={1} value={form.counts[k].target} onChange={e=>update("counts",{...form.counts,[k]:{...form.counts[k],target:e.target.value}})}/></label>}
      </div>)}
    </section>
    <section className="v4-form-group"><h3>周内分布</h3>
      <div className="v4-mode-grid">{[["","不启用",[]],["concentrated","集中",[3,3,0,0,0]],["distributed","分散",[1,1,1,1,1]]].map(([value,label,bars])=><button key={String(value)} className="v4-mode" aria-pressed={form.distribution===value} onClick={()=>update("distribution",String(value))}>
        <strong>{label}</strong>{Array.isArray(bars)&&bars.length>0&&<span className="v4-week-demo" aria-label={`${label}模式示意，周一到周五`}>{bars.map((n,i)=><span key={i} title={weekdays[i]} style={{height:`${4+Number(n)*7}px`}}/>)}</span>}
      </button>)}</div>
      <div className="v4-row">
        <ModeSelect label="目标无课天数" free value={form.freeMode} onChange={v=>update("freeMode",v)}/>
        {form.freeMode&&<label>每周至少无课<select value={form.freeDays} onChange={e=>update("freeDays",Number(e.target.value))}>{Array.from({length:6},(_,i)=><option key={i} value={i}>{i} 天</option>)}</select></label>}
      </div>
      <p className="muted">无课日只统计周一至周五。</p>
      {needWeeks&&<div className="v4-calendar-pick">
        <h4>确认完整教学周</h4><p className="muted">下方日期按所选课程的教学跨度列出。请根据学校校历勾选完整教学周，排除假期与不完整的周。</p>
        <div className="v4-picker v4-week-pick">{weeks.map(w=><Toggle key={w} label={`${w} 起`} checked={form.weeks.includes(w)} onChange={v=>update("weeks",v?[...form.weeks,w].sort():form.weeks.filter(d=>d!==w))}/>)}{!weeks.length&&<p className="muted">选择含教学日期的课程后即可确认。</p>}</div>
      </div>}
    </section>
  </>;
}

export function Weights({form,update}:Props) {
  return <section className="v4-form-group"><h3>类别重要性</h3><p className="muted">启用的类别默认同等重要。关闭类别只停止软偏好计分，硬约束仍然生效。</p>
    {(Object.keys(categories) as Category[]).map(k=><div className="v4-weight" key={k}>
      <Toggle label={`${categories[k]}参与评分`} checked={!form.disabled.includes(k)} onChange={v=>update("disabled",v?form.disabled.filter(x=>x!==k):[...form.disabled,k])}/>
      {!form.disabled.includes(k)&&<Rating weight label={`${categories[k]}重要性`} value={form.weights[k]??3} onChange={v=>update("weights",{...form.weights,[k]:v})}/>}
    </div>)}
  </section>;
}
