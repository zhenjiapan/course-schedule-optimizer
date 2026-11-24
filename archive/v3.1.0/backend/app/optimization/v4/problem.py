"""Translate a catalog and V4 request into a fixed, dated feasible domain."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from ..model import dates


class ProblemError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


@dataclass
class Context:
    days: tuple[date, ...]
    weeks: tuple[date, ...]
    gap_bound: int
    week_bounds: dict[date, int]
    warnings: list[str]


def incompatible(cat, left, right):
    if left.course != right.course:
        return False
    if left.component == "TUT":
        left, right = right, left
    return (left.component == "LEC" and right.component == "TUT"
            and any(c == left.course for c, _ in cat.bindings)
            and right.code not in cat.bindings.get((left.course, left.code), ()))


def prepare(cat, codes, p, check_deadline):
    if not codes or len(set(codes)) != len(codes) or set(codes)-cat.courses.keys():
        raise ProblemError("invalid", "Select distinct courses offered in this term.")
    sections = {(c, s.code): s for c in sorted(codes) for s in sorted(cat.sections[c], key=lambda s: s.code)}
    requested = set(p.required) | set(p.locked)
    excluded = set(p.excluded)
    if (requested | excluded)-sections.keys():
        raise ProblemError("invalid", "A required, locked or excluded section was not found in the selected courses.")
    if requested & excluded:
        raise ProblemError("infeasible_proven", f"班次同时被要求保留和排除：{sorted(requested & excluded)}")
    credits = sum(Decimal(str(cat.courses[c]["credits"])) for c in codes)
    if not p.credit_min <= credits <= p.credit_max:
        raise ProblemError("infeasible_proven", f"{credits} credits outside [{p.credit_min}, {p.credit_max}].")
    by_section = {}
    all_days = set()
    for key, section in sections.items():
        check_deadline()
        records = defaultdict(set)
        for m in section.meetings:
            for day in dates(m):
                records[day, m.start, m.end].update(m.teachers)
        by_section[key] = tuple((day, a, b, tuple(sorted(names))) for (day, a, b), names in sorted(records.items()))
        all_days.update(day for day, *_ in by_section[key])
    needs_weeks = ("B" not in p.disabled and p.distribution) or (
        p.free_days and p.free_days.minimum and (p.free_days.mode == "hard" or "B" not in p.disabled)
    )
    if needs_weeks and not p.teaching_weeks:
        raise ProblemError("insufficient_data", "Supply the verified complete teaching weeks for weekly rules.")
    days = tuple(sorted(p.evaluation_days or all_days))
    weeks = tuple(sorted(p.teaching_weeks))
    warnings = [w for w in cat.warnings if any(w.startswith(c+" ") for c in codes)]
    if any(m.occurrences is None for section in sections.values() for m in section.meetings):
        warnings.append("Catalog meetings without explicit dates repeat by weekday within their recorded date ranges.")
    if not p.evaluation_days and (p.gaps or p.counts):
        warnings.append("Daily evaluation uses the union of candidate meeting dates. Supply evaluation_days for a verified calendar.")
    for c in sorted(codes):
        if {"LEC", "TUT"} <= cat.required[c] and not any(course == c for course, _ in cat.bindings):
            warnings.append(f"{c}: Lecture/Tutorial binding has not been verified.")
    blocked = p.blocks()
    groups = {}
    eligible = {}
    for c in sorted(codes):
        if not cat.required[c]:
            raise ProblemError("insufficient_data", f"{c}: required components are unknown.")
        for component in sorted(cat.required[c]):
            check_deadline()
            domain = [key for key, s in sections.items() if s.course == c and s.component == component and by_section[key]]
            if not domain:
                raise ProblemError("insufficient_data", f"{c}: no dated {component} sections.")
            fixed = requested & set(domain)
            if len(fixed) > 1:
                raise ProblemError("infeasible_proven", f"{c} 的 {component} 组件只能选一个班次，目前要求保留：{', '.join(k[1] for k in sorted(fixed))}。")
            groups[c, component] = []
            for key in domain:
                if key in excluded or (fixed and key not in fixed):
                    continue
                records = by_section[key]
                hits = [(d, a, b) for d, start, end, _ in records for w, a, b in blocked
                        if w == d.isoweekday() and start < b and end > a]
                if hits and key in fixed:
                    day, start, end = hits[0]
                    def hhmm(value):
                        return f"{value // 60:02d}:{value % 60:02d}"
                    raise ProblemError("infeasible_proven",
                        f"{c} {key[1]} 在 {day} 上课，与禁排规则 {hhmm(start)}–{hhmm(end)} 冲突。")
                if hits or any(d.isoweekday() in p.banned_days or (p.ban_early and start == 510) or
                       (p.earliest and p.earliest.mode == "hard" and start < p.earliest.minute) or
                       (p.latest and p.latest.mode == "hard" and end > p.latest.minute)
                       for d, start, end, _ in records):
                    continue
                if any(d == f and b > c0 for (d, a, b, _), (f, c0, e, _) in zip(records, records[1:])):
                    continue
                eligible[key] = records
                groups[c, component].append(key)
            if set(domain) <= excluded:
                raise ProblemError("infeasible_proven", f"{c} 的 {component} 组件所有班次都已被排除。")
            if not groups[c, component]:
                raise ProblemError("infeasible_proven", f"{c}: no {component} section satisfies the selected hard rules.")
    if not requested <= eligible.keys():
        raise ProblemError("infeasible_proven", "A required or locked section cannot be scheduled.")
    daily = defaultdict(list)
    edges = set()
    for key, records in eligible.items():
        for day, start, end, _ in records:
            daily[day].append((start, end, key))
    for rows in daily.values():
        check_deadline()
        active = []
        for a, b, key in sorted(rows):
            active = [(end, other) for end, other in active if end > a]
            edges.update(tuple(sorted((key, other))) for _, other in active if key != other)
            active.append((b, key))
    for c in codes:
        check_deadline()
        for left in groups.get((c, "LEC"), ()):
            for right in groups.get((c, "TUT"), ()):
                if incompatible(cat, sections[left], sections[right]):
                    edges.add(tuple(sorted((left, right))))
    neighbors = defaultdict(set)
    for a, b in edges:
        neighbors[a].add(b)
        neighbors[b].add(a)
    while True:
        check_deadline()
        fixed = {domain[0] for domain in groups.values() if len(domain) == 1}
        forbidden = set().union(*(neighbors[k] for k in fixed))
        if fixed & forbidden:
            pair = next((a,b) for a,b in sorted(edges) if a in fixed and b in fixed)
            a, b = pair
            witness = next(((d, max(i,k), min(j,l)) for d,i,j,_ in eligible[a]
                            for e,k,l,_ in eligible[b] if d == e and max(i,k) < min(j,l)), None)
            where = f" on {witness[0]} (minutes {witness[1]}–{witness[2]})" if witness else " (section binding)"
            raise ProblemError("infeasible_proven", f"Forced sections {a} and {b} conflict{where}.")
        changed = False
        for group, domain in groups.items():
            remaining = [k for k in domain if k not in forbidden]
            if not remaining:
                raise ProblemError("infeasible_proven", f"{group}: its remaining sections conflict with forced sections.")
            changed |= remaining != domain
            groups[group] = remaining
        if not changed:
            break
    live = {key for domain in groups.values() for key in domain}
    daily = {d: sorted(row for row in items if row[2] in live) for d, items in daily.items()}
    def span(d):
        rows = daily.get(d, ())
        return max((b for _, b, _ in rows), default=0)-min((a for a, _, _ in rows), default=0)
    ctx = Context(days, weeks, sum(span(d) for d in days),
                  {w: max(1, *(span(w+timedelta(days=i)) for i in range(5))) for w in weeks}, warnings)
    return groups, {k: eligible[k] for k in sorted(live)}, {pair for pair in edges if set(pair) <= live}, daily, ctx
