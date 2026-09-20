#!/usr/bin/env python3
"""Exercise every allowlisted Larnitech VAKIO control and restore initial state."""
from __future__ import annotations

import argparse
import json
import time
import urllib.request

import websocket

POWER = "407:220"
MODES = {
    "inflow": "407:221", "inflow_max": "407:222", "recuperator": "407:223",
    "winter": "407:224", "outflow": "407:225", "outflow_max": "407:226",
    "night": "407:227",
}
SPEEDS = {str(value): f"407:{227 + value}" for value in range(1, 8)}


def snapshot(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=8) as response:
        return json.load(response)


def status_set(url: str, key: str, addr: str, value: str = "on") -> None:
    connection = websocket.create_connection(url, timeout=10)
    try:
        connection.send(json.dumps({"request": "authorize", "key": key}))
        authorization = json.loads(connection.recv())
        if authorization.get("response") != "authorize" or authorization.get("error"):
            raise RuntimeError("Larnitech authorization failed")
        connection.send(json.dumps({
            "request": "status-set", "addr": addr, "status": {"state": value},
        }))
        result = json.loads(connection.recv())
        devices = result.get("devices", [])
        if not any(item.get("addr") == addr and item.get("success") for item in devices):
            raise RuntimeError(f"Larnitech rejected {addr}={value}: {result}")
    finally:
        connection.close()


def wait_for_topic(health_url: str, topic: str, value: str, timeout: int = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = snapshot(health_url).get("vakio", {}).get("topics", {}).get(topic)
        if current == value:
            return
        time.sleep(0.5)
    raise RuntimeError(f"VAKIO did not confirm {topic}={value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--api2-url", default="ws://192.168.1.185:2041/api")
    parser.add_argument("--health-url", default="http://127.0.0.1/gateway/healthz")
    args = parser.parse_args()

    initial = snapshot(args.health_url).get("vakio", {}).get("topics", {})
    restore = {
        "state": initial.get("vakio/state"),
        "workmode": initial.get("vakio/workmode"),
        "speed": initial.get("vakio/speed"),
    }
    if restore["state"] not in {"on", "off"} or restore["workmode"] not in MODES or restore["speed"] not in SPEEDS:
        raise RuntimeError(f"Incomplete initial VAKIO telemetry: {restore}")

    verified: list[str] = []
    try:
        for value in ("on", "off"):
            status_set(args.api2_url, args.api_key, POWER, value)
            wait_for_topic(args.health_url, "vakio/state", value)
            verified.append(f"state={value}")
        for value, addr in MODES.items():
            status_set(args.api2_url, args.api_key, addr)
            wait_for_topic(args.health_url, "vakio/workmode", value)
            verified.append(f"workmode={value}")
        for value, addr in SPEEDS.items():
            status_set(args.api2_url, args.api_key, addr)
            wait_for_topic(args.health_url, "vakio/speed", value)
            verified.append(f"speed={value}")
    finally:
        status_set(args.api2_url, args.api_key, MODES[restore["workmode"]])
        wait_for_topic(args.health_url, "vakio/workmode", restore["workmode"])
        status_set(args.api2_url, args.api_key, SPEEDS[restore["speed"]])
        wait_for_topic(args.health_url, "vakio/speed", restore["speed"])
        status_set(args.api2_url, args.api_key, POWER, restore["state"])
        wait_for_topic(args.health_url, "vakio/state", restore["state"])

    print(json.dumps({"verified": verified, "restored": restore}, ensure_ascii=False))


if __name__ == "__main__":
    main()
