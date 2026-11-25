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
export async function api<T>(path:string, data?:object, extraHeaders?:Record<string,string>):Promise<T> {
  const response=await fetch("/api/"+path,data ? {method:"POST",headers:{"Content-Type":"application/json",...extraHeaders},body:JSON.stringify(data)} : undefined);
  if (!response.ok) {
    const body=await response.json().catch(()=>null);
    const detail=body?.error?.detail;
    throw new Error(typeof detail==="string" ? detail : Array.isArray(detail) ? detail.map(x=>typeof x==="string"?x:x.message).join(" · ") : `Request failed (${response.status})`);
  }
  return response.json();
}
export function download(body:string, filename:string, mime:string) {
  const url=URL.createObjectURL(new Blob([body],{type:mime}));
  const a=document.createElement("a"); a.href=url; a.download=filename; a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
