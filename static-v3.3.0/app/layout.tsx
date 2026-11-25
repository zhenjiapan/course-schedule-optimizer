import Link from "next/link";
import "./globals.css";

export const metadata = {title:"Course Planner", description:"Build and compare weekly course timetables."};
export default function Layout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body><header className="site-header"><Link className="brand" href="/">◫ Course Planner</Link><nav aria-label="Main navigation"><Link href="/planner">Planner</Link><Link href="/about">About</Link></nav></header>{children}</body></html>;
}
