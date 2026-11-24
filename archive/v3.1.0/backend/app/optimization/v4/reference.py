"""Independent feasibility and exact rational rescoring."""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from fractions import Fraction as F
from itertools import combinations

from .policy import BALANCED_GAP, GAP_SCALE, GAP_TOLERANCE, HALF, PERIODS


def events(section):
    """Expand by walking the calendar rather than using the model's date generator."""
    by_time = defaultdict(set)
    for m in section.meetings:
        if m.occurrences is not None:
            days = set(m.occurrences)
        else:
            days = set()
            day = m.first
            while day <= m.last:
                if day.isoweekday() == m.weekday:
                    days.add(day)
                day += timedelta(days=1)
        for day in days:
            by_time[day, m.start, m.end].update(m.teachers)
    return [(day, start, end, tuple(sorted(names))) for (day, start, end), names in sorted(by_time.items())]


def audit(cat, codes, choices, p, ctx):
    errors = []
    lessons = defaultdict(list)
    grouped = defaultdict(dict)
    if len(set(choices)) != len(choices):
        errors.append("Duplicate section.")
    missing = (set(p.required) | set(p.locked)) - set(choices)
    if missing:
        errors.append(f"Missing required or locked sections: {sorted(missing)}")
    if set(p.excluded) & set(choices):
        errors.append("An excluded section was selected.")
    for course, code in choices:
        section = next((s for s in cat.sections.get(course, ()) if s.code == code), None)
        if course not in codes or section is None:
            errors.append(f"Unknown or unrequested section: {course} {code}")
            continue
        if section.component in grouped[course]:
            errors.append(f"{course}: more than one {section.component} section.")
        grouped[course][section.component] = code
        records = events(section)
        if not records:
            errors.append(f"{course} {code}: no dated meetings.")
        lessons[course].extend(records)
    for course in codes:
        if set(grouped[course]) != cat.required[course]:
            errors.append(f"{course}: selection does not cover exactly the required components.")
        bindings = cat.bindings
        lec, tut = grouped[course].get("LEC"), grouped[course].get("TUT")
        if lec and tut and any(c == course for c, _ in bindings) and tut not in bindings.get((course, lec), ()):
            errors.append(f"{course}: sections {lec} and {tut} are not a verified pair.")
    credits = sum(Decimal(str(cat.courses[c]["credits"])) for c in set(codes))
    if not p.credit_min <= credits <= p.credit_max:
        errors.append(f"{credits} credits outside [{p.credit_min}, {p.credit_max}].")
    days = defaultdict(list)
    for course, records in lessons.items():
        for day, start, end, _ in records:
            weekday = day.isoweekday()
            if weekday in p.banned_days or (p.ban_early and start == 510) or any(
                weekday == wd and max(a, start) < min(b, end) for wd, a, b in p.blocks()
            ):
                errors.append(f"{course} meets during an unavailable period on {day}.")
            if (p.earliest and p.earliest.mode == "hard" and start < p.earliest.minute
                or p.latest and p.latest.mode == "hard" and end > p.latest.minute):
                errors.append(f"{course} violates a time boundary on {day}.")
            for a, b, other in days[day]:
                if max(a, start) < min(b, end):
                    errors.append(f"{day}: {course} and {other} overlap at minute {max(a, start)}.")
            days[day].append((start, end, course))
    for week in ctx.weeks:
        free = sum(week + timedelta(days=i) not in days for i in range(5))
        if p.free_days and p.free_days.mode == "hard" and free < p.free_days.minimum:
            errors.append(f"Week of {week} has only {free} free weekdays.")
    if errors:
        return {"passed": False, "errors": list(dict.fromkeys(errors)), "credits": float(credits)}, {}
    values, stats = score(lessons, days, p, ctx)
    return {"passed": True, "errors": [], "credits": float(credits), "metrics": stats}, values


def score(lessons, days, p, ctx):
    values = defaultdict(F)
    for records in lessons.values():
        minutes = sum(b-a for _, a, b, _ in records)
        n = len(records)
        for day, a, b, names in records:
            teacher = sum(F(5-p.teachers.get(name, 3), 4) for name in (names or (None,))) / max(1, len(names))
            values["T"] += teacher * F(b-a, minutes)
            values["W"] += F((p.weekdays.get(day.isoweekday(), 3)-3)*(b-a), 2*minutes)
            for period, (lo, hi) in PERIODS.items():
                values["periods"] += F((p.periods.get(period, 3)-3)*max(0, min(b, hi)-max(a, lo)), 2*minutes)
            r = p.early or 3
            values["early"] += F(max(0, 3-r) if a == 510 else max(0, r-3), 2*n)
            if p.earliest and p.earliest.mode == "soft":
                values["earliest"] += F(min(GAP_SCALE, max(0, p.earliest.minute-a)), GAP_SCALE*n)
            if p.latest and p.latest.mode == "soft":
                values["latest"] += F(min(GAP_SCALE, max(0, b-p.latest.minute)), GAP_SCALE*n)
    for key in values:
        values[key] /= len(lessons)

    count_stats = {period: {"applicable_days": 0, "matching_days": 0} for period in p.counts}
    extra = 0
    gaps = []
    for day in ctx.days:
        times = sorted(days.get(day, ()))
        waits = [current[0]-previous[1] for previous, current in zip(times, times[1:])]
        extra += sum(max(g-GAP_TOLERANCE, 0) for g in waits)
        gaps.extend(waits)
        if p.gaps in {"balanced", "spacious"}:
            penalties = [
                min(F(1), F(max(BALANCED_GAP[0]-g, g-BALANCED_GAP[1], 0), GAP_SCALE))
                if p.gaps == "balanced" else max(F(0), 1-F(g, GAP_SCALE))
                for g in waits
            ]
            values["gaps"] += (sum(penalties, F())/len(waits) if waits else F(1, 2))/len(ctx.days)
        for period, rule in p.counts.items():
            lo, hi = PERIODS[period]
            n = sum(lo <= a < hi for a, _, _ in times)
            if n:
                delta = n-rule.target
                error = {"exactly": abs(delta), "at_most": max(delta, 0), "at_least": max(-delta, 0)}[rule.comparison]
                values[f"count:{period}"] += min(F(1), F(error, rule.tolerance))/len(ctx.days)
                count_stats[period]["applicable_days"] += 1
                count_stats[period]["matching_days"] += (error == 0)
    cap = HALF*len(ctx.days)
    ceiling = 10*min(ctx.gap_bound, cap)+max(0, ctx.gap_bound-cap)
    if p.gaps == "compact" and ceiling:
        values["gaps"] = F(10*min(extra, cap)+max(0, extra-cap), ceiling)

    weeks = {}
    q = p.free_days.minimum if p.free_days and p.free_days.mode == "soft" else 0
    for week in ctx.weeks:
        totals = [sum(b-a for a, b, _ in days.get(week+timedelta(days=i), ())) for i in range(5)]
        active = [h for h in totals if h]
        k, free = len(active), 5-len(active)
        weeks[week.isoformat()] = {"free_weekdays": free, "load_minutes": totals}
        short = F(max(0, q-free), q) if q else F(0)
        if p.distribution == "concentrated":
            loss = 3*short/4+F(k, 20) if q else (F(k-1, 4) if k else F(1, 2))
        elif p.distribution == "distributed":
            pairs = list(combinations(active, 2))
            balance = F(sum(abs(a-b) for a, b in pairs), len(pairs)*ctx.week_bounds[week]) if pairs else F(1, 2)
            spread = (F(17, 20)*F(5-k, 4)+F(3, 20)*balance) if k else F(1, 2)
            loss = (spread+short)/2 if q else spread
        else:
            loss = short
        values["B"] += loss/len(ctx.weeks)
    return values, {"weekday_minutes": [sum(b-a for d in days if d.isoweekday() == i for a,b,_ in days[d]) for i in range(1,8)],
                    "early_sessions": sum(a == 510 for rows in days.values() for a,_,_ in rows),
                    "unknown_teacher_sessions": sum(not names for rows in lessons.values() for *_,names in rows),
                    "gap_minutes": sum(gaps), "gap_count": len(gaps), "period_counts": count_stats, "weeks": weeks}
