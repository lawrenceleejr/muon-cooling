#!/usr/bin/env python3
"""Headline figure: delivered 6D brightness gain vs nominal, with error bars.

Brightness = transmission / eps6D(exit), the delivered 6D phase-space density
against the common injected beam. Reads a validation_summary.json.

    python plot_brightness.py --summary results/validation2/validation_summary.json --out docs/campaign
"""
from __future__ import annotations
import argparse, json, os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    s = json.load(open(args.summary))
    nb = s["nominal"]["transmission"][0] / s["nominal"]["eps6d_out"][0]

    items = []
    for n, d in s.items():
        t, ts = d["transmission"]
        e, es = d["eps6d_out"]
        gain = (t / e) / nb
        # 1st-order error propagation on gain from T and eps spreads
        rel = np.hypot(ts / t if t else 0, es / e if e else 0)
        items.append((gain, gain * rel, n, t, ts, e, es))
    items.sort(reverse=True)

    names = [i[2] for i in items]
    gains = [i[0] for i in items]
    errs = [i[1] for i in items]
    colors = ["#C23B22" if n == "balanced" else
              ("#1f3b73" if n == "nominal" else "#8a8a8a") for n in names]

    fig, ax = plt.subplots(figsize=(8, 4.6))
    y = range(len(names))
    ax.barh(list(y), gains, xerr=errs, color=colors, alpha=0.9,
            error_kw=dict(ecolor="#333", lw=1.2, capsize=4))
    ax.axvline(1.0, color="#1f3b73", ls="--", lw=1, label="nominal")
    ax.set_yticks(list(y))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel(r"delivered 6D brightness gain  $(T/\epsilon_{6D,\mathrm{exit}})$ / nominal")
    ax.set_title("HFOFO designs vs. nominal (validated, common injected beam)")
    for yi, g, e in zip(y, gains, errs):
        ax.text(g + e + 0.02, yi, f"{g:.2f}×", va="center", fontsize=9)
    ax.set_xlim(0, max(gains) + max(errs) + 0.2)
    ax.legend(loc="lower right")
    fig.tight_layout()
    path = os.path.join(args.out, "brightness_gain.png")
    fig.savefig(path, dpi=170)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
