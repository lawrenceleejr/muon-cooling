#!/usr/bin/env python3
"""Stamp a design's parameters into an hfofo.in card in place.

    python apply_design.py ../hfofo/hfofo.in ../hfofo/optimized_balanced.json
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from muopt.parameters import apply_parameters

card, design = sys.argv[1], sys.argv[2]
params = {k: v for k, v in json.load(open(design)).items() if not k.startswith("_")}
apply_parameters(card, params)
print(f"applied {list(params)} to {card}")
