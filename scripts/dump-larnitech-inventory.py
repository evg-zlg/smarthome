#!/usr/bin/env python3
"""Read the complete Larnitech API2 device inventory over WebSocket."""
from __future__ import annotations

import argparse
import json
import sys

import websocket


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://192.168.1.185:2041/api")
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()

    connection = websocket.create_connection(args.url, timeout=30)
    try:
        connection.send(json.dumps({"request": "authorize", "key": args.api_key}))
        authorization = json.loads(connection.recv())
        if authorization.get("response") != "authorize" or authorization.get("error"):
            raise SystemExit(f"Larnitech authorization failed: {authorization}")
        connection.send(json.dumps({"request": "get-devices", "status": "detailed"}))
        # Некоторые старые конфигурации содержат управляющие символы в именах.
        # API2 отдаёт их без экранирования; strict=False позволяет сохранить
        # такую сущность в инвентаризации, не изменяя контроллер.
        response = json.loads(connection.recv(), strict=False)
        json.dump(response, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
