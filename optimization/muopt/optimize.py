"""Optimizer drivers for the (expensive, noisy, non-differentiable) HFOFO MC.

Each g4bl evaluation costs seconds-to-minutes and is stochastic, so we want a
*sample-efficient* black-box optimizer with a noise model -- not a gradient
method. Three backends are provided behind one interface:

  * ``bayes``  (default) -- Optuna TPE: robust, handles noise, parallelizes,
                            resumable via on-disk storage. Good general choice.
  * ``gp``     -- scikit-optimize Gaussian-process Bayesian optimization:
                  most sample-efficient in low dimensions / few evaluations.
  * ``random`` -- random search baseline (sanity check / embarrassingly parallel).

All backends share the same :class:`Trial` log (one CSV row per evaluation), so
results are comparable and analyzable regardless of optimizer.
"""

from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import asdict, dataclass, field

from .objective import EvalResult, ObjectiveConfig, evaluate
from .parameters import ParameterSpace
from .runner import G4blRunner


@dataclass
class Trial:
    number: int
    params: dict
    result: EvalResult


class TrialLogger:
    """Append-only CSV + JSONL log of every evaluation."""

    def __init__(self, out_dir, param_names):
        os.makedirs(out_dir, exist_ok=True)
        self.out_dir = out_dir
        self.param_names = param_names
        self.csv_path = os.path.join(out_dir, "trials.csv")
        self.jsonl_path = os.path.join(out_dir, "trials.jsonl")
        self._fields = (
            ["number", "score", "loss", "transmission", "cooling_factor",
             "eps6d_in", "eps6d_out", "n_in", "n_out", "ok", "wall_seconds"]
            + [f"p_{n}" for n in param_names]
        )
        with open(self.csv_path, "w", newline="") as fh:
            csv.writer(fh).writerow(self._fields)

    def log(self, trial: Trial):
        r = trial.result
        row = [trial.number, r.score, r.loss, r.transmission, r.cooling_factor,
               r.eps6d_in, r.eps6d_out, r.n_in, r.n_out, int(r.ok), r.wall_seconds]
        row += [trial.params.get(n) for n in self.param_names]
        with open(self.csv_path, "a", newline="") as fh:
            csv.writer(fh).writerow(row)
        with open(self.jsonl_path, "a") as fh:
            rec = {"number": trial.number, "params": trial.params,
                   "result": {k: v for k, v in asdict(r).items() if k != "extra"},
                   "extra": r.extra}
            fh.write(json.dumps(rec) + "\n")


def _make_eval(space: ParameterSpace, obj_cfg: ObjectiveConfig, runner: G4blRunner,
               logger: TrialLogger, state):
    """Return a function: raw params dict -> EvalResult (logged, best-tracked)."""
    def _eval(raw_params):
        params = space.clip(raw_params)
        result = evaluate(params, obj_cfg, runner)
        n = state["count"]
        logger.log(Trial(n, params, result))
        state["count"] += 1
        if state["best"] is None or result.score > state["best"].result.score:
            state["best"] = Trial(n, params, result)
        if state.get("verbose"):
            print(f"[trial {n:3d}] score={result.score:8.3f} "
                  f"T={result.transmission:5.3f} cool={result.cooling_factor:7.3f} "
                  f"params={ {k: round(v, 4) for k, v in params.items()} }")
        return result
    return _eval


def run_optimization(space, obj_cfg, runner, out_dir, method="bayes",
                     n_trials=60, n_jobs=1, seed=0, verbose=True, storage=None):
    """Drive ``method`` over ``space`` for ``n_trials`` evaluations.

    Returns ``(best_trial, logger)``.
    """
    logger = TrialLogger(out_dir, space.names)
    state = {"count": 0, "best": None, "verbose": verbose}
    _eval = _make_eval(space, obj_cfg, runner, logger, state)

    if method == "bayes":
        _run_optuna(space, _eval, n_trials, n_jobs, seed, storage, out_dir)
    elif method == "gp":
        _run_skopt(space, _eval, n_trials, seed)
    elif method == "random":
        _run_random(space, _eval, n_trials, seed)
    else:
        raise ValueError(f"unknown method: {method}")

    best = state["best"]
    if best is not None:
        with open(os.path.join(out_dir, "best.json"), "w") as fh:
            json.dump({"number": best.number, "params": best.params,
                       "score": best.result.score,
                       "transmission": best.result.transmission,
                       "cooling_factor": best.result.cooling_factor,
                       "eps6d_in": best.result.eps6d_in,
                       "eps6d_out": best.result.eps6d_out}, fh, indent=2)
    return best, logger


def _run_optuna(space, _eval, n_trials, n_jobs, seed, storage, out_dir):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        raw = {}
        for p in space:
            if p.integer:
                raw[p.name] = trial.suggest_int(p.name, int(p.low), int(p.high))
            else:
                raw[p.name] = trial.suggest_float(p.name, p.low, p.high, log=p.log)
        return _eval(raw).loss  # minimize loss = -score

    sampler = optuna.samplers.TPESampler(seed=seed, multivariate=True, group=True)
    study = optuna.create_study(
        direction="minimize", sampler=sampler,
        storage=storage, load_if_exists=bool(storage),
        study_name="hfofo",
    )
    study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs)


def _run_skopt(space, _eval, n_trials, seed):
    from skopt import gp_minimize
    from skopt.space import Integer, Real
    dims, names = [], []
    for p in space:
        names.append(p.name)
        if p.integer:
            dims.append(Integer(int(p.low), int(p.high), name=p.name))
        else:
            prior = "log-uniform" if p.log else "uniform"
            dims.append(Real(p.low, p.high, prior=prior, name=p.name))

    def objective(x):
        return _eval(dict(zip(names, x))).loss

    n_init = min(10, max(5, n_trials // 5))
    gp_minimize(objective, dims, n_calls=n_trials, n_initial_points=n_init,
                random_state=seed, acq_func="EI")


def _run_random(space, _eval, n_trials, seed):
    import random
    rng = random.Random(seed)
    for _ in range(n_trials):
        raw = {}
        for p in space:
            v = rng.uniform(p.low, p.high)
            raw[p.name] = int(round(v)) if p.integer else v
        _eval(raw)
