# HFOFO cooling-channel G4beamline configuration

This directory **is** the configuration — a self-contained G4beamline model of
the 31-period HFOFO cooling channel. It is the canonical version of Yuri
Alexahin's "track_v7" design, restructured so the optimizer-tunable knobs live
in one block at the top of `hfofo.in`.

## Files

| File | Contents |
|------|----------|
| `hfofo.in` | Main input card. Physics, beam, fields, detectors, data read-out. The `OPTIMIZER PARAMETERS` block at the top holds the tunable `param` lines. |
| `sol_place.txt` | Placement of all solenoids (per-period currents, tilts, rolls). |
| `solangles1.dat`, `solangles2.dat` | Per-solenoid pitch/roll angles for the matching sections. |
| `abs_place.txt` | Placement of the LiH wedge absorbers and collimator/pressure-wall tubes. |
| `RFplace.txt` | Placement and timing offsets of the 325 MHz RF cavities. |
| `detectors.txt` | One `virtualdetector` per period (`Det1`…`Det31`) → `out1.txt`…`out31.txt`. |
| `initial.dat` | Example upstream beam (ICOOL output) if you want to inject a realistic beam instead of the Gaussian. |

## Geometry at a glance

- **Period length** 4200 mm, **31 periods** + matching solenoid + exit solenoid.
- Six solenoids per period, alternating sign, each rotated 120° from the last —
  this is what makes the snake "helical" and gives simultaneous focusing in all
  planes.
- RF cavities (325 MHz, ~25 MV/m) restore the longitudinal momentum lost in the
  absorbers; their `timeOffset`s are phased to the reference particle.
- LiH wedge absorbers provide the ionization energy loss (cooling) with the
  wedge shape coupling energy spread to position for emittance exchange.

## Detectors / output

Each period boundary has a virtual detector. The optimizer reads:

- `out1.txt`  — beam at the entrance of the cooling section (first full period)
- `out31.txt` — beam at the exit (last period)

and computes transmission (`N_out/N_in`) and the 6D normalized emittance at each
plane. `mu_plus_beam.txt` is a finer `zntuple` sampling the beam every period for
diagnostics / plotting.


## Optimized "balanced" design

A 7-parameter optimization campaign (see [`../docs/campaign/`](../docs/campaign/))
found a design that delivers **1.33× the 6D phase-space brightness** of the
published lattice — exit 6D emittance 160 vs 243 mm³ (1.5× lower) at 88% of the
nominal transmission. Its parameters are in
[`optimized_balanced.json`](optimized_balanced.json); apply them with:

```bash
python ../optimization/apply_design.py hfofo.in optimized_balanced.json
```

| knob | nominal | balanced |
|------|:-------:|:--------:|
| `BLS` | 21.4 | 22.38 |
| `Grad` | 25 | 26.7 |
| `Grad0` | 20 | 22.1 |
| `delf` | 0 | 0.045 |
| `pitchFactor` | 1.0 | 1.06 |
| `dtRF` | 0 | −0.127 |
| `wedgeScale` | 1.0 | 2.87 |

## Tunable parameters

The `OPTIMIZER PARAMETERS` block at the top of `hfofo.in`:

| `param` | Meaning | Nominal |
|---------|---------|---------|
| `BLS`   | Overall solenoid field-strength scale (focusing) | 21.4 |
| `Grad`  | RF gradient in the main snake cavities (MV/m) | 25 |
| `Grad0` | RF gradient in the matching cavities (MV/m) | 20 |
| `delf`  | SolPos/SolNeg current asymmetry | 0 |
| `nEvents` | Number of muons tracked (set by the runner) | 100 |

These are deliberately a small set of global, physically-meaningful knobs. To
expose more (e.g. per-cavity timing, absorber wedge angle), add a `param` line in
the block and the absorber/RF placement files can reference it with `$name`.

## Running

```bash
# inside the published g4beamline container, from this directory mounted at /work
echo "/usr/local/share/geant4/install/4.11.0.2/share/Geant4-11.0.2/data" \
    > /opt/g4beamline/build/.data        # so g4bl finds the datasets, no GUI
QT_QPA_PLATFORM=offscreen g4bl hfofo.in  # offscreen: g4bl links Qt even in batch
```

> **Why these incantations?** g4bl checks for Geant4 datasets by version name and,
> if it thinks they're missing, launches `g4bldata` — a Qt GUI that never closes
> headless, so the run hangs forever. The image actually ships the right datasets;
> the `.data` file points g4bl straight at them so the GUI is never launched.
> `--network none` (when run via Docker) additionally prevents g4bldata from
> blocking on a network poll. The optimization framework's runner does all of
> this for you.
