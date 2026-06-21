#!/usr/bin/env python3
"""Compare optimizer sample-efficiency on the HFOFO objective.

Runs the same objective under several optimizers with an identical evaluation
budget and plots best-so-far vs. trial. This is the "which way is most efficient"
experiment: a good optimizer should reach a high merit in far fewer expensive
g4bl evaluations than random search.

    python compare_optimizers.py --n-trials 25 --n-events 150 --methods bayes,gp,random
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from muopt import G4blRunner, ObjectiveConfig, ParameterSpace, detect_backend
from muopt.optimize import run_optimization

SPACE = {
    "BLS":   {"low": 18.0, "high": 25.0, "nominal": 21.4},
    "Grad":  {"low": 18.0, "high": 32.0, "nominal": 25.0},
    "Grad0": {"low": 14.0, "high": 26.0, "nominal": 20.0},
    "delf":  {"low": -0.10, "high": 0.10, "nominal": 0.0},
}


def best_so_far(csv_path):
    best, out = float("-inf"), []
    with open(csv_path) as fh:
        for row in csv.DictReader(fh):
            s = float(row["score"])
            if s == s:  # not NaN
                best = max(best, s)
            out.append(best)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-trials", type=int, default=25)
    ap.add_argument("--n-events", type=int, default=150)
    ap.add_argument("--n-jobs", type=int, default=3)
    ap.add_argument("--methods", default="bayes,gp,random")
    ap.add_argument("--out-dir", default="results/comparison")
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    out_root = os.path.join(base, args.out_dir)
    os.makedirs(out_root, exist_ok=True)

    space = ParameterSpace.from_config(SPACE)
    backend = detect_backend()
    runner = G4blRunner(backend=backend, timeout=600)
    # Interior detectors isolate steady-state cooling from period-1 halo scraping.
    obj_cfg = ObjectiveConfig(
        config_dir=os.path.join(base, "..", "hfofo"),
        n_events=args.n_events,
        entrance_detector="out3.txt", exit_detector="out28.txt",
        transmission_floor=0.05,
    )

    curves = {}
    for method in args.methods.split(","):
        method = method.strip()
        out_dir = os.path.join(out_root, method)
        print(f"\n### {method} ({args.n_trials} trials, {args.n_events} events) ###")
        best, logger = run_optimization(
            space, obj_cfg, runner, out_dir, method=method,
            n_trials=args.n_trials, n_jobs=args.n_jobs, seed=0, verbose=False)
        curves[method] = best_so_far(logger.csv_path)
        if best:
            print(f"  best score={best.result.score:.3f} T={best.result.transmission:.3f} "
                  f"cooling={best.result.cooling_factor:.2f} params={best.params}")

    # Plot best-so-far comparison.
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for method, curve in curves.items():
            ax.plot(range(1, len(curve) + 1), curve, marker=".", label=method)
        ax.set_xlabel("evaluations")
        ax.set_ylabel("best merit score so far")
        ax.set_title("Optimizer sample-efficiency on the HFOFO objective")
        ax.legend()
        fig.tight_layout()
        path = os.path.join(out_root, "efficiency_comparison.png")
        fig.savefig(path, dpi=150)
        print(f"\nwrote {path}")
    except Exception as exc:
        print(f"(plot skipped: {exc})")

    # Also dump the curves as CSV for the writeup.
    with open(os.path.join(out_root, "best_so_far.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["evaluation"] + list(curves))
        n = max(len(c) for c in curves.values())
        for i in range(n):
            w.writerow([i + 1] + [c[i] if i < len(c) else "" for c in curves.values()])


if __name__ == "__main__":
    main()
