"""Independent feasibility pass. Does not import optimizer or its overlap helper."""
from datetime import timedelta
from model import validate_request


def check(cat,codes,selections,p):
    errors=validate_request(cat,codes,p)
    warnings=['The database does not provide Lecture/Tutorial section-binding rules and personal prerequisite records; these rules have not been verified.']
    if errors:return {'passed':False,'errors':errors,'warnings':warnings}
    selected=[];seen=set();components={c:[] for c in codes}
    for code,sec in selections:
        if (code,sec) in seen: errors.append(f'Duplicate section: {code} {sec}')
        seen.add((code,sec))
        if code not in codes: errors.append(f'Includes an unrequested course: {code}');continue
        options=[s for s in cat.sections[code] if s.code==sec]
        if len(options)!=1: errors.append(f'Section is missing or not unique: {code} {sec}');continue
        s=options[0];selected.append(s);components[code].append(s.component)
    for code in codes:
        required=set(cat.required[code]);offered={s.component for s in cat.sections[code]}
        missing=required-offered
        if missing and p.allow_missing_components:
            warnings.append(f'{code} Missing components {sorted(missing)} was explicitly waived by the user; only available sections are validated.')
            required-=missing
        for comp in required:
            if components[code].count(comp)!=1: errors.append(f'{code} {comp} Exactly one section must be selected.')
        if set(components[code])-required: errors.append(f'{code} Includes a non-required component.')
    calendar={}
    for s in selected:
        for m in s.meetings:
            # Expand each day independently; intentionally different from optimizer's interval test.
            d=m.first
            while d<=m.last:
                if d.isoweekday()==m.weekday:
                    label=f'{s.course} {s.code}'
                    if m.weekday in p.banned_days: errors.append(f'{label} meets on a blocked weekday')
                    if p.ban_early and m.start==510: errors.append(f'{label} violates the early-class ban')
                    for wd,a,b in p.blocked:
                        if wd==m.weekday and max(a,m.start)<min(b,m.end): errors.append(f'{label} overlaps a blocked period')
                    for a,b,other in calendar.setdefault(d,[]):
                        if max(a,m.start)<min(b,m.end):errors.append(f'{d}: {label} and {other} Time conflict')
                    calendar[d].append((m.start,m.end,label))
                d+=timedelta(days=1)
    errors=list(dict.fromkeys(errors))
    relevant=[w for w in cat.warnings if any(w.startswith(c+' ') for c in codes)]
    return {'passed':not errors,'errors':errors,'warnings':list(dict.fromkeys(warnings+relevant))}
