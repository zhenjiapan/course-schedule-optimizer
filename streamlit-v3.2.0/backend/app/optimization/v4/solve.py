"""Calibrate, rank and independently verify schedules on one deadline."""
from fractions import Fraction as F
from time import monotonic

from ortools.sat.python import cp_model

from .cp import Encoding, Expression, PrecisionLimit
from .policy import VERSION
from .problem import ProblemError, prepare
from .reference import audit


def solve(cat, codes, policy, timeout=30, deadline=None, progress_store=None, progress_job_id=None):
    start = monotonic()
    budget_deadline = start + timeout if timeout is not None else float("inf")
    deadline = min(deadline, budget_deadline) if deadline is not None else budget_deadline
    payload = {"status": None, "solutions": [], "certified_prefix": 0, "proof_scope": None,
               "objective_version": VERSION, "numeric_mode": "exact", "warnings": [],
               "errors": [], "calibration": {}, "objective_bound": None,
               "solver_runs": [], "search_summary": None, "qualified_schedule_count": None}
    seed = ()
    active = {}
    transformations = {}
    status = "timeout_no_feasible"
    ctx = None
    seed_row = None
    solver_phase = "feasibility"
    completed_branches = 0
    leaders = {}
    seen_schedules = set()
    counted = None

    def publish_progress(**updates):
        if progress_store is None or not progress_job_id:
            return
        try:
            snapshot = dict(progress_store.get(progress_job_id, {}))
            if snapshot.get("state") in {"completed", "failed", "timed_out"}:
                return
            snapshot.update(updates, schedules_found=str(counted) if counted is not None else str(len(seen_schedules)))
            snapshot["updated_at"] = monotonic()
            progress_store[progress_job_id] = snapshot
        except Exception:
            # Progress reporting is best-effort and must never stop solving.
            return

    publish_progress(state="running", phase="preparing", branches=0,
                     current_branches=0, conflicts=0, solver_run=0)

    def check():
        if monotonic() >= deadline:
            raise TimeoutError()

    def run(model, enumerate_schedules=False):
        nonlocal completed_branches, counted
        check()
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.relative_gap_limit = 0
        solver.parameters.absolute_gap_limit = 0
        if deadline != float("inf"):
            solver.parameters.max_time_in_seconds = max(0.0001, deadline-monotonic())
        solver.parameters.enumerate_all_solutions = enumerate_schedules
        run_index = len(payload["solver_runs"]) + 1
        base_branches = completed_branches
        last_progress_write = [0.0]
        publish_progress(state="running", phase=solver_phase,
                         branches=base_branches, current_branches=0,
                         conflicts=sum(item["conflicts"] for item in payload["solver_runs"]),
                         solver_run=run_index)

        class BranchProgress(cp_model.CpSolverSolutionCallback):
            def on_solution_callback(self):
                nonlocal counted
                if enumerate_schedules:
                    counted += 1
                if timeout is None and solver_phase in {"top_k_ranking", "tie_breaking"}:
                    remember(accepted(selection(self)))
                now = monotonic()
                if now - last_progress_write[0] < 0.4:
                    return
                branches = int(self.num_branches)
                publish_progress(
                    state="running", phase=solver_phase,
                    branches=base_branches + branches, current_branches=branches,
                    conflicts=sum(item["conflicts"] for item in payload["solver_runs"]) + int(self.num_conflicts),
                    solver_run=run_index, preview=list(leaders.values()),
                )
                last_progress_write[0] = now

        callback = BranchProgress() if progress_store is not None or enumerate_schedules else None
        flag = solver.solve(model, callback)
        status_names = {
            cp_model.OPTIMAL: "optimal",
            cp_model.FEASIBLE: "feasible",
            cp_model.INFEASIBLE: "infeasible",
            cp_model.MODEL_INVALID: "model_invalid",
            cp_model.UNKNOWN: "unknown",
        }
        run_stats = {
            "phase": solver_phase,
            "status": status_names.get(flag, str(flag)),
            "branches": int(solver.num_branches),
            "conflicts": int(solver.num_conflicts),
            "wall_time_seconds": round(float(solver.wall_time), 4),
        }
        payload["solver_runs"].append(run_stats)
        completed_branches += run_stats["branches"]
        publish_progress(state="running", phase=solver_phase,
                         branches=completed_branches, current_branches=0,
                         conflicts=sum(item["conflicts"] for item in payload["solver_runs"]),
                         solver_run=run_index, preview=list(leaders.values()))
        if flag == cp_model.MODEL_INVALID:
            raise ProblemError("internal_error", model.validate() or "Invalid solver model.")
        return flag, solver

    def selection(solver):
        return tuple(next(k for k in domain if solver.value(enc.x[k])) for domain in groups.values())

    def accepted(signature, solver=None):
        report, raw = audit(cat, codes, signature, policy, ctx)
        if not report["passed"]:
            raise ProblemError("internal_error", f"Independent validation failed: {report['errors']}")
        metrics = {}
        for key in features if solver is not None else ():
            if raw.get(key,F()) != features[key].value(solver):
                raise ProblemError("internal_error", f"Independent score mismatch in {key}.")
        for category, stages in transformations.items():
            if category in active:
                metrics[category] = sum(
                    (sum((offset+factor*raw.get(k,F()) for k,offset,factor in stage), F())/len(stage)
                     for stage in stages), F())/len(stages)
        loss = (sum((v*policy.weights.get(k,3) for k,v in metrics.items()),F())/
                sum(policy.weights.get(k,3) for k in metrics)) if metrics else None
        return {"selections": signature, "score": float(100*(1-loss)) if loss is not None else None,
                "loss": str(loss) if loss is not None else None,
                "breakdown": {k: float(v) for k,v in metrics.items()},
                "validation": report, "rank": None, "proven": False}

    def remember(row):
        seen_schedules.add(row["selections"])
        leaders[row["selections"]] = row
        def key(item):
            signature, candidate = item
            return F(candidate["loss"] or 0), signature
        best = sorted(leaders.items(), key=key)[:3]
        leaders.clear()
        leaders.update(best)

    def ordered(expr, maximize=False, source=None):
        model = (source or enc.model).clone()
        digits = enc.ordered_objective(model,expr)
        for digit in digits:
            model.maximize(digit) if maximize else model.minimize(digit)
            flag, solver = run(model)
            if flag != cp_model.OPTIMAL:
                return flag,solver,model
            if not isinstance(digit,int):
                model.add(digit == solver.value(digit))
        return flag,solver,model

    def extrema(expr):
        if all(v is None for v in expr.terms):
            v = expr.terms.get(None,F())
            return v,v
        flag, s, _ = ordered(expr)
        if flag != cp_model.OPTIMAL:
            raise TimeoutError()
        minimum = expr.value(s)
        flag, s, _ = ordered(expr,maximize=True)
        if flag != cp_model.OPTIMAL:
            raise TimeoutError()
        return minimum,expr.value(s)

    def varies(expr, witness):
        if all(v is None for v in expr.terms):
            return False
        try:
            goal, scale = enc.objective(expr)
        except PrecisionLimit:
            lo, hi = extrema(expr)
            return lo != hi
        model = enc.model.clone()
        model.clear_objective()
        model.add(goal != int(witness*scale))
        flag, _ = run(model)
        if flag == cp_model.INFEASIBLE:
            return False
        if flag not in (cp_model.FEASIBLE,cp_model.OPTIMAL):
            raise TimeoutError()
        return True

    try:
        publish_progress(state="running", phase="preparing")
        groups, records, edges, daily, ctx = prepare(cat,codes,policy,check)
        payload["warnings"] = ctx.warnings
        enc = Encoding(groups,records,edges,daily,ctx,policy,check)
        count_model = enc.model.clone() if timeout is None else None
        features = {}
        # Try a short fail-first construction before spending the whole request on exact search.
        neighbors = {k: set() for k in records}
        for a,b in edges:
            neighbors[a].add(b)
            neighbors[b].add(a)
        seed_limit = min(deadline, monotonic()+(min(0.2,timeout*0.05) if timeout is not None else 0.2))
        def construct(domains, chosen):
            if monotonic() >= seed_limit:
                return ()
            if not domains:
                answer = tuple(chosen[g] for g in groups)
                return answer if audit(cat,codes,answer,policy,ctx)[0]["passed"] else ()
            group = min(domains,key=lambda g:(len(domains[g]),g))
            for k in sorted(domains[group],key=lambda k:(len(neighbors[k]),k)):
                rest = {g:[r for r in domain if r not in neighbors[k]] for g,domain in domains.items() if g != group}
                if all(rest.values()):
                    result = construct(rest,chosen | {group:k})
                    if result:
                        return result
            return ()
        # Avoid unbounded recursion for unusually large course sets.
        if len(groups) < 200:
            seed = construct(groups,{})
        if not seed:
            flag, solver = run(enc.model)
            if flag == cp_model.INFEASIBLE:
                raise ProblemError("infeasible_proven", "The full model proves that the selected components, conflicts and hard rules cannot coexist.")
            if flag not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
                raise TimeoutError()
            seed = selection(solver)
        status = "feasible_unproven"
        seed_row = accepted(seed)
        for k,v in enc.x.items():
            enc.model.add_hint(v,int(k in seed))
        solver_phase = "model_build"
        publish_progress(state="running", phase=solver_phase,
                         branches=completed_branches, current_branches=0)
        features = enc.course_features() | enc.daily_features() | enc.weekly_feature()
        payload["search_model"] = {
            "course_pattern_space": enc.course_pattern_space,
            "course_patterns_kept": enc.course_patterns_kept,
        }
        _, baseline = audit(cat,codes,seed,policy,ctx)
        configured = {"T":[["T"]], "W":[["W"]], "H":[["early"],["periods"],["earliest","latest"]],
                      "D":[["gaps"],[k for k in sorted(features) if k.startswith("count:")]], "B":[["B"]]}
        solver_phase = "preference_calibration"
        publish_progress(state="running", phase=solver_phase,
                         branches=completed_branches, current_branches=0)
        pending = {}
        for category, stages in configured.items():
            stage_expressions = []
            stage_factors = []
            for stage in stages:
                expressions, factors = [], []
                for key in stage:
                    if key not in features:
                        continue
                    expr = features[key]
                    ref = baseline.get(key,F())
                    offset, factor = F(), F(1)
                    if key in {"W","periods"}:
                        lo, hi = extrema(expr)
                        payload["calibration"][key] = {"min_utility": str(lo), "max_utility": str(hi)}
                        if lo == hi:
                            continue
                        divisor = max(1,hi-lo)
                        offset, factor = hi/divisor,-F(1)/divisor
                    elif not varies(expr,ref):
                        continue
                    expressions.append(expr*factor+offset)
                    factors.append((key,offset,factor))
                if expressions:
                    stage_expressions.append(sum(expressions,Expression())/len(expressions))
                    stage_factors.append(factors)
            if stage_expressions:
                category_expr = sum(stage_expressions,Expression())/len(stage_expressions)
                ref = sum((sum((o+f*baseline.get(k,F()) for k,o,f in stage),F())/len(stage)
                           for stage in stage_factors),F())/len(stage_factors)
                if len(stage_expressions) == 1 and len(stage_factors[0]) == 1 or varies(category_expr,ref):
                    pending[category] = category_expr
                    transformations[category] = stage_factors
        active = pending
        solver_phase = "top_k_ranking"
        objective = sum((expr*policy.weights.get(k,3) for k,expr in active.items()),Expression())
        if active:
            objective /= sum(policy.weights.get(k,3) for k in active)
        seed_row = accepted(seed)
        if timeout is None:
            remember(seed_row)
        payload["active_categories"] = sorted(active)
        for rank in range(1,4):
            check()
            flag, solver, remaining = ordered(objective)
            if flag == cp_model.INFEASIBLE:
                status = "optimal"
                break
            if flag not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
                break
            candidate = selection(solver)
            seed_row = accepted(candidate,solver)
            if timeout is None:
                remember(seed_row)
            if flag != cp_model.OPTIMAL:
                try:
                    _, scale = enc.objective(objective)
                    safe_sum = sum(abs(int(c*scale))*(1 if v is None else enc.bounds[v])
                                   for v,c in objective.terms.items())
                    if active and safe_sum < 2**52:
                        bound = solver.best_objective_bound/scale
                        payload["objective_bound"] = {"rank":rank, "lower_loss":max(0,bound),
                            "gap":max(0,float(objective.value(solver))-bound)}
                except PrecisionLimit:
                    pass
                break
            enc.model.clear_hints()
            remaining.clear_hints()
            if active:
                payload["objective_bound"] = {"rank":rank,"lower_loss":float(objective.value(solver)), "gap":0}
            solver_phase = "tie_breaking"
            # Distributed tie-breaking is lexicographic on course/component and section code.
            # Batch mixed-radix digits so a rank normally needs only one tie solve.
            batch, radix = [], 1
            pending_batches = []
            for domain in groups.values():
                if len(domain) == 1:
                    continue
                if batch and radix*len(domain) > 2**42:
                    pending_batches.append(batch)
                    batch, radix = [], 1
                batch.append(domain)
                radix *= len(domain)
            if batch:
                pending_batches.append(batch)
            for chunk in pending_batches:
                expr = 0
                for domain in chunk:
                    expr = expr*len(domain)+sum(i*enc.x[k] for i,k in enumerate(domain))
                remaining.minimize(expr)
                flag, tie_solver = run(remaining)
                if flag != cp_model.OPTIMAL:
                    raise TimeoutError()
                candidate = selection(tie_solver)
                seed_row = accepted(candidate,tie_solver)
                if timeout is None:
                    remember(seed_row)
                remaining.add(expr == tie_solver.value(expr))
            check()
            seed_row.update(rank=rank,proven=True)
            payload["solutions"].append(seed_row)
            payload["certified_prefix"] += 1
            enc.model.add(sum(enc.x[k] for k in candidate) <= len(candidate)-1)
            seed_row = None
            solver_phase = "top_k_ranking"
        else:
            status = "optimal"
        if status == "optimal" or payload["certified_prefix"]:
            payload["proof_scope"] = "reference" if active else "feasibility_only"
        if status == "optimal" and count_model is not None:
            # The hard model has one assignment per section selection:
            # its auxiliary day loads, day flags and weekly counts are determined by the sections.
            solver_phase = "counting_schedules"
            counted = 0
            flag, _ = run(count_model, enumerate_schedules=True)
            if flag == cp_model.OPTIMAL:
                payload["qualified_schedule_count"] = str(counted)
    except TimeoutError:
        pass
    except PrecisionLimit:
        payload["warnings"].append("Exact integer scaling exceeds the CP-SAT safe range. Ranking is uncertified.")
    except ProblemError as exc:
        status = exc.status
        payload["errors"].append(str(exc))
    if status == "feasible_unproven" and seed_row and not any(
        tuple(row["selections"]) == tuple(seed_row["selections"]) for row in payload["solutions"]
    ):
        payload["solutions"].append(seed_row)
    if status == "infeasible_proven":
        payload["qualified_schedule_count"] = "0"
    runs = payload["solver_runs"]
    payload["search_summary"] = {
        "solver_calls": len(runs),
        "branches": sum(run["branches"] for run in runs),
        "conflicts": sum(run["conflicts"] for run in runs),
        "solver_wall_seconds": round(sum(run["wall_time_seconds"] for run in runs), 4),
    }
    payload.update(status=status, elapsed_ms=round((monotonic()-start)*1000,2))
    publish_progress(state="running", phase="finalizing",
                     branches=payload["search_summary"]["branches"], current_branches=0,
                     conflicts=payload["search_summary"]["conflicts"],
                     solver_run=len(runs), elapsed_ms=payload["elapsed_ms"],
                     result_status=status)
    return payload


def validate(cat,codes,policy,choices):
    try:
        _, _, _, _, ctx = prepare(cat,codes,policy,lambda: None)
    except ProblemError as exc:
        return {"passed":False, "status":exc.status,"errors":[str(exc)]}
    report, raw = audit(cat,codes,choices,policy,ctx)
    return {**report, "warnings":ctx.warnings, "raw_factors":{k:str(v) for k,v in raw.items()}}
