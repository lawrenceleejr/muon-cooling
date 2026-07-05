#!/usr/bin/env python3
"""Map the transmission-vs-cooling Pareto front with multi-objective Bayesian
optimization (Optuna NSGA-II).

Instead of collapsing the two goals into one scalar, this treats
(transmission, cooling factor) as separate objectives and evolves the
non-dominated set. The result is the actual trade-off curve the channel offers,
from which a design point can be chosen with full knowledge of what each extra
percent of transmission costs in cooling (and vice versa).

    python pareto.py --config config_phaseB.yaml
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from muopt.objective import evaluate
from muopt.optimize import Trial, TrialLogger
from run_optimization import build


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--n-trials", type=int, dest="n_trials")
    ap.add_argument("--population", type=int, default=24)
    args = ap.parse_args()

    space, obj_cfg, runner, opt_kw, out_dir = build(
        args.config, {"method": None, "n_trials": args.n_trials, "out_dir": None})
    n_trials = opt_kw["n_trials"]
    n_jobs = opt_kw["n_jobs"]
    seed = opt_kw["seed"]

    os.makedirs(out_dir, exist_ok=True)
    logger = TrialLogger(out_dir, space.names)
    state = {"count": logger.n_existing}

    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        raw = {}
        for p in space:
            raw[p.name] = trial.suggest_float(p.name, p.low, p.high, log=p.log)
        params = space.clip(raw)
        res = evaluate(params, obj_cfg, runner)
        n = state["count"]
        state["count"] += 1
        logger.log(Trial(n, params, res))
        cool = res.cooling_factor if math.isfinite(res.cooling_factor) else 0.0
        print(f"[trial {n:3d}] T={res.transmission:5.3f} cool={cool:9.2f} "
              f"params={ {k: round(v, 4) for k, v in params.items()} }", flush=True)
        # maximize both; log-cooling keeps the second objective well-scaled
        return res.transmission, math.log10(max(cool, 1e-3))

    storage = "sqlite:///" + os.path.join(os.path.abspath(out_dir), "study.db")
    sampler = optuna.samplers.NSGAIISampler(population_size=args.population, seed=seed)
    study = optuna.create_study(directions=["maximize", "maximize"],
                                sampler=sampler, storage=storage,
                                study_name="hfofo_pareto", load_if_exists=True)
    study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs)

    front = []
    for t in study.best_trials:
        front.append({"number": t.number, "params": t.params,
                      "transmission": t.values[0],
                      "log10_cooling": t.values[1]})
    front.sort(key=lambda d: -d["transmission"])
    with open(os.path.join(out_dir, "pareto_front.json"), "w") as fh:
        json.dump(front, fh, indent=2)
    print(f"\nPareto front: {len(front)} non-dominated designs "
          f"-> {out_dir}/pareto_front.json")
    for d in front:
        print(f"  T={d['transmission']:5.3f}  cooling=10^{d['log10_cooling']:5.2f}  "
              f"{ {k: round(v, 3) for k, v in d['params'].items()} }")


if __name__ == "__main__":
    main()
