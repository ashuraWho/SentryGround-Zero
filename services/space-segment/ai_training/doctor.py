# Report toolchain + optional Python deps for Sentry-Sat AI and console workflows.
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path


def _has(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> None:
    print("== Sentry-Sat doctor ==")
    print("python:", sys.executable, sys.version.split()[0])

    for cmd in ("cmake", "cc", "c++"):
        p = shutil.which(cmd)
        print(f"{cmd}: {'[ok] ' + p if p else '[missing]'}")

    pkgs = ["numpy", "tensorflow", "sklearn", "shap", "textual"]
    for p in pkgs:
        print(f"import {p}:", "[ok]" if _has(p) else "[missing]")

    root = Path(__file__).resolve().parent
    cfg = root / "config.default.json"
    print("config.default.json:", "[ok]" if cfg.is_file() else "[missing]")


if __name__ == "__main__":
    main()
