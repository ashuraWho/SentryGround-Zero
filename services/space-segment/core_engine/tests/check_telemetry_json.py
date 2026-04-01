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
    proc = subprocess.run([exe], capture_output=True, timeout=60)
    out = proc.stdout
    
    if proc.returncode != 0:
        print(out.decode('utf-8', errors='ignore'))
        return proc.returncode

    sync_marker = b"\x1a\xcf\xfc\x1d"
    packets = out.split(sync_marker)[1:]
    
    if len(packets) < 2:
        print("expected >= 2 CCSDS packets, got:", len(packets), file=sys.stderr)
        return 1

    for pkt in packets[:2]:
        payload_len = int.from_bytes(pkt[4:6], byteorder='big') + 1
        payload = pkt[6:6+payload_len].decode('utf-8', errors='ignore')
        
        obj = json.loads(payload)
        assert obj.get("telemetry_schema") == "sentry_sat.obc.v2.ccsds"
        assert "cycle_id" in obj and "anomaly" in obj and "signature_hex" in obj
    print("OK:", len(packets), "CCSDS telemetry packets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
