# HFOFO muon ionization-cooling channel

G4beamline configuration for the **HFOFO** (Helical FOFO snake) muon
ionization-cooling channel, plus a framework for optimizing its cooling
performance and transmission.

The HFOFO snake cools a muon beam in all six phase-space dimensions using a
periodic lattice of **tilted solenoids** (alternating-sign, rotated period to
period), **325 MHz RF pillbox cavities** (which restore longitudinal momentum),
and **LiH wedge absorbers** (where the actual ionization cooling happens). The
design goal is to shrink the 6D emittance as much as possible while keeping as
many muons as possible.

## Repository layout

| Path | What it is |
|------|------------|
| [`hfofo/`](hfofo/) | **The configuration.** The full 31-period HFOFO cooling lattice as a G4beamline input card (`hfofo.in`) plus its include files (solenoid / RF / absorber placement, detectors, beam). |
| [`optimization/`](optimization/) | **The optimization framework.** Wraps the G4beamline Monte-Carlo in a sample-efficient black-box optimizer that trades 6D cooling against transmission. |
| [`analysis/`](analysis/) | Standalone analysis helpers (emittance calculation, G4beamline I/O, plotting). |
| [`docs/`](docs/) | Methodology notes, including how the optimization is set up and why. |
| `.github/workflows/ci.yml` | CI: runs the framework unit tests and smoke-tests the HFOFO config inside the published g4beamline image. |

## Running a simulation

The simulation runs inside the G4beamline container image published by the
companion repository
[`lawrenceleejr/g4beamline`](https://github.com/lawrenceleejr/g4beamline)
(`ghcr.io/lawrenceleejr/g4beamline:main`):

```bash
docker pull ghcr.io/lawrenceleejr/g4beamline:main

# run the HFOFO channel
docker run --rm --network none -e QT_QPA_PLATFORM=offscreen \
    -v "$PWD/hfofo":/work -w /work \
    ghcr.io/lawrenceleejr/g4beamline:main \
    bash -lc 'echo "/usr/local/share/geant4/install/4.11.0.2/share/Geant4-11.0.2/data" > /opt/g4beamline/build/.data && g4bl hfofo.in'
```

Three flags matter (see [`hfofo/README.md`](hfofo/README.md)): `--network none`
and the `.data` file stop g4bl from launching its dataset-downloader GUI (which
hangs headless), and `QT_QPA_PLATFORM=offscreen` lets the Qt-linked binary run
without a display. If you have a native `g4bl` on your `PATH` you can just run
`g4bl hfofo.in` from inside `hfofo/`.

## Optimizing

```bash
cd optimization
pip install -r requirements.txt
python run_optimization.py --config config.yaml        # Bayesian optimization
python run_optimization.py --config config.yaml --baseline   # just the nominal design
```

The optimizer treats one g4bl run as a black box: it rewrites the tunable
`param` lines in `hfofo.in`, runs the MC, reads transmission and 6D emittance
back from the detector output, and combines them into a single merit. See
[`optimization/README.md`](optimization/README.md) and
[`docs/optimization.md`](docs/optimization.md).

## Optimization campaign result

A full optimization campaign (~500 g4beamline runs) is written up in
[`docs/campaign/`](docs/campaign/). It found a design (**`brightE2`**) that
delivers **1.80× the 6D phase-space brightness** of the published lattice —
exit 6D emittance 104 vs 243 mm³ (2.3× lower) at 78% of nominal transmission,
validated across three Monte-Carlo seeds. Parameters:
[`hfofo/optimized.json`](hfofo/optimized.json) (with a conservative 1.33×
alternative in [`hfofo/optimized_conservative.json`](hfofo/optimized_conservative.json)).
The design was found by re-optimizing directly on exit brightness after the
report showed the intuitive "cooling factor" merit is misleading — and it
documents why several designs that looked far better under naive metrics were
artifacts of the wrong reference plane or low statistics.

## References

- Paper: <https://inspirehep.net/literature/1678715>
- G4beamline: <https://www.muonsinc.com/Website1/G4beamline>
- g4beamline container / build: <https://github.com/lawrenceleejr/g4beamline>
- HFOFO parameters table: [Google Sheet](https://docs.google.com/spreadsheets/d/1v1Zpk70Wd7Xph-NIqhxQTbpvZjtH8FXlnIF7LXRRGIw/edit?gid=410509727#gid=410509727)
- Indico: <https://indico.phys.utk.edu/category/27/>
