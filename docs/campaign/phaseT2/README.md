# Phase T2 — shaped wedge taper (mid-channel bump) at T ≥ 0.60

10-knob TPE refinement (56 trials, 400 events, warm-started from Phase T) adding
`wedgeScaleMidBump` — a triangular mid-channel term on top of the linear
`wedgeScaleStart→End` taper. Objective: exit brightness with a soft
transmission floor at T = 0.60.

## Files

- `config.yaml` — the search configuration (spaces, objective, optimizer).
- `trials.csv` — all evaluated trials with metrics and parameters.
- `validation_runs.csv`, `validation_summary.json` — 400 events × 3 seeds
  validation of the winners against taperA and nominal.

## Result

| design | T | ε₆D(exit) mm³ | brightness vs nominal |
|---|:---:|:---:|:---:|
| taperB2 (trial 7: 0.8→4.2, +0.5 bump, nominal optics) | 0.606 ± 0.014 | 95.8 ± 18.4 | 1.82× |
| taperC (trial 47: 0.82→4.08, +0.45 bump, mild optics retune) | 0.624 ± 0.018 | 103 ± 23 | 1.75× |
| taperA (Phase T: linear 1.0→3.5) | 0.609 ± 0.010 | 129 ± 32 | 1.36× |
| nominal | 0.650 ± 0.010 | 187 ± 38 | 1.00× |

Both shaped tapers beat taperA in every seed at the same (taperB2) or higher
(taperC) transmission. `taperB2` is the recommended design
(`hfofo/optimized_taper.json`); `taperC` is the higher-transmission variant
(`hfofo/optimized_taper_hiT.json`). See the main campaign report §6a.
