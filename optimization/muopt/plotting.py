"""Summary plots for an optimization run (reads trials.csv)."""

from __future__ import annotations

import csv
import os


def _load(csv_path):
    rows = []
    with open(csv_path) as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    return rows


def plot_summary(csv_path, out_dir, param_names):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rows = _load(csv_path)
    if not rows:
        return
    num = np.array([float(r["number"]) for r in rows])
    score = np.array([float(r["score"]) for r in rows])
    trans = np.array([float(r["transmission"]) for r in rows])
    cool = np.array([float(r["cooling_factor"]) for r in rows])
    ok = np.array([int(r["ok"]) for r in rows], dtype=bool)

    finite = np.isfinite(score)
    best_so_far = np.maximum.accumulate(np.where(finite, score, -np.inf))

    # 1) convergence
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(num[finite], score[finite], ".", alpha=0.4, label="trial score")
    ax.plot(num, best_so_far, "-", color="C3", label="best so far")
    ax.set_xlabel("trial"); ax.set_ylabel("log-merit score")
    ax.set_title("Optimization convergence"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(out_dir, "convergence.png"), dpi=150)
    plt.close(fig)

    # 2) transmission vs cooling trade-off (Pareto view)
    good = ok & np.isfinite(cool) & (cool > 0)
    if good.any():
        fig, ax = plt.subplots(figsize=(6, 5))
        sc = ax.scatter(trans[good], cool[good], c=score[good], cmap="viridis", s=30)
        ax.set_xlabel("transmission"); ax.set_ylabel("cooling factor  (eps6d_in/out)")
        ax.set_title("Transmission vs. cooling trade-off")
        fig.colorbar(sc, label="log-merit score")
        fig.tight_layout(); fig.savefig(os.path.join(out_dir, "tradeoff.png"), dpi=150)
        plt.close(fig)

    # 3) per-parameter slices
    n = len(param_names)
    if n:
        fig, axes = plt.subplots(1, n, figsize=(3.2 * n, 3.2), squeeze=False)
        for j, name in enumerate(param_names):
            vals = np.array([float(r[f"p_{name}"]) for r in rows])
            ax = axes[0][j]
            m = finite
            ax.scatter(vals[m], score[m], c=score[m], cmap="viridis", s=18)
            ax.set_xlabel(name); ax.set_ylabel("score" if j == 0 else "")
        fig.suptitle("Score vs. each parameter")
        fig.tight_layout(); fig.savefig(os.path.join(out_dir, "parameters.png"), dpi=150)
        plt.close(fig)
