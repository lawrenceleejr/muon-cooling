#!/usr/bin/env python3
"""Decompose HFOFO transmission loss into decay vs. aperture/optics.

Runs the same design twice with an identical beam and seed:
  * decay ON   (physics QGSP_BIC)              -> observed transmission
  * decay OFF  (physics QGSP_BIC disable=Decay)-> aperture/optics-only survival

With the two runs, at every period plane:
  aperture survival  A(z) = N_off(z) / N_in       (muons kept by the optics)
  decay survival     S(z) = N_on(z)  / N_off(z)   (muons not yet decayed)
  observed           T(z) = N_on(z)  / N_in       (= A*S, factorized)

So the *decay-corrected transmission* the beam physicist wants -- "of the muons
that had not yet decayed, what fraction did we keep" -- is exactly A(z), the
decay-off curve. This script tabulates all three along the channel.

Uses the shuffled beam by default (representative momentum sampling; the shipped
initial.dat is momentum-ordered).

    python decompose_losses.py --params results/params_brightE2.json \
        --config config_phaseE.yaml --n-events 800 --out results/decomp_brightE2
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil

from muopt import metrics
from muopt.parameters import apply_parameters
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_optimization import build

PERIOD_MM = 4200.0
DET_Z0 = 50.2


def _prep(workdir, beam_file, disable_decay):
    card = os.path.join(workdir, "hfofo.in")
    txt = open(card).read()
    txt = txt.replace("file=initial.dat", f"file={beam_file}")
    if disable_decay:
        # disable muon (and all) decay so only aperture/optics losses remain
        txt = txt.replace("physics QGSP_BIC\n", "physics QGSP_BIC disable=Decay\n")
    open(card, "w").write(txt)


def _counts(workdir, p_low, p_high):
    out = {}
    for i in range(1, 32):
        p = os.path.join(workdir, f"out{i}.txt")
        if os.path.exists(p):
            out[i] = metrics.count_muons(metrics.read_detector(p), p_low, p_high)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", required=True)
    ap.add_argument("--config", default="config_phaseE.yaml")
    ap.add_argument("--n-events", type=int, default=800)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--beam", default="initial_shuffled.dat")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    space, obj_cfg, runner, _, _ = build(args.config, {"method": None, "n_trials": None, "out_dir": None})
    params = json.load(open(args.params))
    if "params" in params:
        params = params["params"]
    params = {k: v for k, v in params.items() if not k.startswith("_")}
    params["nEvents"] = args.n_events
    params["rngSeed"] = args.seed

    os.makedirs(args.out, exist_ok=True)
    results = {}
    for tag, disable in (("decay_on", False), ("decay_off", True)):
        wd = runner.make_workdir(obj_cfg.config_dir)
        apply_parameters(os.path.join(wd, "hfofo.in"), params)
        _prep(wd, args.beam, disable)
        print(f"running {tag} ({args.n_events} events, beam={args.beam}) ...", flush=True)
        run = runner.run(wd, "hfofo.in")
        if not run.success:
            print(f"  FAILED: {run.log.splitlines()[-5:]}")
            shutil.rmtree(wd, ignore_errors=True)
            return
        print(f"  done in {run.wall_seconds:.0f}s")
        results[tag] = _counts(wd, obj_cfg.p_low, obj_cfg.p_high)
        shutil.rmtree(wd, ignore_errors=True)

    on, off = results["decay_on"], results["decay_off"]
    n_in_on = on.get(1, 0)
    n_in_off = off.get(1, 0)

    rows = []
    for i in sorted(on):
        z = (DET_Z0 + PERIOD_MM * i) / 1000.0
        no, nf = on[i], off.get(i, 0)
        T = no / n_in_on if n_in_on else 0.0            # observed
        A = nf / n_in_off if n_in_off else 0.0           # aperture-only (decay corrected)
        S = (no / nf) if nf else 0.0                     # decay survival
        rows.append([i, round(z, 1), no, nf, round(T, 4), round(A, 4), round(S, 4)])

    with open(os.path.join(args.out, "decomposition.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["period", "z_m", "n_decay_on", "n_decay_off",
                    "T_observed", "A_aperture(decay_corrected)", "S_decay_survival"])
        w.writerows(rows)

    last = rows[-1]
    tot_loss = 1 - last[4]
    aperture_loss = 1 - last[5]
    decay_loss = 1 - last[6]
    print("\n=== exit (period {}) ===".format(last[0]))
    print(f"  observed transmission            T = {last[4]:.3f}  ({tot_loss*100:.0f}% lost)")
    print(f"  aperture/optics-only (decay-corr) A = {last[5]:.3f}  ({aperture_loss*100:.0f}% lost to apertures/optics)")
    print(f"  decay survival                    S = {last[6]:.3f}  ({decay_loss*100:.0f}% lost to decay)")
    print(f"  check A*S = {last[5]*last[6]:.3f}  vs T = {last[4]:.3f}")
    with open(os.path.join(args.out, "summary.json"), "w") as fh:
        json.dump({"params": params, "n_in_on": n_in_on, "n_in_off": n_in_off,
                   "T_observed": last[4], "A_aperture": last[5], "S_decay": last[6]}, fh, indent=2)
    print(f"\nwrote {args.out}/decomposition.csv")


if __name__ == "__main__":
    main()
