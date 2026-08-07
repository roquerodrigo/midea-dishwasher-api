#!/usr/bin/env python3
"""Query the device and dump every body byte with its index.

Usage:
    uv run python scripts/dump_state.py > tmp/state_before.txt
    # (restart / clear the filter warning on the machine)
    uv run python scripts/dump_state.py > tmp/state_after.txt
    diff tmp/state_before.txt tmp/state_after.txt
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from device_env import load_env

from midea_dishwasher_api.protocol import build_query, parse_frame
from midea_dishwasher_api.transport import V3Transport


def main() -> int:
    env = load_env(Path(__file__).parent.parent / ".env")
    host = env["DEVICE_HOST"]
    port = int(env.get("DEVICE_PORT", "6444"))
    device_id = int(env["DEVICE_ID"])
    token = bytes.fromhex(env["DEVICE_TOKEN"])
    key = bytes.fromhex(env["DEVICE_KEY"])

    with V3Transport(
        host=host, port=port,
        device_id=device_id, token=token, key=key,
    ) as transport:
        response = transport(build_query())

    msg_type, body = parse_frame(response)
    print(f"# captured {datetime.now().isoformat(timespec='seconds')}")
    print(f"# host={host} device_id={device_id}")
    print(f"# msg_type=0x{msg_type:02x}  body_len={len(body)}")
    print(f"# raw_frame={response.hex()}")
    print()
    for i, b in enumerate(body):
        marker = "  ← reserved" if i in (12, 14, 15, 22, 25, 26, 27, 29, 37, 38, 39, 40, 41) else ""
        print(f"body[{i:2d}] = 0x{b:02x}  ({b:3d}){marker}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
