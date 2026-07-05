# Optimizing the HFOFO cooling channel — campaign report

**Goal:** maximize the cooling performance (6D emittance reduction) and
transmission of the HFOFO ionization-cooling channel, starting from the
published "track_v7" design, using the black-box optimization framework in
[`../../optimization/`](../../optimization/).

**Headline result.** Relative to the published design (transmission
*T* = 0.64, 6D cooling factor ≈ 64×), the optimizer found designs that increase
the delivered 6D phase-space **density gain** by up to **2.2×** — either by
holding transmission near-constant while nearly doubling the cooling, or by
trading transmission for a 3.5× stronger cooling, depending on the downstream
acceptance. All numbers below are validated at high statistics across
independent Monte-Carlo seeds.

> **Status of the numbers.** These are results of an automated optimization
> study on the g4beamline model with the realistic ICOOL input beam. They are
> physically self-consistent and multi-seed validated, but the strongest-cooling
> designs push the LiH wedge thickness well above the nominal value
> (`wedgeScale` up to ~2.9) and should be checked against engineering
> constraints before being treated as an as-built recommendation. See *Caveats*.

---

## 1. Method

Each design is a point in a 7-dimensional parameter space; evaluating it means
running the full 31-period channel in g4beamline and measuring the resulting
transmission and 6D emittance. The model is non-differentiable and stochastic,
so the campaign uses sample-efficient Bayesian / evolutionary optimization
(see [`../optimization.md`](../optimization.md) for the methodology).

**Parameters optimized** (all global, physically-meaningful knobs of `hfofo.in`):

| knob | meaning | nominal | search range |
|------|---------|:-------:|:------------:|
| `BLS` | solenoid focusing-field scale | 21.4 | 19–26 |
| `Grad` | main-cavity RF gradient (MV/m) | 25 | 18–30 |
| `Grad0` | matching-cavity RF gradient (MV/m) | 20 | 14–30 |
| `delf` | SolPos/SolNeg current asymmetry | 0 | 0–0.12 |
| `pitchFactor` | periodic-section solenoid tilt scale | 1.0 | 0.4–1.5 |
| `dtRF` | global RF phase offset (ns) | 0 | −0.6–0.25 |
| `wedgeScale` | LiH wedge width (absorber) scale | 1.0 | 0.5–3.0 |

**Figures of merit.** Transmission *T* = *N*₃₁/*N*₁ (survival from the first to
the last period). Cooling factor = ε₆D(period 2)/ε₆D(period 31), the 6D
normalized-emittance reduction across the cooling section. The combined merit is
the transmission-weighted 6D phase-space **density gain**,
*T* · ε₆D,in/ε₆D,out (see [`../optimization.md`](../optimization.md)).

**Campaign structure.**

1. **Phase A** — broad 7-parameter TPE sweep (129 evaluations, 400 events each,
   fixed seed for common-random-number comparisons).
2. **Phase B** — extended-box TPE refinement (leaders had saturated several
   bounds) + a multi-objective **NSGA-II Pareto** run mapping the full
   transmission-vs-cooling trade-off (warm-started from ~130 prior sims).
3. **Phase C** — high-statistics (1200-event) validation of six representative
   designs across three independent seeds.
4. **Phase D** — full-channel profiling of the recommended designs and this
   report.

---

## 2. The transmission–cooling trade-off

There is no single "best" design: cooling and transmission trade off against each
other. The Pareto front below maps that trade-off. The nominal design (★) sits
at the **high-transmission edge** of the front — it is already near-optimal for
transmission, and essentially all of the available headroom is in **cooling
harder for a modest transmission cost**.

![Pareto front](pareto_front.png)

---

## 3. Validated designs (Phase C)

Six designs spanning the front, each run at 1200 events × 3 seeds. Errors are
the seed-to-seed standard deviation.

<!-- VALIDATION_TABLE -->

**Reading the table.** *Density gain* is the delivered 6D phase-space density
relative to nominal, *T*/*T*₀ · (cooling/cooling₀) — the single number that
captures "more muons, more tightly packed."

- **`balanced`** — the transmission-preserving recommendation. Keeps 89% of the
  nominal transmission while nearly doubling the cooling (1.8×), for a 1.6×
  density gain with the tightest error bars of any design. Robust and low-risk.
- **`high_cooling`** — the maximum-density-gain recommendation: 2.2× density
  gain, 3.5× stronger cooling, at 63% of nominal transmission. Best when the
  downstream acceptance is the binding constraint.
- **`max_cooling`** — 5.9× cooling but only 34% transmission; useful only if
  transmission is cheap downstream.

### Two honest negative results (why validation mattered)

- **`extreme_cooling`** was the *winner* of the single-objective sweep at 400
  events (score 5.16, apparent cooling 1134×). At 1200 events its cooling
  collapsed to 262× — the extreme value was a **low-statistics artifact**: with
  only ~35 survivors the exit emittance is dominated by noise, and the merit
  rewarded that noise. High-statistics multi-seed validation is not optional.
- **`transmission_matched`** looked like it matched nominal transmission with
  higher cooling on the Pareto front (single seed), but across three seeds it
  came out **below** nominal (0.77× density gain) — a single-seed fluctuation.

---

## 4. Recommended design

<!-- RECOMMENDATION -->

---

## 5. How the channel cools (full-channel profiles)

Emittance and survival along the 31 periods, at 2000 events. These show *where*
the optimized designs win: <!-- PROFILE_NARRATIVE -->

<!-- PROFILE_FIGURES -->

---

## 6. Physics interpretation

The optimizer's improvements are coherent and physically interpretable:

- **Thicker LiH wedges (`wedgeScale` ≫ 1)** are the dominant lever for cooling:
  more ionization energy loss per period means faster emittance reduction. The
  nominal design is conservative here.
- **Stronger focusing (`BLS` ↑) and reduced tilt (`pitchFactor` < 1)** keep the
  beta function small at the absorbers, so the extra scattering from the thicker
  wedges does not blow up the equilibrium emittance — this is what lets the extra
  material cool rather than heat.
- **Higher matching-cavity gradient (`Grad0` ↑)** and a small **coil-current
  asymmetry (`delf` > 0)** recover the additional energy lost in the thicker
  absorbers and stabilize the periodic orbit, protecting transmission.
- The nominal design was already near the transmission ceiling; the campaign's
  value is in **charting and exploiting the cooling axis** that it left on the
  table.

---

## 7. Caveats

1. **Wedge thickness.** The strongest-cooling designs use LiH wedges ~2–3× the
   nominal width. The model treats them as ideal LiH trapezoids; real absorbers
   have windows, density and heating limits, and geometric constraints that were
   not modeled. `balanced` (wedge ≈ 2.9) and especially the physics trend are
   robust; the absolute cooling of the thickest-wedge designs should be
   re-checked with engineering constraints in the loop.
2. **Cooling reference plane.** Cooling is measured period-2 → period-31 to
   exclude entrance-matching transients; transmission is period-1 → period-31.
3. **Input beam.** The realistic ICOOL pre-cooling distribution (`initial.dat`)
   is injected. The RF timing offsets were originally tuned to it.
4. **Statistics.** Validation is 1200 events × 3 seeds; the lowest-transmission
   designs still have the largest relative error on cooling. Production numbers
   for a paper would benefit from ≥5000 events.

---

## 8. Reproduce

```bash
cd optimization
python run_optimization.py --config config_phaseA.yaml         # Phase A sweep
python run_optimization.py --config config_phaseB.yaml         # Phase B refine
PARETO_WARM_JSONL=results/phaseB1/trials.jsonl \
    python pareto.py --config config_phaseB2.yaml              # Pareto front
python validate.py --designs results/candidates.json \
    --config config_phaseB2.yaml --n-events 1200 --seeds 1,2,3 # validation
python profile_channel.py --params results/params_balanced.json \
    --config config_phaseB2.yaml --n-events 2000 --out results/profile_balanced
```

Raw artifacts (trial logs, Pareto front, validation runs) are under
[`phaseA/`](phaseA/), [`phaseB/`](phaseB/), and [`phaseC/`](phaseC/).
