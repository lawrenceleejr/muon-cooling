"""Tunable parameters and G4beamline input-card templating.

A :class:`Parameter` is a single ``param NAME=value`` knob in ``hfofo.in`` with a
search range. A :class:`ParameterSpace` is the set the optimizer searches over.

Substitution is deliberately literal: for each parameter we rewrite the matching
``param NAME=...`` line in the card, preserving everything else. This keeps the
physics card readable and avoids a bespoke templating language.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Parameter:
    name: str
    low: float
    high: float
    nominal: float
    log: bool = False           # sample on a log scale
    integer: bool = False       # round to nearest integer

    def clip(self, value):
        value = max(self.low, min(self.high, value))
        return int(round(value)) if self.integer else float(value)


class ParameterSpace:
    def __init__(self, parameters):
        self.parameters = list(parameters)
        self._by_name = {p.name: p for p in self.parameters}

    def __iter__(self):
        return iter(self.parameters)

    def __len__(self):
        return len(self.parameters)

    @property
    def names(self):
        return [p.name for p in self.parameters]

    def nominal(self):
        return {p.name: p.nominal for p in self.parameters}

    def clip(self, values):
        return {n: self._by_name[n].clip(v) for n, v in values.items()}

    @classmethod
    def from_config(cls, cfg):
        params = []
        for name, spec in cfg.items():
            params.append(Parameter(
                name=name,
                low=float(spec["low"]),
                high=float(spec["high"]),
                nominal=float(spec.get("nominal", 0.5 * (spec["low"] + spec["high"]))),
                log=bool(spec.get("log", False)),
                integer=bool(spec.get("integer", False)),
            ))
        return cls(params)


_PARAM_RE_CACHE = {}


def _param_regex(name):
    if name not in _PARAM_RE_CACHE:
        # Matches:  param NAME=<value>   (optionally with trailing comment)
        _PARAM_RE_CACHE[name] = re.compile(
            rf"^(\s*param\s+{re.escape(name)}\s*=)(\S+)(.*)$"
        )
    return _PARAM_RE_CACHE[name]


def apply_parameters(card_path, values):
    """Rewrite ``param NAME=...`` lines in ``card_path`` from the dict ``values``.

    Raises ``KeyError`` if a requested parameter has no matching ``param`` line,
    which catches typos / drift between the config and the card.
    """
    with open(card_path, "r") as fh:
        lines = fh.readlines()

    remaining = dict(values)
    for i, line in enumerate(lines):
        for name in list(remaining):
            m = _param_regex(name).match(line)
            if m:
                val = remaining.pop(name)
                val_str = f"{val:g}" if isinstance(val, float) else str(val)
                lines[i] = f"{m.group(1)}{val_str}{m.group(3)}\n"
                break

    if remaining:
        raise KeyError(
            f"No `param` line found in {card_path} for: {sorted(remaining)}"
        )

    with open(card_path, "w") as fh:
        fh.writelines(lines)
