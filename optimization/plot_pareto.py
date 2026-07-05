#!/usr/bin/env python3
"""Plot the transmission-vs-cooling Pareto front from a Pareto run's trials.csv.

Shows every evaluated design as a faint point, the non-dominated front as a
highlighted staircase, and marks the nominal design and any named candidates.

    python plot_pareto.py --trials results/phaseB2/trials.csv \
        --out docs/campaign --nominal T=0.646,cool=63
"""

from __future__ import annotations

import argparse
import csv
import os


def load(path):
    T, C, ok = [], [], []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            try:
                t = float(r["transmission"])
                c = float(r["cooling_factor"])
            except ValueError:
                continue
            if int(r["ok"]) and c > 0:
                T.append(t)
                C.append(c)
    return T, C


def pareto_front(T, C):
    """Indices of non-dominated points (maximize both T and C)."""
    idx = sorted(range(len(T)), key=lambda i: -T[i])
    front, best_c = [], -1.0
    for i in idx:
        if C[i] > best_c:
            front.append(i)
            best_c = C[i]
    return front


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trials", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nominal", default="", help="T=..,cool=..")
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    T, C = load(args.trials)
    if not T:
        print("no successful trials")
        return
    os.makedirs(args.out, exist_ok=True)

    front = pareto_front(T, C)
    fx = [T[i] for i in front]
    fy = [C[i] for i in front]
    order = sorted(range(len(fx)), key=lambda k: fx[k])
    fx = [fx[k] for k in order]
    fy = [fy[k] for k in order]

    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.scatter(T, C, s=14, c="#b0c4de", alpha=0.6, label="evaluated designs")
    ax.plot(fx, fy, "-o", color="#C23B22", ms=5, lw=1.8, label="Pareto front")

    if args.nominal:
        kv = dict(p.split("=") for p in args.nominal.split(","))
        nt, nc = float(kv["T"]), float(kv["cool"])
        ax.scatter([nt], [nc], marker="*", s=280, color="#1f3b73",
                   edgecolor="white", zorder=5, label="nominal design")

    ax.set_yscale("log")
    ax.set_xlabel("transmission  $N_{31}/N_1$")
    ax.set_ylabel(r"cooling factor  $\epsilon_{6D,2}/\epsilon_{6D,31}$")
    ax.set_title("HFOFO transmission vs. cooling: Pareto front")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    fig.tight_layout()
    path = os.path.join(args.out, "pareto_front.png")
    fig.savefig(path, dpi=170)
    print(f"wrote {path}  ({len(front)} non-dominated of {len(T)} designs)")


if __name__ == "__main__":
    main()
