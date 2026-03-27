# Load training configuration from JSON with deep-merge over bundled defaults.
from __future__ import annotations

import json
import copy
from pathlib import Path

# Directory containing this helper and config.default.json alongside train_model.py.
_HERE = Path(__file__).resolve().parent
# Ships with the repo so `train_model.py` runs without a user config file.
DEFAULT_CONFIG_PATH = _HERE / "config.default.json"


def _deep_merge(base: dict, override: dict) -> dict:
    # Walk keys of override and recursively merge dictionaries; else replace scalars/lists.
    out = copy.deepcopy(base)
    for key, val in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def load_training_config(user_path: str | Path | None = None) -> dict:
    # Read default JSON dict from disk; raises FileNotFoundError if packaging broke.
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if user_path is None:
        return cfg
    p = Path(user_path)
    if not p.is_file():
        raise FileNotFoundError(f"Config not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        user = json.load(f)
    return _deep_merge(cfg, user)
