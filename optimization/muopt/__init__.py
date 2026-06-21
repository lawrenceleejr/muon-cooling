"""muopt -- optimization framework for the HFOFO muon ionization-cooling channel.

Wraps the (non-differentiable, stochastic, expensive) G4beamline Monte-Carlo in a
sample-efficient black-box optimizer that trades 6D cooling against transmission.

Modules:
    metrics     -- transmission + 6D normalized emittance from g4bl output
    runner      -- run g4bl in the published Docker image or a native install
    parameters  -- tunable knobs + input-card templating
    objective   -- one parameter point -> one scalar merit
    optimize    -- Optuna / scikit-optimize / random drivers + trial logging
"""

from .parameters import Parameter, ParameterSpace
from .objective import ObjectiveConfig, EvalResult, evaluate
from .runner import G4blRunner, detect_backend
from .optimize import run_optimization

__all__ = [
    "Parameter", "ParameterSpace", "ObjectiveConfig", "EvalResult",
    "evaluate", "G4blRunner", "detect_backend", "run_optimization",
]
