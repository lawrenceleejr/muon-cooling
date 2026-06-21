# Analysis helpers

Standalone utilities for inspecting G4beamline output, kept separate from the
optimization framework (which has its own lean `metrics.py`).

| File | What |
|------|------|
| `read_g4bl_data.py` | Load G4beamline trace / virtual-detector ASCII files into pandas DataFrames, with derived columns (total momentum, angles, radius, canonical angular momentum). |
| `compute_emittance.py` | Full emittance analysis (`calculateEmittance`): RMS and Gaussian-fit 6D emittances, normalized emittances via the symplectic eigenvalue problem, beam sizes, Twiss-like betas, RF-phase fitting. Richer than the optimizer's `metrics.py`, useful for diagnostics and plots. |
| `set_plot_settings.py` | Matplotlib defaults (dpi, optional LaTeX fonts). |

Example:

```python
from compute_emittance import calculateEmittance
rms, fit, norm_rms, norm_fit = calculateEmittance("out31.txt", p0=247.5, Bz0=2.8)
```

For the lightweight, NumPy-only transmission + 6D emittance used inside the
optimizer, see `../optimization/muopt/metrics.py`.
