# Optimizing the HFOFO cooling channel

This note explains *how* the optimization is set up and *why* — the reasoning
behind treating the simulation as a black box and the choices baked into
`optimization/`.

## Why it's hard

Muon ionization cooling is intrinsically a Monte-Carlo process. To know what a
given lattice does to the beam you have to track many muons through G4beamline
and measure the result, because the physics that matters — multiple scattering in
the absorbers, energy-loss straggling, RF capture, particle loss on apertures —
is stochastic and strongly coupled across the six phase-space dimensions. There
is **no closed-form, differentiable map** from "lattice parameters" to
"transmission and 6D emittance".

So the objective we want to optimize has all the properties that make
optimization hard:

1. **No gradient.** It is the output of a particle-physics simulation.
2. **Expensive.** Each evaluation is a full multi-period tracking run.
3. **Noisy.** Being Monte-Carlo, repeated evaluations of the same point scatter;
   the scatter grows as fewer muons survive to define the exit emittance.
4. **Constrained / multi-objective.** Cooling and transmission trade off: you can
   always "cool" by collimating away the tails, but that throws beam away.

## The wrapping strategy

The core idea — *"wrap that process in an optimizer"* — is to expose the
simulation as a single function

```
f : parameters  ->  scalar merit
```

and hand `f` to a black-box optimizer. Concretely, one evaluation of `f`:

1. copies the `hfofo/` config into a scratch directory,
2. rewrites the tunable `param NAME=...` lines in `hfofo.in` (`parameters.py`),
3. runs g4bl in the container (`runner.py`),
4. reads the entrance/exit detector files and computes transmission and 6D
   emittance (`metrics.py`),
5. folds them into one number (`objective.py`).

Because `f` is just a Python callable, **any** black-box optimizer can drive it;
the framework ships three and they share a trial log so they're directly
comparable.

## Which optimizer

For expensive, noisy, derivative-free objectives the sample-efficient choice is
**Bayesian optimization**: build a probabilistic surrogate of `f` from the
evaluations so far, then use it to decide where to sample next (balancing
"exploit the current best" against "explore where the surrogate is uncertain").
This typically finds good designs in tens of evaluations rather than the
thousands a grid scan or genetic algorithm would need.

- **Optuna TPE** (`bayes`, default) — a Tree-structured Parzen Estimator. Robust,
  copes with noise, parallelizes across workers, and the study can be persisted
  and resumed. A good default that scales from 4 to dozens of parameters.
- **Gaussian-process BO** (`gp`, scikit-optimize) — the textbook surrogate.
  Most sample-efficient when the dimension is low (≤ ~6, as here) and the
  evaluation budget is small, at the cost of `O(n^3)` surrogate fitting as trials
  accumulate.
- **Random search** (`random`) — not competitive, but the honest baseline: if a
  fancy optimizer can't beat random search on your problem, something is wrong.

Practical recommendation: start with `bayes` for a broad, parallel sweep; switch
to `gp` for a tight final polish in a narrowed range.

## The merit function

We optimize the transmission-weighted gain in **6D phase-space density**:

```
merit = T^w_T · (eps6D_in / eps6D_out)^w_cool
```

Phase-space density `ρ ∝ N / eps6D` is the physically meaningful figure for a
cooling channel feeding a downstream accelerator: what matters is how many muons
you deliver *per unit phase-space volume*. The ratio of output to input density
is exactly `T · (eps6D_in/eps6D_out)`. Taking the log keeps the optimizer
well-conditioned across the orders of magnitude the emittance spans.

Setting `w_T = w_cool = 1` optimizes raw density gain. Raising `w_T` favors
transmission (good when downstream acceptance is generous); raising `w_cool`
favors cooling (good when the downstream acceptance is the binding constraint).
The `transmission_floor` adds a soft penalty below a minimum survival fraction so
the optimizer doesn't chase degenerate "cool a handful of muons perfectly"
solutions.

### Measuring emittance robustly

`metrics.compute_emittance` builds the canonical 6D coordinate vector (including
the solenoid vector-potential correction to transverse momentum) and takes the
normalized eigen-emittances from the symplectic eigenvalue problem
`eig(-Σ S₆)`. The 6D emittance is their product. The angular-momentum subtraction
uses an on-axis `Bz0`; because it's applied identically at entrance and exit, the
cooling *ratio* — which is what the merit uses — is insensitive to its exact
value. Planes with fewer than six survivors return "no emittance", which the
objective treats as a feasible-but-bad point.

## Reducing and managing noise

- **Statistics.** The exit emittance is computed from the surviving cooled core,
  so it is the noisiest ingredient. Increase `n_events` to tighten it; the cost
  is linear. Both TPE and GP tolerate noise, but less noise means fewer
  evaluations to separate real improvements from scatter.
- **Common random numbers.** For an even cleaner comparison between nearby
  designs you can fix the G4beamline random seed so two parameter points see the
  same incoming beam; the difference in their merit is then almost entirely
  signal. (Hook: set the seed in `hfofo.in` and expose it as a fixed param.)
- **Parallelism.** Evaluations are independent, so `n_jobs > 1` runs several
  containers at once for near-linear speedup up to the core count.

## Scaling up

The shipped configuration tunes four global knobs as a tractable, meaningful
demonstration. The same machinery scales to richer designs:

- add per-section knobs (matching-cavity timing, absorber wedge angle/thickness,
  individual solenoid currents) — add a `param` in `hfofo.in` and a bound in
  `config.yaml`;
- run a **multi-objective** Optuna study to map the full transmission–cooling
  Pareto front instead of collapsing to one scalar;
- persist the Optuna study to a database and run workers across machines for a
  large evaluation budget.
