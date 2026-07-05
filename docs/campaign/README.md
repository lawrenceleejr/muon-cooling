# Optimizing the HFOFO cooling channel — campaign report

**Goal.** Maximize the cooling performance (6D emittance reduction) and
transmission of the HFOFO ionization-cooling channel, starting from the
published "track_v7" design, using the black-box optimization framework in
[`../../optimization/`](../../optimization/).

**Headline result.** A systematic 7-parameter optimization of the g4beamline
model (with the realistic ICOOL input beam) found one design — **`balanced`** —
that robustly improves on the published design: it delivers **1.33× the 6D
phase-space brightness**, reaching an **exit 6D emittance of 160 ± 17 mm³ versus
243 ± 37 mm³ for nominal (1.5× lower)** while keeping **88% of the nominal
transmission** (0.56 vs 0.64). The improvement is resolved across three
independent Monte-Carlo seeds.

Equally important is a **methodological result**: several designs that appeared
2–18× better under naive figures of merit (an entrance-referenced "cooling
factor", or a low-statistics scalar merit) **did not survive** high-statistics,
common-reference validation. Getting the merit and the statistics right is what
separates a real improvement from an artifact — see §3 and §4.

![brightness gain](brightness_gain.png)

---

## 1. Method

Each design is a point in a 7-dimensional space; evaluating it means running the
full 31-period channel in g4beamline and measuring transmission and 6D
emittance. The model is non-differentiable and stochastic, so the campaign uses
sample-efficient Bayesian (Optuna TPE) and evolutionary (NSGA-II) optimization —
see [`../optimization.md`](../optimization.md).

**Parameters optimized** (global, physically-meaningful knobs of `hfofo.in`):

| knob | meaning | nominal | search range |
|------|---------|:-------:|:------------:|
| `BLS` | solenoid focusing-field scale | 21.4 | 19–26 |
| `Grad` | main-cavity RF gradient (MV/m) | 25 | 18–30 |
| `Grad0` | matching-cavity RF gradient (MV/m) | 20 | 14–30 |
| `delf` | SolPos/SolNeg current asymmetry | 0 | 0–0.12 |
| `pitchFactor` | periodic-section solenoid tilt scale | 1.0 | 0.4–1.5 |
| `dtRF` | global RF phase offset (ns) | 0 | −0.6–0.25 |
| `wedgeScale` | LiH wedge width (absorber) scale | 1.0 | 0.5–3.0 |

**Figure of merit — delivered 6D brightness.** All designs receive the *same*
injected beam, so the physically meaningful, design-independent figure is the
6D phase-space density delivered at the channel exit:

> **brightness** = *T* / ε₆D(exit),  where *T* = *N*₃₁/*N*₁ is transmission and
> ε₆D(exit) is the normalized 6D emittance at period 31.

"Brightness gain" throughout is this quantity relative to nominal. (During the
search we used a proxy, *T*·ε₆D,in/ε₆D,out; §4 explains why the exit-referenced
brightness is the one to trust for the final ranking.)

**Campaign structure.**

1. **Phase A** — broad 7-parameter TPE sweep (129 evals, 400 events, fixed seed).
2. **Phase B** — extended-box TPE refinement + a multi-objective **NSGA-II
   Pareto** run mapping the transmission-vs-cooling trade-off (warm-started from
   ~130 prior sims).
3. **Phase C** — high-statistics validation (1200–1500 events) of candidate
   designs across 3 independent seeds, on the honest brightness metric.
4. **Phase D** — full-channel profiling and this report.

Every simulation ran in the published `ghcr.io/lawrenceleejr/g4beamline` image;
the whole campaign is ~400 g4beamline runs, orchestrated and logged by the
framework.

---

## 2. The transmission–cooling trade-off

There is no single "best" design — cooling and transmission trade off. The
Pareto front below maps that trade-off. The nominal design (★) sits at the
**high-transmission edge**: it is already near-optimal for transmission, so the
available headroom is in cooling harder for a modest transmission cost.

![Pareto front](pareto_front.png)

---

## 3. Validated designs

All figures below are validated at 1500 events × 3 seeds (errors are the
seed-to-seed standard deviation), on the common-injected-beam brightness metric.

| design | params (BLS/Grad/Grad0/delf/pitch/dtRF/wedge) | transmission | ε₆D(exit) (mm³) | brightness gain |
|---|---|:---:|:---:|:---:|
| **balanced** | 22.4 / 26.7 / 22.1 / 0.045 / 1.06 / −0.13 / 2.87 | 0.562 ± 0.008 | **160 ± 17** | **1.33×** |
| nominal | 21.4 / 25.0 / 20.0 / 0.000 / 1.00 / 0.00 / 1.00 | 0.641 ± 0.004 | 243 ± 37 | 1.00× |
| midcool | 21.7 / 21.0 / 27.0 / 0.037 / 0.65 / −0.06 / 1.89 | 0.475 ± 0.005 | 188 ± 37 | 0.96× |
| lowwedge | 23.6 / 20.2 / 23.0 / 0.011 / 0.96 / −0.07 / 1.18 | 0.499 ± 0.013 | 228 ± 21 | 0.83× |
| brightA | 21.3 / 27.3 / 29.0 / 0.081 / 0.83 / +0.23 / 2.56 | 0.456 ± 0.006 | 218 ± 46 | 0.79× |

**Only `balanced` improves on nominal.** Its lower error-bar edge (≈1.18×) clears
nominal's upper edge (≈1.15×), so the gain is statistically resolved. Every other
validated design lands at or below nominal brightness: they cool the surviving
core somewhat, but not enough to pay for the transmission they lose.

### Two instructive negative results

- **Entrance-referenced "cooling factor" is misleading.** A separate Phase-C set
  (`high_cooling`, `max_cooling`) scored 3.5–5.9× on ε₆D(period 2)/ε₆D(exit).
  But those aggressive designs *heat* the beam at injection (optics mismatch —
  see §5), inflating their period-2 reference. Measured against the *common
  injected beam*, `high_cooling` delivers 0.81× and `max_cooling` 0.43× the
  nominal brightness — i.e. worse. The reference plane matters.
- **Low-statistics scalar-merit "winners" are artifacts.** The single-objective
  sweep's best design at 400 events (`extreme_cooling`, apparent cooling 1134×)
  had only ~35 survivors defining its exit emittance. At 1200 events its cooling
  collapsed to 262× and its brightness to 0.13× nominal. High statistics and
  multiple seeds are not optional.

---

## 4. Recommended design: `balanced`

```
BLS = 22.38   Grad = 26.7   Grad0 = 22.1   delf = 0.045
pitchFactor = 1.06   dtRF = -0.127   wedgeScale = 2.87
```

Ready to run: [`../../hfofo/optimized_balanced.json`](../../hfofo/optimized_balanced.json)
(apply with `python optimization/apply_design.py hfofo/hfofo.in hfofo/optimized_balanced.json`).

Relative to nominal it delivers **1.33× the 6D phase-space brightness**: the exit
6D emittance drops from 243 to **160 mm³ (1.5× smaller)** while transmission only
falls from 0.64 to 0.56. It has the **lowest exit emittance of every design
tested** and the tightest error bars — the low-risk, robust improvement.

---

## 5. How the channel cools (full-channel profiles)

Emittance and survival along the 31 periods (2000 events), for nominal,
`balanced`, and the aggressive `high_cooling`:

![6D emittance vs z](eps6d_vs_z.png)
![transmission vs z](transmission_vs_z.png)

The profiles tell the real story:

- **`balanced`** (orange) tracks nominal's emittance for most of the channel and
  pulls clearly below it in the last third, ending at the lowest ε₆D — genuine
  extra cooling from the thicker absorber, without an injection penalty.
- **`high_cooling`** (green) shows a large ε₆D **spike at injection** (period 2):
  its halved solenoid tilt mismatches the incoming beam, which filaments and
  dilutes. It then cools steeply, but it is climbing out of a hole of its own
  making — and it loses beam fastest (transmission plot), because the same thick
  wedges scatter the mismatched beam onto the apertures. This is exactly the
  design the entrance-referenced cooling factor over-rewarded.

---

## 6. Physics interpretation

The one robust improvement is coherent:

- **Thicker LiH wedges (`wedgeScale` ≈ 2.9)** provide more ionization energy loss
  per period — the dominant cooling lever. The nominal design is conservative here.
- **Near-nominal focusing and tilt** (`BLS` 22.4, `pitchFactor` 1.06) keep the
  injected beam matched, so the extra absorber cools rather than heats — this is
  the difference between `balanced` and the mismatch-heated `high_cooling`.
- **Higher main-cavity gradient (`Grad` 26.7)** and a small **coil asymmetry
  (`delf` 0.045)** replace the additional energy lost in the thicker absorber and
  stabilize the periodic orbit, protecting transmission.
- The nominal design was already near the transmission ceiling; the campaign's
  value is charting — and modestly exploiting — the cooling axis it left on the
  table, and quantifying how much of the "obvious" cooling gains are illusory.

---

## 7. Caveats

1. **Wedge thickness.** `balanced` uses LiH wedges ~2.9× the nominal width,
   modeled as ideal LiH trapezoids. Real absorbers have windows, density/heating
   limits and geometric constraints not modeled here; the absolute gain should be
   re-checked with engineering constraints before being treated as as-built.
2. **Reference planes.** Transmission is period 1 → period 31; the final ranking
   uses exit 6D emittance (period 31) against the common injected beam. The
   during-search cooling factor (period 2 → 31) is retained only for continuity.
3. **Input beam.** The realistic ICOOL pre-cooling distribution (`initial.dat`)
   is injected; the RF timing offsets were originally tuned to it.
4. **Statistics.** Validation is 1200–1500 events × 3 seeds. A publication number
   would benefit from ≥5000 events, especially for the lower-transmission designs.

---

## 8. Reproduce

```bash
cd optimization
python run_optimization.py --config config_phaseA.yaml               # Phase A
python run_optimization.py --config config_phaseB.yaml               # Phase B refine
PARETO_WARM_JSONL=results/phaseB1/trials.jsonl \
    python pareto.py --config config_phaseB2.yaml                    # Pareto front
python validate.py --designs results/candidates2.json \
    --config config_phaseB2.yaml --n-events 1500 --seeds 1,2,3 \
    --out results/validation2                                        # validation
python profile_channel.py --params results/params_balanced.json \
    --config config_phaseB2.yaml --n-events 2000 --out results/profile_balanced
python plot_brightness.py --summary results/validation2/validation_summary.json --out ../docs/campaign
```

Raw artifacts (trial logs, Pareto front, validation runs, profiles) are under
[`phaseA/`](phaseA/), [`phaseB/`](phaseB/), [`phaseC/`](phaseC/), and
[`profiles/`](profiles/).
