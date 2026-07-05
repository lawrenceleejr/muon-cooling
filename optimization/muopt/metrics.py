"""Beam metrics for the HFOFO cooling channel.

Reads G4beamline virtual-detector / NTuple ASCII output and computes the two
quantities the optimizer cares about:

  * transmission  -- fraction of launched muons that survive to a plane
  * 6D emittance  -- normalized phase-space volume (the "cooling" figure)

Everything here is pure NumPy and has no dependency on G4beamline, so it can be
unit-tested on synthetic beams in CI without running a simulation.

Units (G4beamline convention): position in mm, momentum in MeV/c, time in ns.
"""

from __future__ import annotations

import dataclasses
import numpy as np

# Physical constants
MUON_MASS = 105.6583745  # MeV/c^2
C_LIGHT = 299.792458     # mm/ns

# Standard G4beamline BLTrackFile column order.
_COLUMNS = ["x", "y", "z", "px", "py", "pz", "t",
            "PDGid", "EventID", "TrackID", "ParentID", "Weight"]

# 6x6 symplectic unit matrix (block-diagonal {{0,1},{-1,0}}).
_S6 = np.array([
    [0, 1, 0, 0, 0, 0],
    [-1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0],
    [0, 0, -1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, -1, 0],
], dtype=float)


def read_detector(path):
    """Load a G4beamline ASCII detector/NTuple file into a structured array.

    Returns a dict of 1D NumPy arrays keyed by column name. Lines beginning with
    ``#`` are comments. An empty / header-only file yields zero-length arrays.
    """
    rows = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 9:
                continue
            rows.append([float(p) for p in parts[:len(_COLUMNS)]])
    if not rows:
        return {c: np.zeros(0) for c in _COLUMNS}
    arr = np.array(rows, dtype=float)
    # Pad if the file omits trailing optional columns.
    if arr.shape[1] < len(_COLUMNS):
        pad = np.zeros((arr.shape[0], len(_COLUMNS) - arr.shape[1]))
        arr = np.hstack([arr, pad])
    return {c: arr[:, i] for i, c in enumerate(_COLUMNS)}


def count_muons(data, p_low=0.0, p_high=1e9):
    """Number of muons (PDGid +-13) within an optional total-momentum window."""
    if len(data["x"]) == 0:
        return 0
    is_mu = np.abs(data["PDGid"]) == 13
    p = np.sqrt(data["px"] ** 2 + data["py"] ** 2 + data["pz"] ** 2)
    sel = is_mu & (p > p_low) & (p < p_high)
    return int(np.count_nonzero(sel))


def transmission(n_in, n_out):
    """Survival fraction. Returns 0.0 if no particles entered."""
    if n_in <= 0:
        return 0.0
    return float(n_out) / float(n_in)


@dataclasses.dataclass
class EmittanceResult:
    """6D emittance breakdown at one plane (all values in mm, normalized)."""
    eps_x: float          # transverse eigen-emittance 1
    eps_y: float          # transverse eigen-emittance 2
    eps_z: float          # longitudinal eigen-emittance
    eps_6d: float         # 6D = eps_x * eps_y * eps_z   (mm^3)
    eps_trans: float      # geometric transverse RMS emittance (sqrt of x-px det)
    eps_long: float       # geometric longitudinal RMS emittance
    n_particles: int
    mean_momentum: float


def _selected_muons(data, p_low, p_high):
    is_mu = np.abs(data["PDGid"]) == 13
    p = np.sqrt(data["px"] ** 2 + data["py"] ** 2 + data["pz"] ** 2)
    sel = is_mu & (p > p_low) & (p < p_high)
    return sel, p


def compute_emittance(data, p0=247.5, Bz0=2.8, p_low=100.0, p_high=400.0,
                      f_rf=0.325, fold_rf=True):
    """Normalized 6D emittance from the covariance of the canonical phase space.

    Follows the standard HFOFO analysis: build the 6-vector

        u = ( x,  px/p0 + kappa*Ax,
              y,  py/p0 + kappa*Ay,
             -c*t,  (gamma/gamma0 - 1)/beta0^2 )

    where the canonical (angular-momentum-subtracting) transverse momentum uses
    the on-axis solenoid potential A = (-Bz0*y/2, Bz0*x/2). The normalized
    eigen-emittances are beta0*gamma0 * Im(eig(-Sigma @ S6)); the 6D emittance is
    their product. ``Bz0`` enters only through the canonical correction and is
    applied identically at every plane, so cooling *ratios* are insensitive to
    its precise value.

    ``fold_rf`` wraps arrival times into a single RF bucket (period 1/f_rf,
    f_rf in GHz) about the beam's circular-mean phase. Without this, a beam
    spread over several buckets gets a bucket-to-bucket "length" that dwarfs the
    true bunch length and corrupts the eigen-decomposition.

    Returns an :class:`EmittanceResult`, or ``None`` if fewer than 6 muons pass
    the momentum window (covariance ill-defined / meaningless statistics).
    """
    sel, p = _selected_muons(data, p_low, p_high)
    n = int(np.count_nonzero(sel))
    if n < 6:
        return None

    x = data["x"][sel]
    y = data["y"][sel]
    px = data["px"][sel]
    py = data["py"][sel]
    pz = data["pz"][sel]
    t = data["t"][sel]
    ptot = p[sel]

    if fold_rf and f_rf > 0:
        omega = 2.0 * np.pi * f_rf  # rad/ns
        phase = omega * t
        # circular mean of the RF phase, so the fold is centered on the bunch
        phi0 = np.arctan2(np.mean(np.sin(phase)), np.mean(np.cos(phase)))
        t = (np.mod(phase - phi0 + np.pi, 2.0 * np.pi) - np.pi) / omega

    m = MUON_MASS
    gamma0 = np.sqrt(1.0 + (p0 / m) ** 2)
    beta0 = (p0 / m) / gamma0
    # kappa converts (B*length) into the magnetic-rigidity-scaled potential term.
    # 0.299792458 GeV/(T*m) rigidity; here p0 in MeV/c, B in T, x in mm:
    #   kappa * A has units of momentum/p0 (dimensionless), matching px/p0.
    kappa = C_LIGHT / p0 / 1000.0  # (mm/ns)/(MeV/c)/1000 -> consistent w/ B[T], x[mm]

    Ax = -0.5 * Bz0 * y
    Ay = 0.5 * Bz0 * x

    gamma = np.sqrt(1.0 + (px ** 2 + py ** 2 + pz ** 2) / m ** 2)
    delta = (gamma / gamma0 - 1.0) / beta0 ** 2

    u = np.column_stack([
        x,
        px / p0 + kappa * Ax,
        y,
        py / p0 + kappa * Ay,
        -C_LIGHT * t,
        delta,
    ])
    u = u - u.mean(axis=0, keepdims=True)
    cov = (u.T @ u) / n

    # Geometric eigen-emittances of each 2D block.
    def block_emit(i):
        a, d, b = cov[i, i], cov[i + 1, i + 1], cov[i, i + 1]
        val = a * d - b * b
        return float(np.sqrt(val)) if val > 0 else 0.0

    eps_trans = block_emit(0)  # x-px block (one transverse plane, geometric)
    eps_long = block_emit(4)   # longitudinal block (geometric)

    # Normalized eigen-emittances via the symplectic eigenvalue problem.
    try:
        vals = np.linalg.eigvals(-cov @ _S6)
        pos = np.array([np.imag(v) for v in vals if np.imag(v) > 1e-12])
        pos = np.sort(pos)[::-1]
    except np.linalg.LinAlgError:
        pos = np.array([])

    norm = beta0 * gamma0
    if len(pos) >= 3:
        e1, e2, e3 = norm * pos[0], norm * pos[1], norm * pos[2]
    else:
        # Fall back to block emittances if the eigen-decomposition degenerates.
        e1 = e2 = norm * eps_trans
        e3 = norm * eps_long

    eps_6d = float(e1 * e2 * e3)

    return EmittanceResult(
        eps_x=float(e1),
        eps_y=float(e2),
        eps_z=float(e3),
        eps_6d=eps_6d,
        eps_trans=float(eps_trans),
        eps_long=float(eps_long),
        n_particles=n,
        mean_momentum=float(np.mean(ptot)),
    )
