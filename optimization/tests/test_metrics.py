"""Unit tests for metrics + parameter templating.

These run without G4beamline (synthetic beams), so they execute in CI on every
push. They pin down the two things that must stay correct: emittance scaling and
input-card substitution.
"""

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from muopt import metrics
from muopt.parameters import ParameterSpace, apply_parameters


def _gaussian_beam(n, sx, spx, sy, spy, st, sdp, p0=247.5, seed=1):
    """Build a detector-style dict for an uncorrelated Gaussian muon beam."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, sx, n)
    y = rng.normal(0, sy, n)
    # small angles -> px ~ p0 * x'
    px = rng.normal(0, spx, n) * p0
    py = rng.normal(0, spy, n) * p0
    dp = rng.normal(0, sdp, n)
    pz = np.sqrt(np.maximum((p0 * (1 + dp)) ** 2 - px ** 2 - py ** 2, 1.0))
    t = rng.normal(0, st, n)
    return {
        "x": x, "y": y, "z": np.zeros(n),
        "px": px, "py": py, "pz": pz, "t": t,
        "PDGid": -13 * np.ones(n), "EventID": np.arange(n),
        "TrackID": np.ones(n), "ParentID": np.zeros(n), "Weight": np.ones(n),
    }


def test_transmission():
    assert metrics.transmission(100, 50) == 0.5
    assert metrics.transmission(0, 0) == 0.0
    assert metrics.transmission(10, 10) == 1.0


def test_count_muons_momentum_window():
    beam = _gaussian_beam(500, 10, 0.01, 10, 0.01, 1.0, 0.02)
    n_all = metrics.count_muons(beam)
    n_win = metrics.count_muons(beam, p_low=100, p_high=400)
    assert n_all == 500
    assert 0 < n_win <= 500


def test_emittance_runs_and_is_positive():
    beam = _gaussian_beam(3000, 20, 0.02, 20, 0.02, 2.0, 0.03)
    res = metrics.compute_emittance(beam, Bz0=0.0)  # Bz0=0 => kinetic emittance
    assert res is not None
    assert res.eps_6d > 0
    assert res.eps_x > 0 and res.eps_y > 0 and res.eps_z > 0
    assert res.n_particles > 1000


def test_emittance_scales_with_beam_size():
    """A tighter beam must have smaller 6D emittance (cooling sanity check)."""
    wide = _gaussian_beam(4000, 30, 0.03, 30, 0.03, 3.0, 0.04, seed=2)
    tight = _gaussian_beam(4000, 15, 0.015, 15, 0.015, 1.5, 0.02, seed=3)
    e_wide = metrics.compute_emittance(wide, Bz0=0.0)
    e_tight = metrics.compute_emittance(tight, Bz0=0.0)
    assert e_tight.eps_6d < e_wide.eps_6d


def test_emittance_too_few_particles():
    beam = _gaussian_beam(3, 10, 0.01, 10, 0.01, 1.0, 0.02)
    assert metrics.compute_emittance(beam) is None


def test_parameter_space_clip():
    space = ParameterSpace.from_config({
        "BLS": {"low": 18, "high": 25, "nominal": 21.4},
        "n": {"low": 1, "high": 10, "nominal": 5, "integer": True},
    })
    clipped = space.clip({"BLS": 100.0, "n": 3.6})
    assert clipped["BLS"] == 25.0
    assert clipped["n"] == 4
    assert set(space.names) == {"BLS", "n"}


def test_apply_parameters_rewrites_card():
    with tempfile.TemporaryDirectory() as d:
        card = os.path.join(d, "test.in")
        with open(card, "w") as fh:
            fh.write("param BLS=21.4\nparam Grad=25 # comment\nphysics QGSP_BIC\n")
        apply_parameters(card, {"BLS": 20.0, "Grad": 28})
        text = open(card).read()
        assert "param BLS=20" in text
        assert "param Grad=28 # comment" in text
        assert "physics QGSP_BIC" in text


def test_apply_parameters_missing_raises():
    with tempfile.TemporaryDirectory() as d:
        card = os.path.join(d, "test.in")
        with open(card, "w") as fh:
            fh.write("param BLS=21.4\n")
        try:
            apply_parameters(card, {"NoSuchParam": 1.0})
        except KeyError:
            return
        raise AssertionError("expected KeyError for missing param")
