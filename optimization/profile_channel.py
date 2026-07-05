#!/usr/bin/env python3
"""Full-channel profile of a design: emittance and muon count at every period.

Runs one simulation keeping all 31 per-period detectors and tabulates the
evolution of the eigen-emittances, 6D emittance, muon count and mean momentum
along the channel. This produces the per-period data behind the
"emittance vs z" and "transmission vs z" figures in the report.

    python profile_channel.py --params best.json --n-events 2000 \
        --out results/profile_best [--config config_phaseA.yaml] [--keep]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from muopt import metrics
from muopt.parameters import apply_parameters
from run_optimization import build

PERIOD_MM = 4200.0
DET_Z0 = 50.2  # Det_i sits at z = -9.8 + 60 + 4200*i


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", required=True,
                    help="JSON file: either a bare param dict or {'params': {...}}")
    ap.add_argument("--config", default="config_phaseA.yaml")
    ap.add_argument("--n-events", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep", action="store_true",
                    help="keep the raw g4bl working directory next to the CSV")
    args = ap.parse_args()

    space, obj_cfg, runner, _, _ = build(
        args.config, {"method": None, "n_trials": None, "out_dir": None})

    with open(args.params) as fh:
        params = json.load(fh)
    if "params" in params and isinstance(params["params"], dict):
        params = params["params"]
    params = dict(params)
    params["nEvents"] = args.n_events
    params["rngSeed"] = args.seed

    os.makedirs(args.out, exist_ok=True)
    workdir = runner.make_workdir(obj_cfg.config_dir)
    apply_parameters(os.path.join(workdir, obj_cfg.input_file), params)
    print(f"running {args.n_events} events ... (params={params})")
    run = runner.run(workdir, obj_cfg.input_file)
    if not run.success:
        print("g4bl FAILED:\n" + "\n".join(run.log.splitlines()[-10:]))
        sys.exit(1)
    print(f"done in {run.wall_seconds:.0f}s")

    rows = []
    for i in range(1, 32):
        path = os.path.join(workdir, f"out{i}.txt")
        if not os.path.exists(path):
            continue
        d = metrics.read_detector(path)
        n = metrics.count_muons(d, obj_cfg.p_low, obj_cfg.p_high)
        e = metrics.compute_emittance(d, obj_cfg.p0, obj_cfg.Bz0,
                                      obj_cfg.p_low, obj_cfg.p_high)
        z_m = (DET_Z0 + PERIOD_MM * i) / 1000.0
        if e:
            rows.append([i, z_m, n, e.eps_x, e.eps_y, e.eps_z, e.eps_6d,
                         e.mean_momentum])
        else:
            rows.append([i, z_m, n] + [""] * 5)

    csv_path = os.path.join(args.out, "profile.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["period", "z_m", "n_mu", "eps1", "eps2", "eps3",
                    "eps6d", "mean_p"])
        w.writerows(rows)
    with open(os.path.join(args.out, "params.json"), "w") as fh:
        json.dump(params, fh, indent=2)
    print(f"wrote {csv_path} ({len(rows)} planes)")

    if args.keep:
        dst = os.path.join(args.out, "g4bl_workdir")
        shutil.rmtree(dst, ignore_errors=True)
        shutil.move(workdir, dst)
        print(f"kept raw output in {dst}")
    else:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
