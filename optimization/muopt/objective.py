"""Turn a point in parameter space into a single scalar to optimize.

The HFOFO cooling problem trades two competing goals:

  * **cooling**       -- shrink the 6D emittance  (eps6D_out << eps6D_in)
  * **transmission**  -- keep the muons           (T = N_out / N_in -> 1)

The natural combined figure of merit is the gain in 6D phase-space *density*,

    M = transmission * (eps6D_in / eps6D_out)

i.e. "how many more muons per unit 6D phase-space volume come out than went in".
Maximizing M rewards cooling and penalizes losing beam. Because emittances span
orders of magnitude we optimize ``score = log(M)``; the driver minimizes
``-score``. A failed/under-populated run returns a finite penalty so the
surrogate model can still learn the infeasible region instead of crashing.

The objective is intentionally configurable (weights, transmission floor,
alternate forms) without touching the optimizer.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

from . import metrics
from .parameters import apply_parameters
from .runner import G4blRunner

PENALTY = 50.0  # -score returned for an infeasible/failed evaluation


@dataclass
class ObjectiveConfig:
    config_dir: str                       # directory holding hfofo.in + includes
    input_file: str = "hfofo.in"
    entrance_detector: str = "out1.txt"   # cooling reference plane (emittance in)
    exit_detector: str = "out31.txt"      # exit plane (emittance out)
    # Transmission may use a different entrance plane than the emittance ratio
    # (e.g. count survival from period 1 but measure cooling from period 2 to
    # avoid crediting entrance-mismatch scraping as "cooling"). Defaults to the
    # same planes.
    trans_entrance_detector: str = ""
    n_events: int = 200
    p0: float = 247.5
    Bz0: float = 2.8
    p_low: float = 100.0
    p_high: float = 400.0
    # objective shaping
    transmission_floor: float = 0.0       # below this T, apply soft penalty
    transmission_weight: float = 1.0      # exponent on T in the merit
    cooling_weight: float = 1.0           # exponent on (eps_in/eps_out)
    # "density_gain": merit = T^wT * (eps_in/eps_out)^wcool   (entrance-referenced)
    # "brightness":   merit = T^wT / eps_out^wcool            (common injected beam)
    # The brightness mode is the physically honest objective -- it does not credit
    # a design for heating the beam at injection and then recovering.
    mode: str = "density_gain"
    cleanup: bool = True


@dataclass
class EvalResult:
    score: float                          # log-merit (higher is better)
    transmission: float = 0.0
    transmission_corrected: float = float("nan")  # decay-corrected (aperture/optics survival)
    decay_survival: float = float("nan")          # muon-decay survival in→out
    eps6d_in: float = float("nan")
    eps6d_out: float = float("nan")
    cooling_factor: float = float("nan")  # eps6d_in / eps6d_out
    n_in: int = 0
    n_out: int = 0
    wall_seconds: float = 0.0
    ok: bool = False
    message: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def loss(self):
        """What the minimizer drives down."""
        return -self.score


def score_from_metrics(trans, eps_in, eps_out, cfg: ObjectiveConfig):
    """The merit score for given metrics under ``cfg`` (shared by evaluate() and
    warm-start rescoring). Returns None if the metrics are infeasible."""
    if eps_out is None or eps_out <= 0:
        return None
    if cfg.mode != "brightness" and (eps_in is None or eps_in <= 0):
        return None
    if cfg.mode == "brightness":
        merit = (max(trans, 1e-6) ** cfg.transmission_weight) / (eps_out ** cfg.cooling_weight)
    else:
        merit = (max(trans, 1e-6) ** cfg.transmission_weight) * ((eps_in / eps_out) ** cfg.cooling_weight)
    score = math.log(max(merit, 1e-30))
    if trans < cfg.transmission_floor:
        score -= 5.0 * (cfg.transmission_floor - trans)
    return float(score)


def evaluate(values, cfg: ObjectiveConfig, runner: G4blRunner) -> EvalResult:
    """Run one HFOFO simulation for parameter dict ``values`` and score it."""
    workdir = runner.make_workdir(cfg.config_dir)
    try:
        card = os.path.join(workdir, cfg.input_file)
        to_set = dict(values)
        to_set.setdefault("nEvents", cfg.n_events)
        apply_parameters(card, to_set)

        run = runner.run(workdir, cfg.input_file)
        if not run.success:
            tail = "\n".join(run.log.splitlines()[-8:])
            return EvalResult(score=-PENALTY, ok=False, wall_seconds=run.wall_seconds,
                              message=f"g4bl failed (rc={run.returncode})\n{tail}")

        ent = metrics.read_detector(os.path.join(workdir, cfg.entrance_detector))
        ex = metrics.read_detector(os.path.join(workdir, cfg.exit_detector))

        emit_in = metrics.compute_emittance(ent, cfg.p0, cfg.Bz0, cfg.p_low, cfg.p_high)
        emit_out = metrics.compute_emittance(ex, cfg.p0, cfg.Bz0, cfg.p_low, cfg.p_high)

        if cfg.trans_entrance_detector:
            tent = metrics.read_detector(
                os.path.join(workdir, cfg.trans_entrance_detector))
        else:
            tent = ent
        n_in = metrics.count_muons(tent, cfg.p_low, cfg.p_high)
        n_out = metrics.count_muons(ex, cfg.p_low, cfg.p_high)
        trans = metrics.transmission(n_in, n_out)
        # Decay-corrected (aperture/optics) transmission -- always reported.
        _, trans_corr, s_decay = metrics.decay_corrected_transmission(
            tent, ex, cfg.p_low, cfg.p_high)

        # "transmission" mode only needs survival; others need the exit emittance.
        need_out = cfg.mode not in ("transmission", "transmission_corrected")
        need_in = cfg.mode == "density_gain"
        if (need_out and (emit_out is None or emit_out.eps_6d <= 0)) or \
           (need_in and emit_in is None):
            # Beam died / too few survivors to define emittance: feasible-but-bad.
            score = -PENALTY + 10.0 * trans  # gradient toward keeping beam alive
            return EvalResult(score=score, ok=True, transmission=trans,
                              transmission_corrected=trans_corr, decay_survival=s_decay,
                              n_in=n_in, n_out=n_out, wall_seconds=run.wall_seconds,
                              eps6d_in=(emit_in.eps_6d if emit_in else float("nan")),
                              message="insufficient survivors for emittance")

        eps_out = emit_out.eps_6d if emit_out else float("nan")
        cooling = (emit_in.eps_6d / eps_out) if (emit_in and emit_out) else float("nan")
        if cfg.mode == "transmission":
            merit = max(trans, 1e-6)                       # raw muon transmission
        elif cfg.mode == "transmission_corrected":
            merit = max(trans_corr, 1e-6)                  # aperture/optics survival
        elif cfg.mode == "brightness":
            # merit = T^wT / eps_out^wcool  (delivered 6D density, common beam)
            merit = (max(trans, 1e-6) ** cfg.transmission_weight) / (eps_out ** cfg.cooling_weight)
        else:
            merit = (max(trans, 1e-6) ** cfg.transmission_weight) * (cooling ** cfg.cooling_weight)
        score = math.log(max(merit, 1e-30))
        if trans < cfg.transmission_floor:
            score -= 5.0 * (cfg.transmission_floor - trans)

        return EvalResult(
            score=float(score), ok=True, transmission=trans,
            transmission_corrected=trans_corr, decay_survival=s_decay,
            eps6d_in=(emit_in.eps_6d if emit_in else float("nan")), eps6d_out=eps_out,
            cooling_factor=float(cooling), n_in=n_in, n_out=n_out,
            wall_seconds=run.wall_seconds,
            extra={
                "eps_trans_in": emit_in.eps_x if emit_in else float("nan"),
                "eps_trans_out": emit_out.eps_x if emit_out else float("nan"),
                "eps_long_in": emit_in.eps_z if emit_in else float("nan"),
                "eps_long_out": emit_out.eps_z if emit_out else float("nan"),
                "pmean_out": emit_out.mean_momentum if emit_out else float("nan"),
            },
        )
    finally:
        if cfg.cleanup:
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)
