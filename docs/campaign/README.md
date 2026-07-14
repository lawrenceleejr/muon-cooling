# Optimizing the HFOFO cooling channel — campaign report

**Goal.** Maximize the cooling performance (6D emittance reduction) and
transmission of the HFOFO ionization-cooling channel, starting from the
published "track_v7" design, using the black-box optimization framework in
[`../../optimization/`](../../optimization/).

**Headline result.** A systematic optimization of the g4beamline model (with the
realistic ICOOL input beam) found a design — **`brightE2`** — that delivers
**1.80× the 6D phase-space brightness** of the published lattice, reaching an
**exit 6D emittance of 104 ± 17 mm³ versus 243 ± 37 mm³ for nominal (2.3× lower)**
while keeping **78% of the nominal transmission** (0.50 vs 0.64). It was found by
re-optimizing *directly on exit brightness* (Phase E) after the earlier searches
revealed that the intuitive "cooling factor" merit is misleading. A more
conservative design (**`balanced`**, 1.33× brightness at 88% transmission with a
thinner absorber) is offered as an alternative. All numbers are resolved across
three independent Monte-Carlo seeds.

The final refinement (Phase T2, §6a) removes brightE2's transmission penalty
almost entirely: a **shaped z-tapered absorber** (**`taperB2`** — wedge width
0.8× → 4.2× along the channel with a mid-channel bump, *nominal optics and RF*)
reaches the same exit emittance (96 ± 18 mm³ at matched 400-event statistics)
at **T = 0.61 instead of 0.49** — **1.8× the delivered brightness of nominal at
93% of its transmission**, changing nothing but the wedge profile.

Equally important is a **methodological result**: several designs that appeared
2–18× better under naive figures of merit (an entrance-referenced "cooling
factor", or a low-statistics scalar merit) **did not survive** high-statistics,
common-reference validation, and re-optimizing on the *right* metric found designs
the wrong one never would. Getting the merit and the statistics right is what
separates a real improvement from an artifact — see §3–§5.

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
4. **Phase E** — **re-optimize directly on exit brightness** (the metric Phase C
   showed is the one that matters), 90 trials warm-started from prior sims
   re-scored, then re-validate the winners at high statistics. This is where the
   best design was found.
5. **Phase F** — a 9-parameter search adding the entrance matching knobs
   (`entCur`, `entTilt`) on an extended config, to test whether correcting the
   injection match unlocks more cooling. It did not (see §3).
6. **Phase D** — full-channel profiling and this report.

Every simulation ran in the published `ghcr.io/lawrenceleejr/g4beamline` image;
the whole campaign is ~600 g4beamline runs, orchestrated and logged by the
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
The winning designs come from Phase E (re-optimization on exit brightness).

| design | params (BLS/Grad/Grad0/delf/pitch/dtRF/wedge) | transmission | ε₆D(exit) (mm³) | brightness gain |
|---|---|:---:|:---:|:---:|
| **brightE2** *(recommended)* | 21.1 / 23.6 / 22.1 / 0.036 / 0.85 / −0.02 / 3.27 | 0.496 ± 0.006 | **104 ± 17** | **1.80×** |
| brightE3 | 21.0 / 23.5 / 25.4 / 0.014 / 0.77 / +0.05 / 3.33 | 0.481 ± 0.002 | 107 ± 4 | 1.69× |
| balanced *(conservative)* | 22.4 / 26.7 / 22.1 / 0.045 / 1.06 / −0.13 / 2.87 | 0.562 ± 0.008 | 160 ± 17 | 1.33× |
| brightE1 | 22.1 / 23.2 / 23.6 / 0.005 / 1.05 / +0.10 / 2.60 | 0.539 ± 0.002 | 155 ± 21 | 1.31× |
| nominal | 21.4 / 25.0 / 20.0 / 0.000 / 1.00 / 0.00 / 1.00 | 0.641 ± 0.004 | 243 ± 37 | 1.00× |

The two Phase-E winners cut the exit 6D emittance by **~2.3×** (243 → ~100 mm³);
even after the transmission cost they deliver **~1.8× the 6D brightness**
(`brightE2` measured at 1.80× and 2.00× in two independent 3-seed validation
sets — exit emittance 94–105 mm³ — so ~1.9× with the seed-to-seed spread).
`brightE3` has the tightest error bars (±4 mm³) if robustness is paramount.

**Phase F — adding entrance-matching freedom does not help.** A 9-parameter
search that additionally tuned the entrance taper current (`entCur`) and
entrance tilt (`entTilt`) was run on the brightness metric, seeded from the
`brightE2` basin. Its best design (`brightF1` = `brightE2` with `entTilt` = 0.7)
looked ~36% brighter at 500-event screening, but at 1500 events × 3 seeds it
landed at exit emittance **96.7 ± 1.1 mm³ — statistically identical to
`brightE2`'s 94.0 ± 14.6**. The entrance-matching knobs give no robust gain:
`brightE2` sits at the practical optimum of this parameterization, and further
improvement would require a richer parameterization (per-cavity RF timing,
per-section wedge taper) or relaxing the transmission floor.

### Designs that did *not* pan out (why validation and re-optimization matter)

- **Entrance-referenced "cooling factor" is misleading.** An earlier Phase-C set
  (`high_cooling`, `max_cooling`) scored 3.5–5.9× on ε₆D(period 2)/ε₆D(exit).
  Those designs *heat* the beam at injection (optics mismatch — see §5),
  inflating their period-2 reference. Against the *common injected beam*,
  `high_cooling` delivers 0.81× and `max_cooling` 0.43× nominal brightness —
  worse. Re-optimizing on the honest exit-brightness metric (Phase E) is exactly
  what found the `brightE*` basin (low field + thick wedge + reduced tilt) that
  the cooling-factor search had penalized.
- **Low-statistics scalar-merit "winners" are artifacts.** The single-objective
  sweep's best design at 400 events (`extreme_cooling`, apparent cooling 1134×)
  had only ~35 survivors defining its exit emittance. At 1200 events its cooling
  collapsed to 262× and its brightness to 0.13× nominal. High statistics and
  multiple seeds are not optional.

---

## 4. Recommended design: `brightE2`

```
BLS = 21.13   Grad = 23.58   Grad0 = 22.07   delf = 0.036
pitchFactor = 0.848   dtRF = -0.024   wedgeScale = 3.27
```

Ready to run: [`../../hfofo/optimized.json`](../../hfofo/optimized.json)
(apply with `python optimization/apply_design.py hfofo/hfofo.in hfofo/optimized.json`).

Relative to nominal it delivers **1.80× the 6D phase-space brightness**: the exit
6D emittance drops from 243 to **104 mm³ (2.3× smaller)** while transmission falls
from 0.64 to 0.50. If transmission or absorber thickness is the binding
constraint, the conservative [`optimized_conservative.json`](../../hfofo/optimized_conservative.json)
(`balanced`: 1.33× brightness at T = 0.56, wedge 2.87) is the safer choice.

---

## 5. How the channel cools (full-channel profiles)

Emittance and survival along the 31 periods (2000 events), for nominal, the
recommended `brightE2`, and the conservative `balanced`:

![6D emittance vs z](eps6d_vs_z.png)
![transmission vs z](transmission_vs_z.png)

The profiles tell the real story:

- **`brightE2`** (orange) cools faster than both other designs from about period
  6 onward and ends at the lowest ε₆D by a clear margin (~118 vs ~175 for
  `balanced` and ~290 for nominal at 2000 events). Crucially it shows **no
  injection spike** — its period-2 emittance (~19000 mm³) is essentially nominal
  (~16500), so the gain is genuine cooling, not recovery from self-inflicted
  mismatch heating. Its thicker wedge (3.27×) and slightly reduced tilt (0.85)
  cool harder while the near-nominal field keeps the beam matched.
- **`balanced`** (green) tracks nominal for most of the channel and pulls below in
  the last third — a milder version of the same effect with a thinner absorber
  and higher transmission.
- The transmission plot shows the cost: `brightE2` loses beam faster in the first
  ~30 m (thicker absorber + reduced tilt scatter more onto the apertures), then
  runs parallel to the others. This early loss is what the brightness metric
  correctly weighs against the extra cooling — and still comes out 1.8× ahead.

---

## 6. Physics interpretation

The improvement is coherent:

- **Thicker LiH wedges (`wedgeScale` ≈ 3.3)** provide more ionization energy loss
  per period — the dominant cooling lever. The nominal design is conservative here.
- **Near-nominal focusing with a slightly reduced tilt** (`BLS` ≈ 21, `pitchFactor`
  ≈ 0.85) keep the injected beam matched (no injection spike) while lowering the
  beta function enough that the extra scattering from the thick wedge cools rather
  than heats — the delicate balance the honest brightness objective found and the
  entrance-referenced cooling factor missed.
- **A modest main-cavity gradient (`Grad` ≈ 23.5)** matched to the thicker
  absorber's energy loss, plus a small **coil asymmetry (`delf` ≈ 0.04)**, keep
  the reference orbit stable.
- The nominal design was already near the transmission ceiling; the campaign's
  value is charting — and now substantially exploiting — the cooling axis it left
  on the table, while quantifying how much of the "obvious" cooling gains are
  illusory.

---

## 6a. Phase T — the tapered absorber: high transmission *and* strong cooling

The loss decomposition (§6b) showed that thick wedges cost transmission mostly
**early** in the channel, where the beam is still hot and large. That suggested a
new degree of freedom the whole campaign had lacked: a **z-tapered wedge
profile** (`wedgeScaleStart` → `wedgeScaleEnd`, linear over periods 1→30) — thin
absorbers early to protect the beam, thick absorbers late to cool hard once the
beam is small.

It works. Validated at 400 events × 3 seeds against nominal at identical
statistics:

| design | T | ε₆D(exit) (mm³) |
|---|:---:|:---:|
| **taperA** — nominal optics, wedge 1.0→3.5 | **0.609 ± 0.010** | **129 ± 32** |
| nominal | 0.650 ± 0.010 | 187 ± 37 |
| (brightE2, flat 3.27×, for reference) | 0.49 | ~100 |

`taperA` keeps **94 % of the nominal transmission** (vs 75 % for the flat
thick-wedge `brightE2`) while cooling harder than nominal in **every seed**
(mean exit emittance 31 % lower; brightness ≈ 1.4× nominal at these statistics,
up to 2.0× in same-seed comparisons). A 22-trial TPE refinement of the linear
taper family did not beat this point. Raw artifacts in [`phaseT/`](phaseT/).

### Phase T2 — shaping the taper (mid-channel bump)

The linear taper leaves one question open: is *linear* the right profile? Phase
T2 added a third shape term — `wedgeScaleMidBump`, a triangular bump that is
zero at both ends and maximal at mid-channel — and re-optimized all ten knobs
(56 TPE trials at 400 events, warm-started from Phase T, transmission floor
T ≥ 0.60). The optimizer's answer: start *thinner* than taperA (0.8×), ramp
steeper (to ~4.2×), and add material mid-channel (+0.5 bump) where the beam is
already compact but still far from equilibrium. Validated at 400 events × 3
seeds against taperA and nominal at identical statistics:

| design | T | ε₆D(exit) (mm³) | exit brightness vs nominal |
|---|:---:|:---:|:---:|
| **taperB2** — nominal optics, shaped 0.8→4.2 + 0.5 bump | 0.606 ± 0.014 | **95.8 ± 18.4** | **1.82×** |
| taperC — shaped 0.82→4.08 + 0.45 bump, mild optics retune | **0.624 ± 0.018** | 103 ± 23 | 1.75× |
| taperA — nominal optics, linear 1.0→3.5 | 0.609 ± 0.010 | 129 ± 32 | 1.36× |
| nominal | 0.650 ± 0.010 | 187 ± 38 | 1.00× |

`taperB2` beats taperA in **every seed** at the same transmission — 26 % lower
mean exit emittance, matching the flat-wedge `brightE2`'s cooling (ε ≈ 100) at
**T = 0.61 instead of 0.49** — and it changes *nothing* but the wedge profile
(nominal fields, RF, and timing). It is now the recommended design:
[`../../hfofo/optimized_taper.json`](../../hfofo/optimized_taper.json). `taperC`
([`../../hfofo/optimized_taper_hiT.json`](../../hfofo/optimized_taper_hiT.json))
trades a little cooling for T = 0.624 (96 % of nominal) via a mild optics
retune. Raw artifacts in [`phaseT2/`](phaseT2/).

*Caveat:* the exit-emittance estimator is noisy at 400 events (±20–25 %), so the
brightness magnitudes carry that uncertainty; the transmission numbers are
solid (±0.01–0.02). A ≥1500-event revalidation is the standing follow-up
(blocked by container instability in this session). The shaped taper inherits
the wedge engineering caveat (§7): late-channel wedges reach ~4.2× the design
width, and the mid-channel bump adds up to +0.5× on top of the ramp there.

## 6b. Transmission and where the losses go

A dedicated study ([`losses/`](losses/)) decomposes the transmission loss and
asks whether it can be recovered. Summary:

- The injected beam (`initial.dat`, ICOOL pre-cooling) is broad in momentum —
  only ~71 % of muons are in the 100–400 MeV/c window — and has a transverse
  halo reaching the RF iris.
- By running decay-on vs. decay-off, nominal loss splits into **~6 % muon decay**
  and **~33 % aperture/optics**; the aggressive `brightE2` pays more on *both*
  (~14 % decay, ~39 % aperture) because its lower momentum shortens the decay
  length and increases scraping — cooling and transmission genuinely trade off.
- A transmission-maximizing optimization (free to open the RF irises and thin the
  wedges) **could not beat nominal by more than Monte-Carlo noise**: the loss is
  **dynamic/momentum acceptance**, not physical-aperture scraping, so opening
  irises doesn't help. Raising transmission requires a narrower/better-matched
  input beam or the frozen per-element lattice freedoms, not the global knobs.
- Every evaluation now reports a **decay-corrected transmission** (aperture/optics
  survival) alongside the raw number.

## 6c. The paper's suggested improvements, tested

The HFOFO paper ([arXiv:1806.07517](https://arxiv.org/abs/1806.07517)) closes
with a short list of possible improvements. We implemented and tested each of
them in this model (raw artifacts in
[`paper_suggestions/`](paper_suggestions/)); all runs at 400 events with common
random numbers, references on the same seed/batch: nominal T=0.650, ε₆D=187;
`taperB2` T=0.606, ε₆D=96.

**1. Quadrupole equalization field (paper §4).** A constant unipolar quadrupole
Gq = −0.052 T/m equalizes the two transverse normal-mode cooling rates, at the
price of a β-beat; it is off in the published design. We added it as an overlay
field (`Gq`/`GqRoll` knobs in `hfofo.in`) and scanned Gq ∈ {−0.026, −0.052,
−0.078} T/m and a 45° roll on both the nominal and `taperB2` backgrounds. **No
gain**: on nominal the best case (−0.052, roll 45°) is only ~seed-noise better
in ε₆D (172 vs 205) at lower T; on `taperB2` it degrades both T (0.568 vs
0.602) and ε₆D (90 vs 80). An apparent transmission boost at −0.078 T/m
(T=0.677 on seed 1) did not reproduce on seeds 2–3 (0.645 ± 0.012 vs nominal
0.649). The equalization helps the *slower* mode but the β-beat and the
already-dominant mode coupling in the tilted lattice appear to eat the benefit.

**2. Independently powered dipole coils (paper §7).** The engineering point —
separate coils are more practical than tilting solenoids — is outside a
tracking study, but its tunable-physics content is a *z-dependent dipole
strength*, decoupled from focusing. We added per-period tilt factors
(`pitchTaperStart/End`, `pitchP1..29` in the card) and screened rising and
falling profiles (±15–30 %) on both backgrounds. **All variants are neutral or
worse** (e.g. on `taperB2`: 1.15→0.85 gives ε₆D=115 vs 80; 0.85→1.15 gives
213). The flat dipole profile of the published design is already near-optimal
at this granularity — consistent with the dispersion being resonantly
generated, where a z-profile mostly detunes it.

**3. Higher betatron phase advance per focusing unit (paper §7).** The paper
suggests going beyond the design's φ = 74° to shrink β at the absorbers,
cautioning that the full benefit needs absorbers localized at the β-minima and
vacuum RF. A dedicated 24-trial TPE scan (Phase P,
[`../../optimization/config_phaseP.yaml`](../../optimization/config_phaseP.yaml))
over BLS ∈ [22.5, 30] with all RF/tilt/wedge-shape knobs co-tuned confirms the
caution empirically — **in this GH2-filled lattice, stronger focusing is
strictly worse**:

| BLS (taperB2 wedge, same seed) | 21.4 | 23 | 25 | 27 | 29 |
|---|:---:|:---:|:---:|:---:|:---:|
| T | **0.602** | 0.517 | 0.538 | 0.508 | 0.435 |
| ε₆D(exit) mm³ | **80** | 123 | 138 | 124 | 162 |

Transmission decays monotonically with BLS (the transverse tunes climb toward
the parametric resonance and the dynamic momentum acceptance shrinks — the
same acceptance wall as §6b), and ε₆D never improves because the absorption is
distributed over the GH2 and wedges rather than localized at the β-minima. The
best design the optimizer could find in the whole high-BLS box (BLS 22.5,
validated 3 seeds: T=0.596 ± 0.007, ε₆D=101 ± 17) merely matches `taperB2` at
slightly lower transmission. Every earlier phase independently drifted to
BLS ≈ 20.5–22.5; this closes that question.

**4. Length taper (paper §7): "×5 by tapering down the length of all elements
and increasing the solenoid current".** This is the one suggestion that cannot
be tested with global knobs, and the geometry says why: each 700 mm focusing
cell carries a rigid ~500 mm block of two 325 MHz cavities (their radius is
fixed by the frequency, their combined length by the gradient needed for the
energy balance) centered in the solenoid bore. The free mid-cell gap is
(700·s − 500) mm under a cell compaction s, while the thick end-channel wedge
needs ~115 mm plus clearance — so **only s ≳ 0.93 (~7 % compaction) is
available without redesigning the RF**, worth an estimated 10–15 % in ε₆D (β
∝ cell length at fixed tune), not ×5. The full factor requires progressively
shorter cells with the absorbers at the β-minima and the RF moved out of the
cells (vacuum RF between coils, or the pulsed radial lines the paper cites) —
i.e. a new lattice, not a tune of this one. This is the genuine follow-up
design study; the present campaign's shaped wedge taper (`taperB2`, §6a)
captures the same "adapt the cooling to the shrinking beam" physics on the z
axis that *is* accessible in the fixed lattice.

**Bottom line.** Within the fixed 325 MHz GH2 architecture, none of the
paper's four suggestions beats the shaped wedge taper found in Phase T2 —
suggestions 1–3 are net-negative or neutral in this model (1 and 3 for reasons
the paper itself anticipated), and suggestion 4 needs a redesigned lattice.
The `Gq`, `GqRoll` and `pitchTaperStart/End` knobs remain in the card for
future studies.

## 7. Caveats

1. **Wedge thickness.** `brightE2` uses LiH wedges ~3.3× the nominal width
   (`balanced` ~2.9×), modeled as ideal LiH trapezoids. Real absorbers have
   windows, density/heating limits and geometric constraints not modeled here;
   the absolute gain should be re-checked with engineering constraints before
   being treated as as-built. If the wedge cannot be thickened that far,
   `balanced` (thinner wedge, still 1.33×) is the fallback.
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
python run_optimization.py --config config_phaseE.yaml               # Phase E (brightness)
python validate.py --designs results/candidates3.json \
    --config config_phaseE.yaml --n-events 1500 --seeds 1,2,3 \
    --out results/validation3                                        # validation
python profile_channel.py --params results/params_brightE2.json \
    --config config_phaseE.yaml --n-events 2000 --out results/profile_brightE2
python plot_brightness.py --summary results/validation3/validation_summary.json --out ../docs/campaign
```

Raw artifacts (trial logs, Pareto front, validation runs, profiles) are under
[`phaseA/`](phaseA/), [`phaseB/`](phaseB/), [`phaseC/`](phaseC/), [`phaseE/`](phaseE/),
and [`profiles/`](profiles/).
