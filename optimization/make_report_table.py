#!/usr/bin/env python3
"""Render the validation summary as a markdown table for the report.

    python make_report_table.py --summary results/validation/validation_summary.json \
        --order nominal,transmission_matched,balanced,high_cooling,max_cooling,extreme_cooling
"""

from __future__ import annotations

import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--order", default="")
    args = ap.parse_args()

    s = json.load(open(args.summary))
    names = args.order.split(",") if args.order else list(s)
    names = [n for n in names if n in s]

    base = s.get("nominal")
    print("| design | params (BLS/Grad/Grad0/delf/pitch/dtRF/wedge) | "
          "transmission | cooling factor | eps6D_out (mm^3) | density gain vs nominal |")
    print("|---|---|---|---|---|---|")
    for n in names:
        d = s[n]
        p = d["designs"]
        pstr = (f"{p['BLS']:.1f}/{p['Grad']:.1f}/{p['Grad0']:.1f}/{p['delf']:.3f}/"
                f"{p['pitchFactor']:.2f}/{p['dtRF']:+.2f}/{p['wedgeScale']:.2f}")
        tm, ts = d["transmission"]
        cm, cs = d["cooling"]
        em, es = d["eps6d_out"]
        gain = ""
        if base:
            bt = base["transmission"][0]
            bc = base["cooling"][0]
            if bt > 0 and bc > 0:
                g = (tm / bt) * (cm / bc)
                gain = f"{g:.2f}x"
        print(f"| {n} | {pstr} | {tm:.3f} ± {ts:.3f} | {cm:.1f} ± {cs:.1f} | "
              f"{em:.1f} ± {es:.1f} | {gain} |")


if __name__ == "__main__":
    main()
