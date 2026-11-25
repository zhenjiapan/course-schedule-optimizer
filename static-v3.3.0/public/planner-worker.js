const periods = {morning:[0,720], afternoon:[720,1080], evening:[1080,1440]};
const ms = 86400000;
const weekday = day => ((new Date(day).getUTCDay()+6)%7)+1;
const plusDay = (day,i) => new Date(Date.parse(day)+i*ms).toISOString().slice(0,10);
const overlap = (a,b,c,d) => Math.max(0,Math.min(b,d)-Math.max(a,c));
const key = (course,section) => JSON.stringify([course,section]);
const order = (a,b) => a < b ? -1 : a > b ? 1 : 0;
const average = numbers => numbers.reduce((sum,value)=>sum+value,0)/numbers.length;
const close = (a,b) => Math.abs(a-b) <= 1e-12;

function events(section) {
  const unique = new Map();
  for (const meeting of section.meetings) {
    const dates = meeting.occurrences ?? [];
    if (meeting.occurrences == null) {
      for(let t=Date.parse(meeting.first); t<=Date.parse(meeting.last);t+=ms) {
        const day = new Date(t).toISOString().slice(0,10);
        if(weekday(day)===meeting.weekday) dates.push(day);
      }
    }
    for(const day of dates) {
      const id = JSON.stringify([day,meeting.start,meeting.end]);
      if(!unique.has(id)) unique.set(id,{day,a:meeting.start,b:meeting.end,names:new Set()});
      for(const name of meeting.teachers) unique.get(id).names.add(name);
    }
  }
  return [...unique.values()].sort((x,y)=>order(x.day,y.day)||x.a-y.a||x.b-y.b);
}

function model(details,p) {
  const blocks=p.blocked.flatMap(([w,a,b])=>a<b?[[w,a,b]]:[[w,a,1440],[w%7+1,0,b]]);
  const fixed = new Set([...p.required,...p.locked].map(pair=>key(...pair)));
  const excluded = new Set(p.excluded.map(pair=>key(...pair)));
  const groups=[], all=new Map(), days=new Set(), warnings=details.flatMap(d=>d.warnings);
  const weeks=[...p.teaching_weeks].sort();
  const credits=details.reduce((n,d)=>n+d.credits,0);
  const forbidden = ({day,a,b}) => blocks.some(([w,x,y])=>w===weekday(day)&&overlap(a,b,x,y))
    || (p.earliest?.mode==="hard"&&a<p.earliest.minute) || (p.latest?.mode==="hard"&&b>p.latest.minute);
  const fail=(status,message)=>{throw Object.assign(new Error(message),{status});};
  if(credits+1e-9<Number(p.credit_min)||credits-1e-9>Number(p.credit_max)) fail("infeasible_proven","所选课程学分不在指定范围内。");
  if(!weeks.length && ((!p.disabled.includes("B") && (p.distribution || p.free_days?.mode==="soft"&&p.free_days.minimum))
      || (p.free_days?.mode==="hard"&&p.free_days.minimum))) fail("insufficient_data","请先确认完整教学周。");
  for(const d of details) {
    if(!d.required.length) fail("insufficient_data",d.code+" 的必修组件未知。");
    for(const s of d.sections) {
      const records=events(s), id=key(d.code,s.code);
      all.set(id,{d,s,id,records});
      for(const {day} of records) days.add(day);
    }
    if(d.required.includes("LEC")&&d.required.includes("TUT")&&!Object.keys(d.bindings).length)
      warnings.push(d.code+" 的 Lecture/Tutorial 配对未经核验。");
  }
  for(const id of [...fixed,...excluded]) if(!all.has(id)) fail("invalid","所指定的班次不存在。");
  for(const id of fixed) if(excluded.has(id)) fail("infeasible_proven","同一班次同时被要求保留和排除。");
  if([...all.values()].some(({s})=>s.meetings.some(m=>m.occurrences==null)))
    warnings.push("缺少独立授课日期的会议，按目录的星期和日期范围展开。");
  if(p.gaps||Object.keys(p.counts).length) warnings.push("日结构按所有候选班次上课日期的并集计算。");

  for(const d of details) for(const component of d.required) {
    const options=[...all.values()].filter(x=>x.d===d&&x.s.component===component&&x.records.length);
    if(!options.length) fail("insufficient_data",d.code+" 缺少可用的 "+component+" 班次。");
    const requested=options.filter(x=>fixed.has(x.id));
    const eligible=(requested.length?requested:options).filter(x=>!excluded.has(x.id)&&!x.records.some(forbidden)
      && !x.records.some(({day,a},i)=>i>0&&x.records[i-1].day===day&&x.records[i-1].b>a));
    if(requested.length>1||!eligible.length) fail("infeasible_proven",d.code+" 的 "+component+" 无法满足班次限制。");
    groups.push(eligible);
  }
  if([...fixed].some(id=>!groups.some(group=>group.some(x=>x.id===id)))) fail("infeasible_proven","指定保留的班次无法排入课表。");

  function bindingConflict(x,y) {
    if(x.d!==y.d) return false;
    if(x.s.component==="TUT") [x,y]=[y,x];
    return x.s.component==="LEC"&&y.s.component==="TUT"&&Object.keys(x.d.bindings).length>0
      && !(x.d.bindings[x.s.code]??[]).includes(y.s.code);
  }
  const edges=new Map(), dateRows=new Map();
  const connect=(x,y)=>{
    if(x===y)return;
    edges.get(x).add(y);
    edges.get(y).add(x);
  };
  const live=groups.flat();
  for(const x of live) edges.set(x.id,new Set());
  for(const x of live) {
    for(const {day,a,b} of x.records){
      if(!dateRows.has(day))dateRows.set(day,[]);
      dateRows.get(day).push({a,b,id:x.id});
    }
  }
  for(const rows of dateRows.values()){
    const active=[];
    for(const row of rows.sort((x,y)=>x.a-y.a)){
      for(let i=active.length-1;i>=0;i--){
        if(active[i].b<=row.a)active.splice(i,1);
        else connect(active[i].id,row.id);
      }
      active.push(row);
    }
  }
  for(let i=0;i<live.length;i++)for(let j=i+1;j<live.length;j++)if(bindingConflict(live[i],live[j]))connect(live[i].id,live[j].id);
  for(;;){
    const forced=groups.filter(g=>g.length===1).map(g=>g[0].id);
    const forbiddenIds=new Set(forced.flatMap(id=>[...edges.get(id)]));
    let changed=false;
    for(let i=0;i<groups.length;i++){
      const filtered=groups[i].filter(x=>!forbiddenIds.has(x.id));
      if(!filtered.length)fail("infeasible_proven","固定班次之间存在时间或组件配对冲突。");
      changed ||= filtered.length!==groups[i].length;
      groups[i]=filtered;
    }
    if(!changed)break;
  }
  const surviving=new Set(groups.flat().map(x=>x.id));
  const span=day=>{
    const rows=(dateRows.get(day)??[]).filter(row=>surviving.has(row.id));
    return rows.length?Math.max(...rows.map(r=>r.b))-Math.min(...rows.map(r=>r.a)):0;
  };
  const dateList=[...days].sort(), gapBound=dateList.reduce((n,d)=>n+span(d),0);
  const weekBounds=new Map(weeks.map(w=>[w,Math.max(1,...Array.from({length:5},(_,i)=>span(plusDay(w,i))))]));
  groups.sort((a,b)=>a.length-b.length);
  return {details,p,all,groups,edges,weeks,dateList,gapBound,weekBounds,credits,warnings,forbidden,bindingConflict,fixed,excluded};
}

function audit(m,chosen) {
  const errors=[], days=new Map(), lessons=new Map();
  const ids=new Set(chosen.map(x=>x.id));
  if(ids.size!==chosen.length)errors.push("存在重复班次。");
  for(const id of m.fixed)if(!ids.has(id))errors.push("遗漏必选或锁定班次。");
  for(const d of m.details){
    const selected=chosen.filter(x=>x.d===d);
    if(selected.length!==d.required.length||d.required.some(component=>selected.filter(x=>x.s.component===component).length!==1))
      errors.push(d.code+" 的组件选择不完整或重复。");
    if(selected.some(x=>selected.some(y=>m.bindingConflict(x,y))))errors.push(d.code+" 的 Lecture/Tutorial 配对不符。");
    lessons.set(d.code,[]);
    for(const x of selected){
      if(m.excluded.has(x.id))errors.push("选择了已排除班次。");
      if(!x.records.length)errors.push("班次没有有效上课日期。");
      for(const row of x.records){
        if(m.forbidden(row))errors.push(d.code+" 有班次违反禁排或时间边界。");
        if(!days.has(row.day))days.set(row.day,[]);
        const today=days.get(row.day);
        if(today.some(r=>overlap(row.a,row.b,r.a,r.b)))errors.push(row.day+" 存在上课时间冲突。");
        today.push(row);
        lessons.get(d.code).push(row);
      }
    }
  }
  const weeks={};
  for(const week of m.weeks){
    const load_minutes=Array.from({length:5},(_,i)=>(days.get(plusDay(week,i))??[]).reduce((sum,r)=>sum+r.b-r.a,0));
    const free_weekdays=load_minutes.filter(n=>!n).length;
    weeks[week]={load_minutes,free_weekdays};
    if(m.p.free_days?.mode==="hard"&&free_weekdays<m.p.free_days.minimum)errors.push(week+" 所在周没有足够的空闲工作日。");
  }
  return {errors:[...new Set(errors)],days,lessons,weeks};
}

function factors(m,checked) {
  const {p,dateList}=m, {days,lessons,weeks}=checked;
  const raw={}, add=(k,v)=>{raw[k]=(raw[k]??0)+v;};
  let early_sessions=0,unknown_teacher_sessions=0,gap_count=0,gap_minutes=0,extra=0;
  for(const records of lessons.values()){
    const minutes=records.reduce((n,r)=>n+r.b-r.a,0);
    for(const {day,a,b,names} of records){
      const duration=(b-a)/minutes/lessons.size, n=records.length*lessons.size;
      const rating=names.size?average([...names].map(name=>p.teachers[name]??3)):3;
      add("T",(5-rating)*duration/4);
      add("W",((p.weekdays[weekday(day)]??3)-3)*duration/2);
      for(const [period,[lo,hi]] of Object.entries(periods))
        add("periods",((p.periods[period]??3)-3)*overlap(a,b,lo,hi)/minutes/lessons.size/2);
      const early=p.early??3;
      add("early",(a===510?Math.max(0,3-early):Math.max(0,early-3))/2/n);
      if(p.earliest?.mode==="soft")add("earliest",Math.min(60,Math.max(0,p.earliest.minute-a))/60/n);
      if(p.latest?.mode==="soft")add("latest",Math.min(60,Math.max(0,b-p.latest.minute))/60/n);
      if(a===510)early_sessions++;
      if(!names.size)unknown_teacher_sessions++;
    }
  }
  const period_counts=Object.fromEntries(Object.keys(p.counts).map(name=>[name,{applicable_days:0,matching_days:0}]));
  for(const day of dateList){
    const rows=(days.get(day)??[]).sort((x,y)=>x.a-y.a||x.b-y.b);
    const gaps=rows.slice(1).map((r,i)=>r.a-rows[i].b);
    gap_count+=gaps.length;
    gap_minutes+=gaps.reduce((n,g)=>n+g,0);
    extra+=gaps.reduce((n,g)=>n+Math.max(g-10,0),0);
    if(p.gaps==="balanced"||p.gaps==="spacious")
      add("gaps",(gaps.length?average(gaps.map(g=>p.gaps==="balanced"
        ? Math.min(1,Math.max(10-g,g-40,0)/60) : Math.max(0,1-g/60))):0.5)/dateList.length);
    for(const [name,rule] of Object.entries(p.counts)){
      const [lo,hi]=periods[name], count=rows.filter(r=>r.a>=lo&&r.a<hi).length;
      if(!count)continue;
      const delta=count-rule.target;
      const error=rule.comparison==="exactly"?Math.abs(delta):rule.comparison==="at_most"?Math.max(delta,0):Math.max(-delta,0);
      add("count:"+name,Math.min(1,error/(rule.tolerance??2))/dateList.length);
      period_counts[name].applicable_days++;
      if(!error)period_counts[name].matching_days++;
    }
  }
  if(p.gaps==="compact"){
    const cap=30*dateList.length;
    const penalty=n=>10*Math.min(n,cap)+Math.max(0,n-cap);
    if(m.gapBound)add("gaps",penalty(extra)/penalty(m.gapBound));
  }
  for(const [week,{load_minutes,free_weekdays}] of Object.entries(weeks)){
    const active=load_minutes.filter(Boolean), k=active.length;
    const q=p.free_days?.mode==="soft"?p.free_days.minimum:0;
    const short=q?Math.max(0,q-free_weekdays)/q:0;
    let loss=short;
    if(p.distribution==="concentrated")loss=q?0.75*short+k/20:k?(k-1)/4:0.5;
    if(p.distribution==="distributed"){
      const differences=active.flatMap((a,i)=>active.slice(i+1).map(b=>Math.abs(a-b)));
      const balance=differences.length?average(differences)/m.weekBounds.get(week):0.5;
      const spread=k?0.85*(5-k)/4+0.15*balance:0.5;
      loss=q?(spread+short)/2:spread;
    }
    add("B",loss/m.weeks.length);
  }
  return {raw,metrics:{early_sessions,unknown_teacher_sessions,gap_count,gap_minutes,period_counts,weeks}};
}

function validation(m,chosen,checked=factorsCheck(m,chosen)) {
  const {auditResult,metrics}=checked;
  return {passed:!auditResult.errors.length, errors:auditResult.errors,warnings:m.warnings,metrics,
    meetings:auditResult.errors.length?[]:chosen.flatMap(({d,s})=>s.meetings.map(meeting=>({...meeting,course:d.code,section:s.code,component:s.component,name:d.name})))};
}

function factorsCheck(m,chosen) {
  const auditResult=audit(m,chosen);
  return {auditResult,...(auditResult.errors.length?{}:factors(m,auditResult))};
}

function solve(m,jobId) {
  const time=performance.now(), p=m.p;
  let branches=0, count=0n, stage="preference_calibration", last=0, leaders=[];
  let conflicts=0;
  const started=()=>performance.now()-time;
  const progress=()=>{
    if(started()-last<300)return;
    last=started();
    self.postMessage({job_id:jobId,state:"running",phase:stage,branches,current_branches:branches,conflicts,solver_run:1,schedules_found:String(count),preview:leaders});
  };
  const walk=(visit,depth=0,chosen=[])=>{
    if(depth===m.groups.length){
      const check=factorsCheck(m,chosen);
      if(!check.auditResult.errors.length)visit(chosen,check);
      return;
    }
    for(const x of m.groups[depth]){
      branches++;
      if(branches%256===0)progress();
      if(chosen.some(y=>m.edges.get(x.id).has(y.id))){conflicts++;continue;}
      chosen.push(x);walk(visit,depth+1,chosen);chosen.pop();
    }
  };
  const configured={
    T:[["T"]], W:[["W"]], H:[["early"],["periods"],["earliest","latest"]],
    D:[["gaps"],Object.keys(p.counts).map(k=>"count:"+k)], B:[["B"]],
  };
  const entries=Object.entries(configured).filter(([c])=>!p.disabled.includes(c));
  const extremes=new Map(entries.flatMap(([,stages])=>stages.flat()).map(k=>[k,[Infinity,-Infinity]]));
  walk((chosen,{raw})=>{
    count++;
    for(const [k,bounds] of extremes){const x=raw[k]??0;bounds[0]=Math.min(bounds[0],x);bounds[1]=Math.max(bounds[1],x);}
    progress();
  });
  const summary=()=>({solver_calls:count?2:1,branches,conflicts,solver_wall_seconds:started()/1000});
  if(!count)return {status:"infeasible_proven",solutions:[],warnings:m.warnings,errors:["所有候选组合均无法满足硬约束。"],qualified_schedule_count:"0",search_summary:summary(),elapsed_ms:started()};
  const active=entries.map(([category,stages])=>[category,stages.map(stage=>stage.filter(k=>!close(...extremes.get(k)))).filter(stage=>stage.length)]).filter(([,stages])=>stages.length);
  const factor=(k,x)=>{
    if(k!=="W"&&k!=="periods")return x;
    const [lo,hi]=extremes.get(k);return (hi-x)/Math.max(1,hi-lo);
  };
  const categoryBounds=new Map(active.map(([category])=>[category,[Infinity,-Infinity]]));
  const weight=c=>p.weights[c]??3;
  const lossFor=breakdown=>Object.entries(breakdown).reduce((n,[c,v])=>n+weight(c)*v,0);
  stage="top_k_ranking";
  walk((chosen,checked)=>{
    const breakdown=Object.fromEntries(active.map(([c,stages])=>[c,average(stages.map(stage=>average(stage.map(k=>factor(k,checked.raw[k]??0)))))]));
    for(const [c,v] of Object.entries(breakdown)){
      const bounds=categoryBounds.get(c);
      bounds[0]=Math.min(bounds[0],v);bounds[1]=Math.max(bounds[1],v);
    }
    const selections=chosen.map(x=>[x.d.code,x.s.code]).sort((a,b)=>order(a[0],b[0])||order(a[1],b[1]));
    const loss=lossFor(breakdown);
    const cmp=(a,b)=>close(a.loss,b.loss)?order(JSON.stringify(a.selections),JSON.stringify(b.selections)):a.loss-b.loss;
    if(leaders.length<3||cmp({loss,selections},leaders[2])<0){
      const total=active.reduce((n,[c])=>n+weight(c),0);
      leaders.push({loss,selections,breakdown,score:total?100*(1-loss/total):null,validation:validation(m,chosen,checked),proven:false});
      leaders.sort(cmp);leaders=leaders.slice(0,3);
    }
    progress();
  });
  for(const row of leaders){
    for(const [category,bounds] of categoryBounds)if(close(...bounds))delete row.breakdown[category];
    const total=Object.keys(row.breakdown).reduce((n,c)=>n+weight(c),0);
    row.score=total?100*(1-lossFor(row.breakdown)/total):null;
    row.proven=false;
    delete row.loss;
  }
  return {status:"browser_complete",solutions:leaders,warnings:m.warnings,errors:[],qualified_schedule_count:String(count),
    search_summary:summary(),elapsed_ms:started(),certified_prefix:0};
}

self.onmessage=({data})=>{
  const {jobId,details,preferences,selections}=data;
  try{
    const m=model(details,preferences);
    if(selections){
      const chosen=selections.map(pair=>m.all.get(key(...pair)));
      const result=chosen.some(x=>!x)?{passed:false,errors:["包含未知班次。"],warnings:m.warnings,meetings:[]}:validation(m,chosen);
      self.postMessage({job_id:jobId,validation:result});
    }else{
      const result=solve(m,jobId);
      self.postMessage({job_id:jobId,state:"completed",phase:"completed",branches:result.search_summary.branches,result});
    }
  }catch(error){
    const errors=[error.message||"浏览器求解失败。"];
    if(selections)self.postMessage({job_id:jobId,validation:{passed:false,errors,warnings:[],meetings:[]}});
    else self.postMessage({job_id:jobId,state:"completed",phase:"completed",branches:0,result:{
      status:error.status??"internal_error",solutions:[],warnings:[],errors,
      qualified_schedule_count:error.status==="infeasible_proven"?"0":null,
    }});
  }
};
