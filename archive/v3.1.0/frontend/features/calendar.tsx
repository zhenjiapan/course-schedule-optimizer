"use client";
import {useState} from "react";
import {clock, days, download, type Scheduled} from "./api";

const shortDays=["一","二","三","四","五","六","日"];
const dateAt = (value:string) => new Date(value+"T00:00:00Z");
function shift(value:string, delta:number) {
  const d=dateAt(value); d.setUTCDate(d.getUTCDate()+delta); return d.toISOString().slice(0,10);
}
function monday(value:string) {return shift(value,-((dateAt(value).getUTCDay()+6)%7));}
const colors=["#d9f2eb","#e8e4ff","#ffe8ce","#dbeafe","#f8e0eb","#eaf1cd","#d5eef8","#ffedd5"];
export default function Calendar({meetings, empty}:{meetings:Scheduled[]; empty:string}) {
  const [chosen,setChosen]=useState("");
  const first=meetings.flatMap(m=>m.occurrences??[m.first]).sort()[0];
  const last=meetings.flatMap(m=>m.occurrences??[m.last]).sort().at(-1);
  const weeks:string[]=[];
  if(first&&last) for(let d=monday(first);d<=last;d=shift(d,7)) weeks.push(d);
  const today=monday(new Date().toISOString().slice(0,10));
  const week=weeks.includes(chosen)?chosen:today> (weeks.at(-1)??"") ? weeks.at(-1) : weeks.includes(today)?today:weeks[0];
  const rows=week?meetings.flatMap(m=>{
    if(m.occurrences) return m.occurrences.filter(d=>d>=week&&d<=shift(week,6)).map(d=>({...m,weekday:((dateAt(d).getUTCDay()+6)%7)+1}));
    const d=shift(week,m.weekday-1);
    return d>=m.first&&d<=m.last?[m]:[];
  }).sort((a,b)=>a.weekday-b.weekday||a.start-b.start):[];
  const start=Math.min(480,...rows.map(m=>Math.floor(m.start/60)*60));
  const end=Math.max(1080,...rows.map(m=>Math.ceil(m.end/60)*60));
  const hours=Array.from({length:(end-start)/60},(_,i)=>start+60*i);
  const courseColors=[...new Set(meetings.map(m=>m.course))].sort();
  const csv=()=>{
    const fields=[["Date","Weekday","Course code","Course name","Section","Type","Start","End","Instructor","Room"],...rows.map(m=>[shift(week!,m.weekday-1),days[m.weekday-1],m.course,m.name,m.section,m.component,clock(m.start),clock(m.end),m.teachers.join(" / ")||"待定",m.rooms.join(" / ")])];
    download("\ufeff"+fields.map(row=>row.map(value=>'"'+value.replaceAll('"','""')+'"').join(",")).join("\r\n"),`timetable_${week}.csv`,"text/csv;charset=utf-8");
  };
  return <>{weeks.length>0&&<div className="calendar-toolbar"><label>教学周 <select value={week} onChange={e=>setChosen(e.target.value)}>{weeks.map((d,i)=><option key={d} value={d}>第 {i+1} 周 · {d}</option>)}</select></label><button className="secondary" onClick={csv} disabled={!rows.length}>导出本周 CSV</button></div>}
    {week&&<p className="muted">{rows.length} 节 · {rows.filter(m=>m.start===510).length} 节早八 · 周一至周五 {5-new Set(rows.filter(m=>m.weekday<=5).map(m=>m.weekday)).size} 个无课日</p>}
    {rows.length===0&&<p className="calendar-empty">{week?"本周无课。":empty}</p>}
    <div className="calendar-scroll" tabIndex={0} aria-label="每周课表"><div className="calendar-grid">
      <span className="day-label">时间</span>{shortDays.map(d=><span className="day-label" key={d}>周{d}</span>)}
      <div className="time-column" style={{height:hours.length*64}}>{hours.map(h=><span key={h}>{clock(h)}</span>)}</div>
      {days.map((d,i)=><div className="day-column" key={d} style={{height:hours.length*64}}>{rows.filter(m=>m.weekday===i+1).map((m,j)=>
        <article key={j} className="meeting" tabIndex={0} style={{top:(m.start-start)*64/60,height:(m.end-m.start)*64/60,background:colors[courseColors.indexOf(m.course)%colors.length]}} title={`${m.name} · ${m.teachers.join(" / ")} · ${m.rooms.join(" / ")}`}>
          <strong>{m.course} · {m.section}</strong><span>{clock(m.start)}–{clock(m.end)}</span><span>{m.teachers.join(" / ")||"待定"}</span><span>{m.rooms.join(" / ")}</span>
        </article>)}</div>)}
    </div></div>
    {rows.length>0&&<details><summary>本周课程明细</summary><ul className="details-list">{rows.map((m,i)=><li key={i}>周{shortDays[m.weekday-1]} {clock(m.start)}–{clock(m.end)} · {m.course} {m.section} · {m.teachers.join(" / ")||"待定"} · {m.rooms.join(" / ")}</li>)}</ul></details>}
  </>;
}
