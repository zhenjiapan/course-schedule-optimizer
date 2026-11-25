"""CP-SAT model. All proof-producing objectives are exact integers."""
from collections import defaultdict
from datetime import timedelta
from fractions import Fraction as F
from itertools import combinations
from math import lcm, prod

from ortools.sat.python import cp_model

from .policy import BALANCED_GAP, GAP_SCALE, GAP_TOLERANCE, HALF, PERIODS


class PrecisionLimit(Exception):
    pass


class Expression:
    def __init__(self, terms=None):
        self.terms = {k: F(v) for k, v in (terms or {}).items() if v}

    def __add__(self, other):
        if not isinstance(other, Expression):
            other = Expression({None: other})
        terms = self.terms.copy()
        for k, coefficient in other.terms.items():
            terms[k] = terms.get(k, 0)+coefficient
        return Expression(terms)

    __radd__ = __add__

    def __mul__(self, factor):
        return Expression({k: v*factor for k, v in self.terms.items()})

    def __truediv__(self, divisor):
        return self * (F(1)/divisor)

    def value(self, solver):
        return sum((coef*(1 if var is None else solver.value(var))
                    for var, coef in self.terms.items()), F())


class Encoding:
    def __init__(self, groups, records, edges, daily, ctx, policy, check):
        self.model = cp_model.CpModel()
        self.ctx, self.p, self.check = ctx, policy, check
        self.groups, self.records, self.daily = groups, records, daily
        self.edge_pairs = frozenset(edges)
        self.course_pattern_space = 0
        self.course_patterns_kept = 0
        self.bounds = {}
        self.x = {key: self.boolean(":".join(key)) for key in records}
        self.loads = {}
        self.week_vars = {}
        self.day_cache = {}
        for domain in groups.values():
            self.model.add_exactly_one(self.x[k] for k in domain)
        for a, b in sorted(edges):
            check()
            self.model.add_at_most_one(self.x[a], self.x[b])
        if policy.free_days and policy.free_days.mode == "hard" and policy.free_days.minimum:
            for w in ctx.weeks:
                count, _, _ = self.week(w)
                self.model.add(count <= 5-policy.free_days.minimum)

    def boolean(self, name):
        v = self.model.new_bool_var(name)
        self.bounds[v] = 1
        return v

    def integer(self, bound, name):
        v = self.model.new_int_var(0, bound, name)
        self.bounds[v] = bound
        return v

    def objective(self, expression):
        scale = 1
        for coefficient in expression.terms.values():
            scale = lcm(scale, coefficient.denominator)
            if scale > 2**61:
                raise PrecisionLimit()
        terms = {v: int(c*scale) for v,c in expression.terms.items()}
        if sum(abs(c)*(1 if v is None else self.bounds[v]) for v,c in terms.items()) > 2**61:
            raise PrecisionLimit()
        return sum((c if v is None else c*v for v,c in terms.items())), scale

    def ordered_objective(self, model, expression):
        """Return most-significant-first integer expressions on a private model."""
        try:
            goal, _ = self.objective(expression)
            return [goal]
        except PrecisionLimit:
            pass
        # A positive scale preserves ordering. Move negative terms into
        # c*(upper-v), so every digit and carry has a nonnegative domain.
        scale = lcm(*(c.denominator for c in expression.terms.values()))
        terms = [(v, abs(int(c*scale)), c < 0, self.bounds[v])
                 for v,c in expression.terms.items() if v is not None]
        radix = 2**18
        digits = []
        previous, previous_bound = 0, 0
        while any(coefficient for _,coefficient,_,_ in terms) or previous_bound:
            self.check()
            pending = []
            column = []
            highest = previous_bound
            for var, coefficient, reverse, bound in terms:
                carry, digit = divmod(coefficient,radix)
                pending.append((var,carry,reverse,bound))
                term = bound-var if reverse else var
                if digit:
                    column.append(digit*term)
                    highest += digit*bound
            if highest > 2**60 or len(digits) >= 256:
                raise PrecisionLimit()
            value = model.new_int_var(0,min(radix-1,highest),"objective digit")
            carry = model.new_int_var(0,highest//radix,"objective carry")
            model.add(value+radix*carry == previous+sum(column))
            digits.append(value)
            previous, previous_bound = carry, highest//radix
            terms = pending
        return list(reversed(digits)) or [0]

    def table(self, index, values, name):
        scale = lcm(*(F(v).denominator for v in values))
        if scale > 2**55:
            raise PrecisionLimit()
        values = [int(v*scale) for v in values]
        result = self.integer(max(values), name)
        self.model.add_element(index, values, result)
        return Expression({result: F(1, scale)})

    def course_features(self):
        p, m = self.p, self.model
        active = set()
        if "T" not in p.disabled and p.teachers: active.add("T")
        if "W" not in p.disabled and p.weekdays: active.add("W")
        if "H" not in p.disabled:
            if p.periods: active.add("periods")
            if p.early and p.early != 3: active.add("early")
            for k in ("earliest", "latest"):
                if getattr(p, k) and getattr(p, k).mode == "soft": active.add(k)
        if not active:
            return {}
        coefficients = {k: {} for k in active}
        courses = defaultdict(list)
        for (course, _), group in self.groups.items():
            courses[course].append(group)
        for course, groups in courses.items():
            self.course_pattern_space += prod(len(group) for group in groups)
            for signature in self.compatible_signatures(groups):
                self.course_patterns_kept += 1
                indicator = self.x[signature[0]]
                if len(signature) > 1:
                    indicator = self.boolean(f"pattern:{course}")
                    xs = [self.x[k] for k in signature]
                    m.add_min_equality(indicator, xs)
                events = [record for k in signature for record in self.records[k]]
                minutes = sum(b-a for _, a,b,_ in events)
                counts = defaultdict(F)
                for d, a, b, names in events:
                    self.check()
                    if "T" in active:
                        counts["T"] += F((b-a)*sum(5-p.teachers.get(n,3) for n in (names or (None,))), 4*max(1,len(names))*minutes)
                    if "W" in active:
                        counts["W"] += F((b-a)*(p.weekdays.get(d.isoweekday(),3)-3),2*minutes)
                    if "periods" in active:
                        for period, (lo, hi) in PERIODS.items():
                            counts["periods"] += F(max(0,min(b,hi)-max(a,lo))*(p.periods.get(period,3)-3),2*minutes)
                    if "early" in active:
                        counts["early"] += F(max(0, (3-p.early) if a==510 else (p.early-3)),2*len(events))
                    for key, value in (("earliest", p.earliest.minute-a if p.earliest else 0),
                                       ("latest", b-p.latest.minute if p.latest else 0)):
                        if key in active:
                            counts[key] += F(max(0,min(GAP_SCALE,value)),GAP_SCALE*len(events))
                for key, value in counts.items():
                    coefficients[key][indicator] = value/len(courses)
        return {key: Expression(terms) for key, terms in coefficients.items()}

    def compatible_signatures(self, groups):
        """Enumerate only component combinations that can coexist.

        A pattern containing an incompatible section pair has an indicator
        that is forced to zero by the model's at-most-one constraint. Omitting
        that pattern therefore removes variables and score terms without
        removing any feasible timetable or changing its score.
        """
        chosen = []

        def extend(index):
            if index == len(groups):
                yield tuple(chosen)
                return
            for key in groups[index]:
                self.check()
                if any(tuple(sorted((key, other))) in self.edge_pairs for other in chosen):
                    continue
                chosen.append(key)
                yield from extend(index + 1)
                chosen.pop()

        return extend(0)

    def day_load(self, day):
        rows = tuple(self.daily.get(day, ()))
        if rows in self.loads:
            return self.loads[rows]
        load = self.integer(1440, "daily teaching minutes")
        self.model.add(load == sum((b-a)*self.x[k] for a,b,k in rows))
        used = self.boolean("teaching day")
        self.model.add(load >= 1).only_enforce_if(used)
        self.model.add(load == 0).only_enforce_if(used.Not())
        self.loads[rows] = load, used
        return load, used

    def week(self, monday):
        if monday not in self.week_vars:
            rows = [self.day_load(monday+timedelta(days=i)) for i in range(5)]
            count = self.integer(5, "teaching weekdays")
            self.model.add(count == sum(used for _,used in rows))
            self.week_vars[monday] = count, rows, self.ctx.week_bounds[monday]
        return self.week_vars[monday]

    def daily_features(self):
        p, m = self.p, self.model
        if "D" in p.disabled or not self.ctx.days:
            return {}
        features = defaultdict(Expression)
        for day in self.ctx.days:
            self.check()
            rows = tuple(self.daily.get(day, ()))
            if rows not in self.day_cache:
                parts = {}
                for period, rule in p.counts.items():
                    lo, hi = PERIODS[period]
                    candidates = [self.x[k] for a, _, k in rows if lo <= a < hi]
                    count = self.integer(len(candidates), "period count")
                    m.add(count == sum(candidates))
                    values = [F()]
                    for n in range(1, len(candidates)+1):
                        delta = n-rule.target
                        errors = {"exactly": abs(delta), "at_most": max(0,delta), "at_least": max(0,-delta)}
                        values.append(min(1,F(errors[rule.comparison],rule.tolerance)))
                    parts[f"count:{period}"] = self.table(count, values, "count loss")
                if p.gaps:
                    parts["gaps"] = self.gap_expression(rows)
                self.day_cache[rows] = parts
            for key, expr in self.day_cache[rows].items():
                features[key] = features[key]+expr
        if p.gaps == "compact":
            raw = features.pop("gaps")
            ceiling = self.ctx.gap_bound
            cap = HALF*len(self.ctx.days)
            if ceiling:
                compact = self.integer(ceiling,"adjusted gaps")
                m.add(compact == self.objective(raw)[0])
                bend = self.integer(min(ceiling, cap), "gaps below threshold")
                m.add_min_equality(bend, [compact, cap])
                features["gaps"] = Expression({compact: 1, bend: 9})/(10*min(ceiling,cap)+max(0,ceiling-cap))*len(self.ctx.days)
        return {k: v/len(self.ctx.days) for k,v in features.items()}

    def gap_expression(self, rows):
        m, mode = self.model, self.p.gaps
        incoming = [[self.boolean("first event")] for _ in rows]
        outgoing = [[self.boolean("last event")] for _ in rows]
        empty = self.boolean("empty day")
        m.add_exactly_one([empty]+[row[0] for row in incoming])
        m.add_exactly_one([empty]+[row[0] for row in outgoing])
        costs = {}
        for i, (_, end, _) in enumerate(rows):
            self.check()
            for j in range(i+1,len(rows)):
                start = rows[j][0]
                if start < end:
                    continue
                gap = start-end
                arc = self.boolean("adjacent events")
                outgoing[i].append(arc)
                incoming[j].append(arc)
                if mode == "compact":
                    costs[arc] = max(gap-GAP_TOLERANCE,0)
                elif mode == "balanced":
                    costs[arc] = min(GAP_SCALE,max(0,BALANCED_GAP[0]-gap,gap-BALANCED_GAP[1]))
                else:
                    costs[arc] = max(0,GAP_SCALE-gap)
        for (_, _, key), ins, outs in zip(rows,incoming,outgoing):
            m.add(sum(ins) == self.x[key])
            m.add(sum(outs) == self.x[key])
        if mode == "compact":
            return Expression(costs)
        count = self.integer(len(rows),"event count")
        m.add(count == sum(self.x[k] for _,_,k in rows))
        na = self.boolean("fewer than two events")
        m.add(count <= 1).only_enforce_if(na)
        m.add(count >= 2).only_enforce_if(na.Not())
        raw = sum(v*c for v,c in costs.items())
        expr = Expression({na:F(1,2)})
        for n in range(2,len(rows)+1):
            self.check()
            selected = self.boolean("event count equals n")
            m.add(count == n).only_enforce_if(selected)
            m.add(count != n).only_enforce_if(selected.Not())
            cost = self.integer((len(rows)-1)*GAP_SCALE,"conditional gap loss")
            m.add(cost == raw).only_enforce_if(selected)
            m.add(cost == 0).only_enforce_if(selected.Not())
            expr = expr+Expression({cost:F(1,(n-1)*GAP_SCALE)})
        return expr

    def weekly_feature(self):
        p, m = self.p, self.model
        q = p.free_days.minimum if p.free_days and p.free_days.mode == "soft" else 0
        if "B" in p.disabled or not (p.distribution or q):
            return {}
        total = Expression()
        for w in self.ctx.weeks:
            self.check()
            count, rows, bound = self.week(w)
            short = [F(max(0,q-5+k),q) if q else F() for k in range(6)]
            if p.distribution == "concentrated":
                values = [3*s/4+F(k,20) if q else (F(k-1,4) if k else F(1,2)) for k,s in enumerate(short)]
                loss = self.table(count, values, "concentration")
            elif p.distribution == "distributed":
                coverage = [F(1,2),F(17,20)+F(3,40)]+[F(17*(5-k),80) for k in range(2,6)]
                loss = self.table(count, coverage, "distribution coverage")
                differences = []
                for (a, on_a),(b, on_b) in combinations(rows,2):
                    d = self.integer(bound,"load difference")
                    m.add_abs_equality(d,a-b)
                    use = self.integer(bound,"active pair difference")
                    m.add(use == d).only_enforce_if([on_a,on_b])
                    m.add(use == 0).only_enforce_if(on_a.Not())
                    m.add(use == 0).only_enforce_if(on_b.Not())
                    differences.append(use)
                for k in range(2,6):
                    active = self.boolean("weekday count case")
                    m.add(count == k).only_enforce_if(active)
                    m.add(count != k).only_enforce_if(active.Not())
                    use = self.integer(10*bound,"weekday case total difference")
                    m.add(use == sum(differences)).only_enforce_if(active)
                    m.add(use == 0).only_enforce_if(active.Not())
                    loss = loss+Expression({use:F(3,20*(k*(k-1)//2)*bound)})
                if q:
                    loss = (loss+self.table(count,short,"free day shortfall"))/2
            else:
                loss = self.table(count,short,"free day shortfall")
            total = total+loss
        return {"B":total/len(self.ctx.weeks)}
