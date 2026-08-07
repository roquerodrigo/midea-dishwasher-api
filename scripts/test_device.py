#!/usr/bin/env python3
"""Connect to the real dishwasher over LAN V3 and exercise the operations.

Usage:
    uv run python scripts/test_device.py                    # query (default)
    uv run python scripts/test_device.py --power-on
    uv run python scripts/test_device.py --power-off
    uv run python scripts/test_device.py --start eco        # start the eco cycle
    uv run python scripts/test_device.py --bright 3         # set the rinse-aid level
    uv run python scripts/test_device.py --debug            # print wire bytes
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from device_env import load_env

from midea_dishwasher_api import BrightLevel, Client, DishwasherStatus, Mode
from midea_dishwasher_api.transport import V3Transport


def _hex_dump(direction: str, data: bytes) -> None:
    print(f"  [{direction}] {len(data):3d}B  {data.hex()}", file=sys.stderr)


def _print_status(s: DishwasherStatus) -> None:
    print("\n=== DishwasherStatus ===")
    print(f"  machine_state = {s.machine_state.value if s.machine_state else '-'}")
    print(f"  cycle_state   = {s.cycle_state.value if s.cycle_state else '-'}")
    print(f"  wash_stage    = {s.wash_stage.name if hasattr(s.wash_stage, 'name') else s.wash_stage}")
    print(f"  left_time     = {f'{s.left_time} min' if s.left_time is not None else '-'}")
    print(f"  error_code    = {s.error_code.name if hasattr(s.error_code, 'name') else s.error_code}")
    print(f"  door_closed   = {s.door_closed}")
    print(f"  bright_lack   = {s.bright_lack}  (rinse aid ran out)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=Path(__file__).parent.parent / ".env")
    parser.add_argument("--debug", action="store_true", help="print wire bytes")
    parser.add_argument(
        "--start", metavar="MODE",
        help="start a cycle in the given mode (auto, eco, intensive, normal, …)",
    )
    parser.add_argument(
        "--extra-dry", action="store_true",
        help="enable extra drying when starting the cycle (additional=1)",
    )
    parser.add_argument("--power-on", action="store_true")
    parser.add_argument("--power-off", action="store_true")
    parser.add_argument("--stop", action="store_true", help="cancel the running cycle")
    parser.add_argument(
        "--bright", type=lambda s: BrightLevel(int(s)),
        help="rinse-aid level 1..5",
    )
    parser.add_argument(
        "--refresh-after", type=float, default=3.0,
        help="seconds to wait before the final query (default 3.0)",
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    env = load_env(args.env)
    try:
        host = env["DEVICE_HOST"]
        port = int(env.get("DEVICE_PORT", "6444"))
        device_id = int(env["DEVICE_ID"])
        token = bytes.fromhex(env["DEVICE_TOKEN"])
        key = bytes.fromhex(env["DEVICE_KEY"])
    except KeyError as e:
        sys.exit(f"missing env var: {e}")

    print(f"connecting to {host}:{port}  device_id={device_id}")

    on_wire = _hex_dump if args.debug else None
    with V3Transport(
        host=host, port=port,
        device_id=device_id, token=token, key=key,
        on_wire=on_wire,
    ) as transport:
        client = Client(send=transport)

        ran_action = False
        if args.power_on:
            print(">>> power_on()")
            client.power_on()
            ran_action = True
        if args.power_off:
            print(">>> power_off()")
            client.power_off()
            ran_action = True
        if args.stop:
            print(">>> cancel_work()")
            client.cancel_work()
            ran_action = True
        if args.bright is not None:
            print(f">>> set_bright({args.bright})")
            client.set_bright(args.bright)
            ran_action = True
        if args.start:
            print(f">>> start_to_work(mode={args.start}, extra_drying={args.extra_dry})")
            client.start_to_work(mode=Mode(args.start), extra_drying=args.extra_dry)
            ran_action = True

        if ran_action:
            print(f"... waiting {args.refresh_after}s for the machine to update")
            time.sleep(args.refresh_after)

        print(">>> query_status()")
        _print_status(client.query_status())

    return 0


if __name__ == "__main__":
    sys.exit(main())
