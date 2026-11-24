import Link from "next/link";
export default function Home() {
  return <main className="hero"><div className="hero-copy"><p className="eyebrow">CUHK–Shenzhen course planning</p><h1>Find a timetable that fits your week.</h1><p>Choose courses, set your preferences, and compare schedules before enrollment.</p><Link className="primary" href="/planner">Open planner →</Link></div><div className="hero-art" aria-hidden="true"><span/><span/><span/><span/><span/></div></main>;
}
