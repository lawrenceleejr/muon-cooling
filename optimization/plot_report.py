#!/usr/bin/env python3
"""Publication figures comparing channel profiles (baseline vs optimized).

Takes two or more profile.csv files from profile_channel.py and overlays
transmission and emittance evolution along the channel.

    python plot_report.py --profiles baseline=results/profile_nominal/profile.csv \
        optimized=results/profile_best/profile.csv --out docs/campaign
"""

from __future__ import annotations

import argparse
import csv
import os


def load_profile(path):
    rows = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            if r["eps6d"]:
                rows.append({k: float(v) for k, v in r.items()})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profiles", nargs="+", required=True,
                    help="name=path/to/profile.csv ...")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    profiles = {}
    for spec in args.profiles:
        name, path = spec.split("=", 1)
        profiles[name] = load_profile(path)
    os.makedirs(args.out, exist_ok=True)

    colors = {"baseline": "#888888", "optimized": "#C23B22"}

    def color(name, i):
        return colors.get(name, f"C{i}")

    # --- transmission vs z ---------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for i, (name, rows) in enumerate(profiles.items()):
        n0 = rows[0]["n_mu"]
        ax.plot([r["z_m"] for r in rows], [r["n_mu"] / n0 for r in rows],
                "-o", ms=3.5, color=color(name, i), label=name)
    ax.set_xlabel("z (m)")
    ax.set_ylabel("muon survival  $N(z)/N_1$")
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.25)
    ax.legend()
    ax.set_title("Transmission along the HFOFO channel")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "transmission_vs_z.png"), dpi=170)
    plt.close(fig)

    # --- 6D emittance vs z (log) --------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for i, (name, rows) in enumerate(profiles.items()):
        ax.semilogy([r["z_m"] for r in rows], [r["eps6d"] for r in rows],
                    "-o", ms=3.5, color=color(name, i), label=name)
    ax.set_xlabel("z (m)")
    ax.set_ylabel(r"$\epsilon_{6D}$  (mm$^3$)")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    ax.set_title("6D emittance along the HFOFO channel")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "eps6d_vs_z.png"), dpi=170)
    plt.close(fig)

    # --- eigen-emittances vs z ----------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharex=True)
    labels = [r"$\epsilon_1$ (mm)", r"$\epsilon_2$ (mm)", r"$\epsilon_3$ (mm)"]
    for j, key in enumerate(["eps1", "eps2", "eps3"]):
        for i, (name, rows) in enumerate(profiles.items()):
            axes[j].semilogy([r["z_m"] for r in rows], [r[key] for r in rows],
                             "-o", ms=3, color=color(name, i), label=name)
        axes[j].set_xlabel("z (m)")
        axes[j].set_ylabel(labels[j])
        axes[j].grid(alpha=0.25, which="both")
    axes[0].legend()
    fig.suptitle("Normalized eigen-emittances along the channel")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "eigen_emittances_vs_z.png"), dpi=170)
    plt.close(fig)

    # --- phase-space density gain vs z ---------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for i, (name, rows) in enumerate(profiles.items()):
        n0, e0 = rows[0]["n_mu"], rows[0]["eps6d"]
        gain = [(r["n_mu"] / n0) * (e0 / r["eps6d"]) for r in rows]
        ax.semilogy([r["z_m"] for r in rows], gain, "-o", ms=3.5,
                    color=color(name, i), label=name)
    ax.set_xlabel("z (m)")
    ax.set_ylabel(r"6D density gain  $T \cdot \epsilon_{6D,1}/\epsilon_{6D}(z)$")
    ax.grid(alpha=0.25, which="both")
    ax.legend()
    ax.set_title("Phase-space density gain (the merit) along the channel")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "density_gain_vs_z.png"), dpi=170)
    plt.close(fig)

    print(f"wrote 4 figures to {args.out}")


if __name__ == "__main__":
    main()
