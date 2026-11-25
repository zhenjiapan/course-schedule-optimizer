import {clock, minute, type Detail, type Selection} from "./api";

export const weekdays = ["周一","周二","周三","周四","周五","周六","周日"];
export const periods = ["morning","afternoon","evening"] as const;
export const periodNames = {morning:"上午",afternoon:"下午",evening:"晚上"};
export const slots = {all:[0,1440],morning:[0,720],afternoon:[720,1080],evening:[1080,1440]} as const;
export type Mode = ""|"hard"|"soft";
export type Rule = "required"|"locked"|"excluded";
export type BlockRule = {day:number; kind:keyof typeof slots|"custom"; start:string; end:string};
export type SectionRule = {selection:Selection; rule:Rule; reason:string};
export type Ratings = Record<string,number>;
export const categories = {T:"教师", W:"星期", H:"时间", D:"每日结构", B:"周内分布"};
export type Category = keyof typeof categories;
type Boundary = {mode:Mode; time:string};
type Count = {comparison:""|"exactly"|"at_most"|"at_least"; target:string};
const emptyCount:Count = {comparison:"",target:"2"};

export const defaults = {
  creditMin:"", creditMax:"", blocks:[] as BlockRule[], sectionRules:[] as SectionRule[],
  earliest:{mode:"",time:"10:00"} as Boundary, latest:{mode:"",time:"18:00"} as Boundary,
  early:0, ratePeriods:false, rateWeekdays:false, rateTeachers:false,
  periods:{} as Ratings, weekdays:{} as Ratings, teachers:{} as Ratings,
  gaps:"", counts:{morning:emptyCount,afternoon:emptyCount,evening:emptyCount},
  distribution:"", freeMode:"" as Mode, freeDays:2, weeks:[] as string[],
  weights:{} as Ratings, disabled:[] as Category[], timeout:"30",
};
export type Form = typeof defaults;

export function validTime(value:string, end=false) {
  return /^([01]\d|2[0-3]):[0-5]\d$/.test(value) || (end && value==="24:00");
}

export function interval(rule:BlockRule) {
  return rule.kind==="custom"?[minute(rule.start),minute(rule.end)]:slots[rule.kind];
}

export function makePayload(form:Form, term:string, codes:string[], teachers:string[]) {
  const boundaries = (value:Boundary) => value.mode ? {mode:value.mode,minute:minute(value.time)} : null;
  const rules = (rule:Rule) => form.sectionRules.filter(item=>item.rule===rule).map(item=>item.selection);
  return { term,codes, preferences:{
    credit_min:form.creditMin || "12", credit_max:form.creditMax || "18",
    blocked:form.blocks.map(rule=>[rule.day,...interval(rule)]),
    required:rules("required"),locked:rules("locked"),excluded:rules("excluded"),
    earliest:boundaries(form.earliest),latest:boundaries(form.latest),
    early:form.early || null,
    periods:form.ratePeriods?Object.fromEntries(periods.map(k=>[k,form.periods[k]??3])):{},
    weekdays:form.rateWeekdays?Object.fromEntries(weekdays.map((_,i)=>[i+1,form.weekdays[i+1]??3])):{},
    teachers:form.rateTeachers?Object.fromEntries(teachers.map(k=>[k,form.teachers[k]??3])):{},
    gaps:form.gaps||null,
    counts:Object.fromEntries(periods.flatMap(k=>form.counts[k].comparison?[[k,{...form.counts[k],target:Number(form.counts[k].target)}]]:[])),
    distribution:form.distribution||null,
    free_days:form.freeMode?{mode:form.freeMode,minimum:form.freeDays}:null,
    teaching_weeks:form.weeks,
    weights:form.weights,disabled:form.disabled,
  }};
}

export function candidateMondays(details:Detail[]) {
  const meetings=details.flatMap(d=>d.sections.flatMap(s=>s.meetings));
  const starts=meetings.flatMap(m=>m.occurrences??[m.first]).sort();
  const ends=meetings.flatMap(m=>m.occurrences??[m.last]).sort();
  if (!starts.length||!ends.length) return [];
  const date=new Date(starts[0]+"T00:00:00Z");
  date.setUTCDate(date.getUTCDate()-((date.getUTCDay()+6)%7));
  const weeks:string[]=[];
  while(date.toISOString().slice(0,10)<=ends[ends.length-1]&&weeks.length<53){
    weeks.push(date.toISOString().slice(0,10));
    date.setUTCDate(date.getUTCDate()+7);
  }
  return weeks;
}

export function blockLabel(rule:BlockRule) {
  if(rule.kind==="custom"&&(!validTime(rule.start)||!validTime(rule.end,true))) return "";
  const [a,b]=interval(rule);
  return `${clock(a)}–${clock(b)}${b<a?"（次日）":""}`;
}
