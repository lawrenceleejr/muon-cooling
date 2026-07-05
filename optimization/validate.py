#!/usr/bin/env python3
"""High-statistics, multi-seed validation of candidate designs.

The optimization runs on a fixed seed and moderate statistics (fast, noise-free
comparisons, but risks overfitting to one Monte-Carlo realization). This tool
re-evaluates chosen designs at high statistics across several independent seeds
and reports mean +/- spread for transmission, cooling, and exit emittance --
the numbers that go in the paper.

    python validate.py --designs designs.json --n-events 2000 --seeds 1,2,3 \
        --config config_phaseA.yaml --out results/validation

designs.json:  {"name": {"BLS": ..., "Grad": ...}, ...}
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from muopt.objective import evaluate
from run_optimization import build


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--designs", required=True)
    ap.add_argument("--config", default="config_phaseA.yaml",
                    help="yaml supplying runner/objective settings")
    ap.add_argument("--n-events", type=int, default=2000)
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--n-jobs", type=int, default=4)
    ap.add_argument("--out", default="results/validation")
    args = ap.parse_args()

    space, obj_cfg, runner, _, _ = build(
        args.config, {"method": None, "n_trials": None, "out_dir": None})
    obj_cfg.n_events = args.n_events

    with open(args.designs) as fh:
        designs = json.load(fh)
    seeds = [int(s) for s in args.seeds.split(",")]

    jobs = []
    for name, params in designs.items():
        for seed in seeds:
            p = dict(params)
            p["rngSeed"] = seed
            jobs.append((name, seed, p))

    def run(job):
        name, seed, params = job
        res = evaluate(params, obj_cfg, runner)
        print(f"  {name:16s} seed={seed}  T={res.transmission:5.3f} "
              f"cool={res.cooling_factor:9.2f} eps_out={res.eps6d_out:8.2f} "
              f"({res.wall_seconds:.0f}s)", flush=True)
        return name, seed, res

    print(f"validating {len(designs)} designs x {len(seeds)} seeds "
          f"@ {args.n_events} events, {args.n_jobs} workers")
    with ThreadPoolExecutor(max_workers=args.n_jobs) as ex:
        results = list(ex.map(run, jobs))

    os.makedirs(args.out, exist_ok=True)
    rows = []
    by_design = {}
    for name, seed, res in results:
        by_design.setdefault(name, []).append(res)
        rows.append([name, seed, res.transmission, res.cooling_factor,
                     res.eps6d_in, res.eps6d_out, res.score,
                     res.n_in, res.n_out])
    with open(os.path.join(args.out, "validation_runs.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["design", "seed", "transmission", "cooling_factor",
                    "eps6d_in", "eps6d_out", "score", "n_in", "n_out"])
        w.writerows(rows)

    def mean_std(vals):
        m = statistics.fmean(vals)
        s = statistics.stdev(vals) if len(vals) > 1 else 0.0
        return m, s

    summary = {}
    print(f"\n{'design':16s} {'T':>14s} {'cooling':>18s} {'eps6d_out':>16s} {'score':>12s}")
    for name, rs in by_design.items():
        tm, ts = mean_std([r.transmission for r in rs])
        cm, cs = mean_std([r.cooling_factor for r in rs])
        em, es = mean_std([r.eps6d_out for r in rs])
        sm, ss = mean_std([r.score for r in rs])
        summary[name] = {"designs": designs[name],
                         "transmission": [tm, ts], "cooling": [cm, cs],
                         "eps6d_out": [em, es], "score": [sm, ss]}
        print(f"{name:16s} {tm:7.3f}±{ts:5.3f} {cm:11.1f}±{cs:7.1f} "
              f"{em:9.2f}±{es:5.2f} {sm:6.2f}±{ss:4.2f}")

    with open(os.path.join(args.out, "validation_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\nwrote {args.out}/validation_runs.csv and validation_summary.json")


if __name__ == "__main__":
    main()
