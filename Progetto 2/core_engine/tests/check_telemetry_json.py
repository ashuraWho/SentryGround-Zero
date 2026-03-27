#!/usr/bin/env python3
"""Run sentry_sat_sim and assert two valid [json] telemetry lines are emitted."""
from __future__ import annotations

import json
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_telemetry_json.py /path/to/sentry_sat_sim", file=sys.stderr)
        return 2
    exe = sys.argv[1]
    proc = subprocess.run([exe], capture_output=True, text=True, timeout=60)
    out = proc.stdout + proc.stderr
    if proc.returncode != 0:
        print(out)
        return proc.returncode

    lines = [ln for ln in out.splitlines() if ln.strip().startswith("[json] ")]
    if len(lines) < 2:
        print("expected >= 2 [json] lines, got:", len(lines), file=sys.stderr)
        print(out[:2000], file=sys.stderr)
        return 1

    for raw in lines[:2]:
        payload = raw.split("[json] ", 1)[1].strip()
        obj = json.loads(payload)
        assert obj.get("telemetry_schema") == "sentry_sat.obc.v1"
        assert "cycle_id" in obj and "anomaly" in obj and "signature_hex" in obj
    print("OK:", len(lines), "json telemetry lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
