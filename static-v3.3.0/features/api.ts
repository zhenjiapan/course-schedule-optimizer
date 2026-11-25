export interface Course {code:string; name:string; credits:number}
export interface Meeting {weekday:number; start:number; end:number; first:string; last:string; rooms:string[]; teachers:string[]; occurrences?:string[]|null}
export interface Section {code:string; component:string; meetings:Meeting[]; teachers:string[]}
export interface Detail extends Course {required:string[]; sections:Section[]; warnings:string[]; bindings?:Record<string,string[]>}
export type Selection = [string,string];
export type Block = [number,string,string];
export interface Scheduled extends Meeting {course:string; section:string; component:string; name:string}
export interface Validation {passed:boolean; errors:string[]; warnings:string[]; meetings:Scheduled[]; metrics?:{early_sessions:number; unknown_teacher_sessions:number; gap_minutes:number; gap_count:number; period_counts:Record<string,{applicable_days:number; matching_days:number}>; weeks:Record<string,{free_weekdays:number; load_minutes:number[]}>}}
export interface Solution {selections:Selection[]; score:number|null; proven?:boolean; breakdown:Record<string,number>; validation:Validation}
export interface SolverRun {phase:string; status:string; branches:number; conflicts:number; wall_time_seconds:number}
export interface SearchSummary {solver_calls:number; branches:number; conflicts:number; solver_wall_seconds:number}
export interface SearchModel {course_pattern_space:number; course_patterns_kept:number}
export interface Progress {job_id:string; state:string; phase:string; branches:number; schedules_found?:string|number; current_branches:number; conflicts:number; solver_run:number; result_status?:string; preview?:Solution[]; result?:Result}
export interface Result {status:string; qualified_schedule_count?:string|null; solutions:Solution[]; errors:string[]; nodes?:number; elapsed?:number; elapsed_ms?:number; certified_prefix?:number; proof_scope?:string; warnings?:string[]; solver_runs?:SolverRun[]; search_summary?:SearchSummary; search_model?:SearchModel}
export const days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];
export const clock = (n:number) => [Math.floor(n/60),n%60].map(x=>String(x).padStart(2,"0")).join(":");
export const minute = (s:string) => {const [h,m]=s.split(":").map(Number); return h*60+m;};
type BrowserPayload = {term:string; codes:string[]; preferences:object; selections?:Selection[]};
let catalogRequest:Promise<Record<string,Record<string,Detail>>>|undefined;
const browserJobs=new Map<string,Progress>();

async function catalog() {
  catalogRequest ??= fetch("/catalog.json").then(response=>{
    if(!response.ok)throw new Error("课程快照无法加载，请刷新重试。");
    return response.json();
  }).catch(error=>{catalogRequest=undefined;throw error;});
  return catalogRequest;
}

export async function api<T>(path:string, data?:object, _extraHeaders?:Record<string,string>):Promise<T> {
  const url=new URL(path,"https://planner.invalid/");
  const name=url.pathname;
  const payload=data as BrowserPayload|undefined;
  if(name.startsWith("/v4/progress/")){
    const id=name.split("/").pop()??"";
    const snapshot=browserJobs.get(id);
    if(!snapshot)throw new Error("本次搜索记录不存在。");
    if(snapshot.result||snapshot.state==="failed")browserJobs.delete(id);
    return snapshot as T;
  }
  if(name==="/v4/settings"){
    return {top_k:3,last_verified:null,data_source:"学校 SIS 课程快照",timeout_limit:0} as T;
  }
  const current=(await catalog())[payload?.term??url.searchParams.get("term")??""]??{};
  if(name==="/courses"){
    return Object.values(current).map(({code,name,credits})=>({code,name,credits})) as T;
  }
  if(name.startsWith("/courses/")){
    const item=current[decodeURIComponent(name.slice("/courses/".length))];
    if(!item)throw new Error("本学期没有该课程。");
    return item as T;
  }
  if(payload&&(name==="/v4/optimize"||name==="/v4/validate")){
    const details=payload.codes.map(code=>current[code]);
    if(!details.length||details.some(detail=>!detail))throw new Error("选中的课程快照加载失败。");
    const jobId=crypto.randomUUID();
    const worker=new Worker("/planner-worker.js");
    const request={jobId,details,preferences:payload.preferences,selections:payload.selections};
    if(name==="/v4/validate"){
      return new Promise<T>((resolve,reject)=>{
        worker.onmessage=({data})=>{worker.terminate();resolve(data.validation as T);};
        worker.onerror=()=>{worker.terminate();reject(new Error("浏览器无法运行校验。"));};
        worker.postMessage(request);
      });
    }
    const initial:Progress={job_id:jobId,state:"queued",phase:"queued",branches:0,current_branches:0,conflicts:0,solver_run:0};
    browserJobs.set(jobId,initial);
    worker.onmessage=({data}:MessageEvent<Progress>)=>{
      browserJobs.set(jobId,data);
      if(data.result)worker.terminate();
    };
    worker.onerror=()=>{worker.terminate();browserJobs.set(jobId,{...initial,state:"failed"});};
    worker.postMessage(request);
    return {job_id:jobId} as T;
  }
  throw new Error("未知的规划操作。");
}
export function download(body:string, filename:string, mime:string) {
  const url=URL.createObjectURL(new Blob([body],{type:mime}));
  const a=document.createElement("a"); a.href=url; a.download=filename; a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
