# Where the muons go: transmission and loss analysis

This note answers a set of concrete questions about HFOFO transmission: what beam
we inject, how much beam is lost to muon **decay** versus **apertures/optics**,
where along the channel it is lost, and whether the loss can be recovered.

## The injected beam

`hfofo/initial.dat` — the ICOOL **pre-cooling** distribution injected at
z = −700 mm: **11 755 µ⁺ + 716 π⁺**. Key properties for transmission:

- **Broad momentum spectrum** (µ⁺ median 287 MeV/c, p5–p95 = 203–992, tail to
  ~3.8 GeV/c). Only **~71 % of the muons lie in the 100–400 MeV/c window** the
  channel accepts; the rest are outside its momentum acceptance from injection.
- **Transverse halo** reaching the aperture: µ⁺ radius median 93 mm, **p95 ≈ 199 mm**,
  max ≈ 300 mm — the p95 sits right at the RFC2 RF iris (200 mm).
- The shipped file is **momentum-ordered** (low-p first), so a truncated
  `nEvents` sample was biased toward the easy-to-capture core. The default beam
  is now `initial_shuffled.dat` (deterministic shuffle → representative sampling);
  `initial_muplus.dat` (µ⁺-only) is used for clean decay studies.

## Decay vs. aperture/optics — measured by decay-on / decay-off

Running the channel with muon decay **on** vs. **off** (`physics ... disable=Decay`,
µ⁺-only beam so π→µ feed-in doesn't distort the count) cleanly separates the two
loss channels. At the exit (period 31), of the muons in the momentum window:

| design | decay loss | aperture/optics loss | observed T |
|--------|:----------:|:--------------------:|:----------:|
| **nominal** | **~6 %**  (S ≈ 0.94) | **~33 %** (A ≈ 0.67) | 0.63 |
| **brightE2** (brightness-optimal) | ~14 % (S ≈ 0.86) | ~39 % (A ≈ 0.61) | 0.53 |

(The factorization T ≈ A·S holds to ~1 %.) Two takeaways:

1. **Decay is a small, near-irreducible term (~6 % for nominal).** The
   addressable loss is aperture/optics.
2. **Cooling harder costs transmission twice.** brightE2's thick LiH wedge lowers
   the momentum, which *both* shortens the decay length (14 % vs 6 %) *and*
   increases scraping (39 % vs 33 %) — the physical price of its 2.3× emittance
   reduction. Transmission and cooling genuinely trade off.

Per-period tracking (`decomposition_nominal.csv`) shows the aperture loss is
**spread ~1–1.5 %/period along the whole channel**, not a single injection-halo cut.

## Can we recover the aperture/optics loss? Mostly no — it's dynamic acceptance

A dedicated optimization was run to **maximize the decay-corrected (aperture)
transmission**, free to open the small RF irises (`irisScale` on RFC1/RFC2, the
200/250 mm apertures where the halo sits) and thin the wedges. The result is
decisive:

| design | T (raw) |
|--------|:-------:|
| nominal | 0.653 |
| nominal + **open irises (×1.35)** | 0.654 — **no change** |
| nominal + thin wedge + open irises | 0.649 |
| best found (thin wedge + open iris + retune) | ~0.656 — within MC noise |

**Opening the RF irises does not increase transmission, and no combination of the
global knobs beats nominal by more than Monte-Carlo noise (~±0.02).** The lost
muons are *not* being scraped at the iris edge — they are outside the channel's
**stable dynamic + momentum acceptance** and drift out regardless of physical
aperture. Transmission of the periodic channel is at its acceptance ceiling
(~0.65) for this beam.

### So how *do* you increase transmission?

The global lattice knobs are exhausted; real gains require enlarging the
**acceptance**, which lives upstream and in the fine lattice structure:

- **Momentum acceptance (largest lever).** ~29 % of injected muons are outside
  the 100–400 MeV/c window at the start. A narrower-momentum, better-matched
  input beam (upstream rotator/buncher), or a wider RF bucket (frequency /
  gradient / longitudinal lattice), recovers beam the periodic channel currently
  cannot capture. This is an upstream / longitudinal-dynamics design task, not a
  transverse-aperture one.
- **Transverse dynamic acceptance.** Enlarging the stable transverse region needs
  the per-element degrees of freedom (individual solenoid tilts/currents — the
  ~37 matching-section parameters, deliberately frozen in this campaign), not a
  global field/tilt scale. A future study could open those.
- **Shorter channel / fewer periods** trades cooling for less integrated decay +
  scraping, if the downstream stage tolerates larger emittance.

## Reporting: decay-corrected transmission is now standard

Every evaluation now logs three numbers:

- `transmission` — raw muon survival N_out/N_in in the momentum window;
- `decay_survival` S — muon-decay survival between planes, from the recorded
  transit time and path-averaged γ (validated against the two-run decay-off
  measurement: 0.916 vs 0.942, ~3 %);
- `transmission_corrected` = T / S — the **aperture/optics survival**, i.e.
  "of the muons that had not yet decayed, what fraction did we keep." This is the
  number to watch when comparing lattice changes, since it removes the
  near-irreducible decay term.

For the exact decay/aperture split of any design, `optimization/decompose_losses.py`
runs the authoritative two-run (decay-on/off) measurement.

## Reproduce

```bash
cd optimization
# exact decay vs aperture split (two-run) for a design
python decompose_losses.py --params results/params_nominal.json \
    --config config_phaseE.yaml --n-events 400 --beam initial_muplus.dat \
    --out results/decomp_nominal
# transmission-focused optimization (maximize aperture survival)
python run_optimization.py --config config_transmission.yaml
```
