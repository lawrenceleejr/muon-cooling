#!/usr/bin/env python3
"""CLI entry point for HFOFO cooling-channel optimization.

    python run_optimization.py --config config.yaml
    python run_optimization.py --config config.yaml --method gp --n-trials 40
    python run_optimization.py --config config.yaml --baseline   # nominal point only

Reads config.yaml, runs the chosen optimizer, writes a trial log + best.json +
summary plots into out_dir.
"""

from __future__ import annotations

import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from muopt import G4blRunner, ObjectiveConfig, ParameterSpace, detect_backend, evaluate
from muopt.optimize import run_optimization


def build(config_path, overrides):
    with open(config_path) as fh:
        cfg = yaml.safe_load(fh)
    base = os.path.dirname(os.path.abspath(config_path))

    config_dir = os.path.normpath(os.path.join(base, cfg["config_dir"]))
    space = ParameterSpace.from_config(cfg["parameters"])

    rcfg = cfg.get("runner", {})
    backend = rcfg.get("backend", "auto")
    if backend == "auto":
        backend = detect_backend()
    runner = G4blRunner(backend=backend, image=rcfg.get("image", G4blRunner.image),
                        timeout=float(rcfg.get("timeout", 1200)))

    ocfg = cfg.get("objective", {})
    obj_cfg = ObjectiveConfig(
        config_dir=config_dir,
        input_file=cfg.get("input_file", "hfofo.in"),
        entrance_detector=ocfg.get("entrance_detector", "out1.txt"),
        exit_detector=ocfg.get("exit_detector", "out31.txt"),
        n_events=int(ocfg.get("n_events", 200)),
        p0=float(ocfg.get("p0", 247.5)),
        Bz0=float(ocfg.get("Bz0", 2.8)),
        p_low=float(ocfg.get("p_low", 100.0)),
        p_high=float(ocfg.get("p_high", 400.0)),
        transmission_floor=float(ocfg.get("transmission_floor", 0.0)),
        transmission_weight=float(ocfg.get("transmission_weight", 1.0)),
        cooling_weight=float(ocfg.get("cooling_weight", 1.0)),
        trans_entrance_detector=ocfg.get("trans_entrance_detector", ""),
    )

    opt = cfg.get("optimizer", {})
    opt_kw = dict(
        method=overrides.get("method") or opt.get("method", "bayes"),
        n_trials=overrides.get("n_trials") or int(opt.get("n_trials", 60)),
        n_jobs=int(opt.get("n_jobs", 1)),
        seed=int(opt.get("seed", 0)),
        storage=opt.get("storage"),
    )
    out_dir = os.path.normpath(os.path.join(base, overrides.get("out_dir")
                                            or cfg.get("out_dir", "results/run")))
    return space, obj_cfg, runner, opt_kw, out_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--method", choices=["bayes", "gp", "random"])
    ap.add_argument("--n-trials", type=int, dest="n_trials")
    ap.add_argument("--out-dir", dest="out_dir")
    ap.add_argument("--baseline", action="store_true",
                    help="evaluate only the nominal design point and exit")
    args = ap.parse_args()

    space, obj_cfg, runner, opt_kw, out_dir = build(
        args.config, {"method": args.method, "n_trials": args.n_trials,
                      "out_dir": args.out_dir})

    print(f"backend={runner.backend}  config={obj_cfg.config_dir}  out={out_dir}")
    print(f"parameters: {space.names}")

    if args.baseline:
        os.makedirs(out_dir, exist_ok=True)
        res = evaluate(space.nominal(), obj_cfg, runner)
        print(f"nominal: score={res.score:.3f} T={res.transmission:.3f} "
              f"cooling={res.cooling_factor:.3f} "
              f"eps6d {res.eps6d_in:.1f} -> {res.eps6d_out:.1f}  ({res.message})")
        return

    best, logger = run_optimization(space, obj_cfg, runner, out_dir, **opt_kw)
    if best is None:
        print("no successful trials")
        return
    print("\n=== best ===")
    print(f"  score={best.result.score:.3f}  T={best.result.transmission:.3f}  "
          f"cooling={best.result.cooling_factor:.3f}")
    print(f"  eps6d {best.result.eps6d_in:.1f} -> {best.result.eps6d_out:.1f}")
    print(f"  params={best.params}")

    try:
        from muopt.plotting import plot_summary
        plot_summary(logger.csv_path, out_dir, space.names)
        print(f"  plots written to {out_dir}")
    except Exception as exc:  # plotting is optional
        print(f"  (plotting skipped: {exc})")


if __name__ == "__main__":
    main()
