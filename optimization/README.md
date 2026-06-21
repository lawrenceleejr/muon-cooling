# HFOFO cooling optimization framework (`muopt`)

A framework for optimizing the HFOFO cooling channel when the model is **not
differentiable**: the only way to know the resulting transmission and 6D
phase-space reduction is to push Monte-Carlo muons through G4beamline. This wraps
that black box in a sample-efficient optimizer.

## The problem, and the approach

Each evaluation is:

- **expensive** — a g4bl run is seconds to minutes,
- **noisy** — it's Monte-Carlo, so the same parameters give slightly different
  answers run-to-run,
- **non-differentiable** — no gradients; the objective comes out of a physics
  simulation,
- **multi-objective** — we want *both* strong cooling *and* high transmission,
  and they fight each other.

That rules out gradient methods and rewards **sample-efficient black-box
optimization with a noise model**. The framework provides three interchangeable
optimizers:

| method | what | when to use |
|--------|------|-------------|
| `bayes` *(default)* | Optuna **TPE** | robust general choice; parallel + resumable |
| `gp` | scikit-optimize **Gaussian-process** Bayesian optimization | most sample-efficient in ≤ ~6 dims / few evaluations |
| `random` | random search | baseline / sanity check |

All three log identical per-trial records, so you can compare them directly.

### Figure of merit

The two goals are folded into one scalar — the gain in 6D phase-space **density**,
transmission-weighted:

```
merit  =  transmission ^ w_T  ×  (eps6D_in / eps6D_out) ^ w_cool
score  =  log(merit)            # optimizer maximizes this
```

Maximizing it rewards shrinking the 6D emittance *and* keeping the beam. The
weights `w_T`, `w_cool` and a soft `transmission_floor` (to discourage designs
that throw the beam away) are all set in `config.yaml`, so you can shift the
emphasis without touching code. Failed or beam-killing runs return a finite
penalty with a gradient back toward "keep the beam alive", so the surrogate model
learns the infeasible region instead of seeing NaNs.

## Layout

```
optimization/
├── config.yaml          # parameter space + objective + optimizer settings
├── run_optimization.py  # CLI entry point
├── requirements.txt
├── muopt/
│   ├── metrics.py       # transmission + 6D normalized emittance (pure NumPy)
│   ├── runner.py        # run g4bl in Docker or natively
│   ├── parameters.py    # tunable knobs + input-card templating
│   ├── objective.py     # one parameter point -> one scalar score
│   ├── optimize.py      # optimizer drivers + trial logging
│   └── plotting.py      # convergence / trade-off / parameter-slice plots
└── tests/               # unit tests (no g4bl required; run in CI)
```

## Usage

```bash
pip install -r requirements.txt

# full optimization run (reads config.yaml)
python run_optimization.py --config config.yaml

# evaluate only the published nominal design
python run_optimization.py --config config.yaml --baseline

# override optimizer / budget on the command line
python run_optimization.py --config config.yaml --method gp --n-trials 40
```

Outputs land in `out_dir` (default `results/run/`):

- `trials.csv` / `trials.jsonl` — every evaluation (params + metrics)
- `best.json` — best design found
- `convergence.png`, `tradeoff.png`, `parameters.png` — summary plots

### Backend

`runner.backend: auto` uses a native `g4bl` if one is on your `PATH`, otherwise
Docker with `ghcr.io/lawrenceleejr/g4beamline:main`. The Docker path handles the
`.data` / `--network none` / offscreen-Qt details automatically (see
`../hfofo/README.md` for why).

## Tuning the run

- **Noise vs. cost**: raise `objective.n_events` for less run-to-run scatter at
  higher cost per trial. A few hundred events is a reasonable starting point;
  the surviving cooled core is what determines the exit emittance, so very low
  statistics make the emittance noisy.
- **Parallelism**: `optimizer.n_jobs > 1` runs several g4bl containers at once
  (each is single-threaded). Keep `n_jobs ≲ nproc`.
- **More knobs**: add parameters in `config.yaml` *and* a matching `param` line
  in `hfofo.in` (and reference `$name` from the placement files if the knob
  drives geometry such as absorber wedge angle or per-cavity timing).
- **Resuming / distributed** (TPE): pass an Optuna `storage` URL to share a study
  across processes/machines.

## Extending

- **New metric** (e.g. transverse-only emittance, transmission within an
  acceptance): add it in `metrics.py` and reference it from `objective.py`.
- **True multi-objective Pareto front**: Optuna supports multi-objective studies;
  `optimize.py` is structured so a `directions=[...]` study slots in alongside the
  scalar one.
