#!/usr/bin/env python3
"""Local Larnitech inventory and VAKIO Base Smart gateway."""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import paho.mqtt.client as mqtt
import websocket

HTTP_HOST = os.environ.get("GATEWAY_HTTP_HOST", "127.0.0.1")
HTTP_PORT = int(os.environ.get("GATEWAY_HTTP_PORT", "8080"))
LARNITECH_URL = os.environ.get("LARNITECH_URL", "http://192.168.1.185/API2/")
LARNITECH_WS_URL = os.environ.get("LARNITECH_WS_URL", "ws://192.168.1.185:2041/api")
LARNITECH_API_KEY = os.environ.get("LARNITECH_API_KEY", "")
LARNITECH_POLL_SECONDS = max(10, int(os.environ.get("LARNITECH_POLL_SECONDS", "30")))
LARNITECH_DETAILED_REFRESH_ADDRS = frozenset({"456:249"})
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "gateway")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
VAKIO_TOPIC = os.environ.get("VAKIO_TOPIC", "vakio").strip("/")
CONTROL_ENABLED = os.environ.get("CONTROL_ENABLED", "false").lower() == "true"
VAKIO_TELEMETRY_MAX_AGE = max(15, int(os.environ.get("VAKIO_TELEMETRY_MAX_AGE", "90")))
VAKIO_CONFIRM_TIMEOUT = max(1, int(os.environ.get("VAKIO_CONFIRM_TIMEOUT", "8")))
VAKIO_PRESENCE_POLL_SECONDS = max(
    30, int(os.environ.get("VAKIO_PRESENCE_POLL_SECONDS", "60"))
)
VAKIO_MODES = (
    "inflow", "inflow_max", "recuperator", "winter",
    "outflow", "outflow_max", "night",
)
VAKIO_SPEEDS = tuple(str(value) for value in range(1, 8))
VAKIO_RAW_COMMANDS: dict[tuple[str, str], str] = {
    ("state", "off"): "06000",
    ("state", "on"): "06001",
    ("workmode", "recuperator"): "06010",
    ("workmode", "winter"): "06011",
    ("workmode", "inflow"): "06021",
    ("workmode", "inflow_max"): "06022",
    ("workmode", "outflow"): "06031",
    ("workmode", "outflow_max"): "06032",
    ("workmode", "night"): "06041",
    **{("speed", str(value)): f"0650{value}" for value in range(1, 8)},
}


def parse_addr_map(raw: str, allowed_keys: tuple[str, ...], variable: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in raw.split(","):
        if not item.strip():
            continue
        key, separator, addr = item.partition("=")
        key, addr = key.strip(), addr.strip()
        if separator != "=" or key not in allowed_keys or not re.fullmatch(r"\d+:\d+", addr):
            raise RuntimeError(f"Invalid {variable} entry: {item!r}")
        if key in result:
            raise RuntimeError(f"Duplicate {variable} key: {key}")
        result[key] = addr
    return result


VAKIO_LARNITECH_BRIDGE_ENABLED = (
    os.environ.get("VAKIO_LARNITECH_BRIDGE_ENABLED", "false").lower() == "true"
)
VAKIO_LARNITECH_POWER_ADDR = os.environ.get("VAKIO_LARNITECH_POWER_ADDR", "").strip()
if VAKIO_LARNITECH_POWER_ADDR and not re.fullmatch(r"\d+:\d+", VAKIO_LARNITECH_POWER_ADDR):
    raise RuntimeError("Invalid VAKIO_LARNITECH_POWER_ADDR")
VAKIO_LARNITECH_MODE_ADDRS = parse_addr_map(
    os.environ.get("VAKIO_LARNITECH_MODE_ADDRS", ""), VAKIO_MODES,
    "VAKIO_LARNITECH_MODE_ADDRS",
)
VAKIO_LARNITECH_SPEED_ADDRS = parse_addr_map(
    os.environ.get("VAKIO_LARNITECH_SPEED_ADDRS", ""), VAKIO_SPEEDS,
    "VAKIO_LARNITECH_SPEED_ADDRS",
)
VAKIO_LARNITECH_ADDRS = tuple(filter(None, (
    VAKIO_LARNITECH_POWER_ADDR,
    *VAKIO_LARNITECH_MODE_ADDRS.values(),
    *VAKIO_LARNITECH_SPEED_ADDRS.values(),
)))
if len(set(VAKIO_LARNITECH_ADDRS)) != len(VAKIO_LARNITECH_ADDRS):
    raise RuntimeError("VAKIO Larnitech addresses must be unique")
if VAKIO_LARNITECH_BRIDGE_ENABLED and (
    not VAKIO_LARNITECH_POWER_ADDR
    or set(VAKIO_LARNITECH_MODE_ADDRS) != set(VAKIO_MODES)
    or set(VAKIO_LARNITECH_SPEED_ADDRS) != set(VAKIO_SPEEDS)
):
    raise RuntimeError("Enabled VAKIO Larnitech bridge requires power, all modes and speeds")
configured_subscribe_addrs = [
    addr.strip()
    for addr in os.environ.get("LARNITECH_SUBSCRIBE_ADDRS", "315:36,456:249").split(",")
    if addr.strip()
]
LARNITECH_SUBSCRIBE_ADDRS = tuple(dict.fromkeys(
    configured_subscribe_addrs + list(VAKIO_LARNITECH_ADDRS)
))
LARNITECH_SCENARIO_CONTROL_ENABLED = (
    os.environ.get("LARNITECH_SCENARIO_CONTROL_ENABLED", "false").lower() == "true"
)
LARNITECH_SCENARIO_COOLDOWN_SECONDS = max(
    5, int(os.environ.get("LARNITECH_SCENARIO_COOLDOWN_SECONDS", "30"))
)

# This immutable registry is the first allowlist boundary. The HTTP API never
# accepts an API2 status payload, only one of these exact scenario addresses.
SCENARIO_REGISTRY: dict[str, dict[str, str]] = {
    "315:246": {
        "name": "ушел",
        "risk": "high",
        "summary": "Закрывает шторы, выключает группы света и сценарий температуры.",
    },
    "315:250": {
        "name": "Доброе утро",
        "risk": "medium",
        "summary": "Включает свет и с задержкой открывает обе группы штор.",
    },
    "407:246": {
        "name": "я пришел",
        "risk": "high",
        "summary": "Открывает шторы, включает свет и запускает температурный сценарий.",
    },
    "407:247": {
        "name": "я ушел",
        "risk": "high",
        "summary": "Запускает «ушел», выключает кондиционер и управляет светом.",
    },
    "407:248": {
        "name": "Спокойной ночи",
        "risk": "high",
        "summary": "Закрывает шторы, выключает свет и выполняет отложенное затухание.",
    },
    "456:46": {
        "name": "темпер 1",
        "risk": "medium",
        "summary": "Переключает температурную автоматику по времени и состоянию «я ушел».",
    },
    "456:47": {
        "name": "темпер",
        "risk": "high",
        "summary": "Автоматически включает и выключает кондиционер по температуре.",
    },
}
configured_scenario_allowlist = {
    addr.strip()
    for addr in os.environ.get("LARNITECH_SCENARIO_ALLOWLIST", "").split(",")
    if addr.strip()
}
unknown_scenario_addrs = configured_scenario_allowlist - SCENARIO_REGISTRY.keys()
if unknown_scenario_addrs:
    raise RuntimeError(f"Unknown Larnitech scenario allowlist addresses: {sorted(unknown_scenario_addrs)}")
LARNITECH_SCENARIO_ALLOWLIST = frozenset(configured_scenario_allowlist)
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,80}$")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("smarthome-gateway")
lock = threading.Lock()
confirmation = threading.Condition(lock)
state: dict[str, Any] = {
    "started_at": time.time(),
    "mqtt": {"status": "waiting", "updated_at": None, "error": None},
    "larnitech": {
        "status": "not_configured", "updated_at": None, "heartbeat_at": None,
        "last_event_at": None, "subscribed_addrs": [], "reconnects": 0,
        "devices": [], "error": None,
    },
    "vakio": {
        "status": "waiting", "updated_at": None, "topics": {},
        "confirmed_topics": {}, "commanded_topics": {}, "error": None,
    },
}
mqtt_client: mqtt.Client | None = None
last_device_message_monotonic: float | None = None
pending_confirmation: tuple[str, str] | None = None
fresh_topic_versions: dict[str, int] = {}
fresh_topic_values: dict[str, tuple[str, float]] = {}
scenario_guard = threading.Lock()
scenario_runs: dict[str, dict[str, Any]] = {}
vakio_bridge_guard = threading.Lock()


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def age_seconds(timestamp: str | None) -> int | None:
    if not timestamp:
        return None
    try:
        updated = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return max(0, int((datetime.now(timezone.utc) - updated).total_seconds()))
    except (TypeError, ValueError):
        return None


def entity_by_addr(devices: list[dict[str, Any]], addr: str) -> dict[str, Any] | None:
    return next((device for device in devices if device.get("addr") == addr), None)


def entity_view(devices: list[dict[str, Any]], addr: str, label: str, unit: str | None = None) -> dict[str, Any]:
    device = entity_by_addr(devices, addr) or {}
    status = device.get("status") if isinstance(device.get("status"), dict) else {}
    return {
        "addr": addr,
        "label": label,
        "type": device.get("type"),
        "value": status.get("state"),
        "unit": unit,
        "available": bool(device),
        "status": status,
    }


def observed_map(result: dict[str, Any]) -> dict[str, Any]:
    """Build a small, stable read-only view from noisy API2 channels."""
    larnitech = result["larnitech"]
    devices = larnitech.get("devices", [])
    if not isinstance(devices, list):
        devices = []
    larnitech_age = age_seconds(larnitech.get("heartbeat_at") or larnitech.get("updated_at"))
    mqtt_age = age_seconds(result["mqtt"].get("updated_at"))
    vakio_age = age_seconds(result["vakio"].get("updated_at"))

    modules = [
        {"id": "407", "model": "MF-14.C", "role": "Основной контроллер", "channels": 27},
        {"id": "315", "model": "CW-CO2.C", "role": "Климат и движение", "channels": 9},
        {"id": "456", "model": "DW-RS485", "role": "Кондиционер / Modbus", "channels": 205},
        {"id": "500", "model": "DW-RGB03.B", "role": "RGB-подсветка", "channels": 12},
    ]
    present_ids = {str(device.get("addr", "")).split(":", 1)[0] for device in devices}
    for module in modules:
        module["status"] = "online" if module["id"] in present_ids else ("unknown" if not devices else "missing")

    climate = [
        entity_view(devices, "315:36", "CO₂", "ppm"),
        entity_view(devices, "315:32", "Температура", "°C"),
        entity_view(devices, "315:33", "Влажность", "%"),
    ]
    lights = [entity_view(devices, addr, label) for addr, label in (
        ("407:8", "Рабочая зона — левая"), ("407:9", "Рабочая зона — правая"),
        ("407:250", "Переговорная зона"),
    )]
    curtains = [entity_view(devices, addr, label) for addr, label in (
        ("407:3", "Шторы переговорной"), ("407:5", "Шторы 1"),
    )]
    ac = entity_view(devices, "456:249", "Кондиционер AC1")
    ac["connected"] = (entity_by_addr(devices, "456:237") or {}).get("status", {}).get("state") == "opened"
    ac["error"] = (entity_by_addr(devices, "456:230") or {}).get("status", {}).get("state")
    ac["alarm"] = (entity_by_addr(devices, "456:231") or {}).get("status", {}).get("state")
    ac["temperatures"] = {
        "indoor": entity_view(devices, "456:233", "В помещении", "°C")["value"],
        "supply": entity_view(devices, "456:235", "Воздух внутри", "°C")["value"],
    }

    errors: list[dict[str, str]] = []
    for source in ("larnitech", "mqtt", "vakio"):
        item = result[source]
        if item.get("error"):
            errors.append({"source": source, "message": str(item["error"])})
    if larnitech_age is not None and larnitech_age > LARNITECH_POLL_SECONDS * 3:
        errors.append({"source": "larnitech", "message": "Данные Larnitech устарели"})

    return {
        "services": {
            "pi": {"status": "online", "updated_at": utc_timestamp(), "age_seconds": 0},
            "larnitech": {"status": larnitech["status"], "updated_at": larnitech.get("updated_at"), "age_seconds": larnitech_age},
            "mqtt": {**result["mqtt"], "age_seconds": mqtt_age},
            "vakio": {"status": result["vakio"]["status"], "updated_at": result["vakio"].get("updated_at"), "age_seconds": vakio_age},
        },
        "physical_modules": modules,
        "api_channels": {"total": len(devices), "note": "Адресуемые каналы, не физические устройства"},
        "climate": climate,
        "air_conditioner": ac,
        "lights": lights,
        "curtains": curtains,
        "errors": errors,
        "read_only": True,
    }


def larnitech_response(connection: websocket.WebSocket) -> dict[str, Any]:
    response = json.loads(connection.recv(), strict=False)
    if not isinstance(response, dict):
        raise ValueError("Larnitech response is not an object")
    return response


def decode_larnitech_event_state(device_type: str | None, raw_status: str) -> int | float | str:
    """Decode only confirmed office sensor formats; keep unknown values raw."""
    if not raw_status.startswith("0x"):
        return raw_status
    try:
        payload = bytes.fromhex(raw_status[2:])
    except ValueError:
        return raw_status
    if not payload:
        return raw_status
    if device_type == "co2-sensor" and len(payload) >= 2:
        return int.from_bytes(payload[:2], "little", signed=False)
    if device_type == "temperature-sensor" and len(payload) >= 2:
        return round(int.from_bytes(payload[:2], "little", signed=True) / 100, 2)
    if device_type == "humidity-sensor":
        return int.from_bytes(payload[:2], "little", signed=False)
    if device_type in {"lamp", "switch", "virtual"}:
        return "on" if payload[0] & 1 else "off"
    return raw_status


def larnitech_update_state(update: dict[str, Any], device: dict[str, Any] | None) -> str | None:
    incoming = update.get("status")
    if isinstance(incoming, dict):
        value = incoming.get("state")
        return str(value) if value is not None else None
    if isinstance(incoming, str):
        decoded = decode_larnitech_event_state((device or {}).get("type"), incoming)
        return decoded if decoded in {"on", "off"} else None
    return None


def vakio_command_from_larnitech_update(
    update: dict[str, Any], devices: list[dict[str, Any]],
) -> dict[str, str] | None:
    """Translate exact allowlisted virtual buttons into an operating command."""
    addr = str(update.get("addr", ""))
    device = entity_by_addr(devices, addr)
    value = larnitech_update_state(update, device)
    if addr == VAKIO_LARNITECH_POWER_ADDR and value in {"on", "off"}:
        return {"command": "state", "value": value}
    if value != "on":
        # Mode and speed buttons are selectors. Switching one off is only a UI
        # event; the confirmed selector is restored from VAKIO telemetry.
        return None
    for mode, mode_addr in VAKIO_LARNITECH_MODE_ADDRS.items():
        if addr == mode_addr:
            return {"command": "workmode", "value": mode}
    for speed, speed_addr in VAKIO_LARNITECH_SPEED_ADDRS.items():
        if addr == speed_addr:
            return {"command": "speed", "value": speed}
    return None


def merge_larnitech_devices(devices: list[dict[str, Any]], updates: list[dict[str, Any]]) -> list[str]:
    """Merge API2 status messages into the detailed inventory in place."""
    by_addr = {str(device.get("addr")): device for device in devices}
    changed: list[str] = []
    for update in updates:
        addr = str(update.get("addr", ""))
        device = by_addr.get(addr)
        if not addr or device is None:
            continue
        incoming = update.get("status")
        if isinstance(incoming, dict):
            device.setdefault("status", {}).update(incoming)
        elif isinstance(incoming, str):
            device_status = device.setdefault("status", {})
            device_status["raw"] = incoming
            # AC events are packed binary frames. Preserve the last detailed
            # climate state until the worker refreshes the entity with a
            # status-get request instead of showing an opaque hex value.
            if device.get("type") != "AC":
                device_status["state"] = decode_larnitech_event_state(device.get("type"), incoming)
        else:
            continue
        changed.append(addr)
    return changed


def open_larnitech_connection() -> tuple[websocket.WebSocket, list[dict[str, Any]]]:
    connection = websocket.create_connection(LARNITECH_WS_URL, timeout=LARNITECH_POLL_SECONDS)
    connection.send(json.dumps({"request": "authorize", "key": LARNITECH_API_KEY}))
    authorization = larnitech_response(connection)
    if authorization.get("response") != "authorize" or authorization.get("error"):
        connection.close()
        raise ValueError(f"Larnitech authorization failed: {authorization}")

    connection.send(json.dumps({"request": "get-devices", "status": "detailed"}))
    inventory = larnitech_response(connection)
    devices = inventory.get("devices", [])
    if not isinstance(devices, list):
        connection.close()
        raise ValueError("Larnitech response has no devices list")

    for addr in LARNITECH_SUBSCRIBE_ADDRS:
        connection.send(json.dumps({"request": "status-subscribe", "addr": addr}))
        subscribed = larnitech_response(connection)
        if subscribed.get("response") != "status-subscribe" or subscribed.get("subscribed") != 1:
            connection.close()
            raise ValueError(f"Larnitech subscription failed for {addr}: {subscribed}")
        updates = subscribed.get("devices", [])
        if isinstance(updates, list):
            merge_larnitech_devices(devices, updates)
    return connection, devices


def larnitech_exchange(connection: websocket.WebSocket, request: dict[str, Any]) -> dict[str, Any]:
    connection.send(json.dumps(request, separators=(",", ":")))
    response = json.loads(connection.recv(), strict=False)
    if not isinstance(response, dict):
        raise ValueError("Larnitech response is not an object")
    if response.get("error"):
        raise ValueError(f"Larnitech request failed: {response.get('error')}")
    return response


def open_authorized_larnitech_connection(timeout: int = 10) -> websocket.WebSocket:
    connection = websocket.create_connection(LARNITECH_WS_URL, timeout=timeout)
    authorization = larnitech_exchange(
        connection, {"request": "authorize", "key": LARNITECH_API_KEY}
    )
    if authorization.get("response") != "authorize":
        connection.close()
        raise ValueError("Larnitech authorization was not confirmed")
    return connection


def larnitech_status_set(connection: websocket.WebSocket, addr: str, value: str) -> None:
    response = larnitech_exchange(
        connection,
        {"request": "status-set", "addr": addr, "status": {"state": value}},
    )
    if response.get("response") != "status-set" or not scenario_status_set_succeeded(response, addr):
        raise ValueError(f"Larnitech did not accept state for {addr}")


def desired_larnitech_vakio_states(command: str) -> dict[str, str]:
    with lock:
        topics = dict(state["vakio"].get("topics", {}))
    desired: dict[str, str] = {}
    if command == "state":
        current = topics.get(f"{VAKIO_TOPIC}/state")
        if current in {"on", "off"}:
            desired[VAKIO_LARNITECH_POWER_ADDR] = current
    elif command == "workmode":
        current = topics.get(f"{VAKIO_TOPIC}/workmode")
        if current in VAKIO_MODES:
            desired.update({addr: "on" if mode == current else "off" for mode, addr in VAKIO_LARNITECH_MODE_ADDRS.items()})
    elif command == "speed":
        current = topics.get(f"{VAKIO_TOPIC}/speed")
        if current in VAKIO_SPEEDS:
            desired.update({addr: "on" if speed == current else "off" for speed, addr in VAKIO_LARNITECH_SPEED_ADDRS.items()})
    return desired


def larnitech_vakio_state(devices: list[dict[str, Any]]) -> dict[str, Any]:
    """Read the user-facing VAKIO state from its Larnitech selectors."""
    states = {
        str(device.get("addr")): (device.get("status") or {}).get("state")
        for device in devices
        if isinstance(device, dict) and isinstance(device.get("status"), dict)
    }
    mode = next(
        (name for name, addr in VAKIO_LARNITECH_MODE_ADDRS.items() if states.get(addr) == "on"),
        None,
    )
    speed = next(
        (value for value, addr in VAKIO_LARNITECH_SPEED_ADDRS.items() if states.get(addr) == "on"),
        None,
    )
    power = states.get(VAKIO_LARNITECH_POWER_ADDR)
    return {
        "available": power in {"on", "off"},
        "power": power if power in {"on", "off"} else None,
        "mode": mode,
        "speed": speed,
        "source": "larnitech",
    }


def sync_larnitech_vakio_states(command: str) -> None:
    """Reflect confirmed device telemetry into the Larnitech virtual selectors."""
    if not VAKIO_LARNITECH_BRIDGE_ENABLED or not LARNITECH_API_KEY:
        return
    desired = desired_larnitech_vakio_states(command)
    if not desired:
        return
    with vakio_bridge_guard:
        connection: websocket.WebSocket | None = None
        try:
            connection = open_authorized_larnitech_connection()
            for addr, value in desired.items():
                with lock:
                    devices = state["larnitech"].get("devices", [])
                    entity = entity_by_addr(devices, addr) if isinstance(devices, list) else None
                    current = (entity or {}).get("status", {}).get("state")
                if current == value:
                    continue
                larnitech_status_set(connection, addr, value)
            LOG.info("VAKIO %s state synchronized to Larnitech", command)
        except (OSError, ValueError, json.JSONDecodeError, websocket.WebSocketException) as exc:
            LOG.warning("VAKIO state sync to Larnitech failed: %s", exc)
            with lock:
                state["larnitech"]["error"] = f"VAKIO sync: {exc}"
        finally:
            if connection is not None:
                connection.close()


def vakio_larnitech_command_worker(command: dict[str, str]) -> None:
    key, value = command["command"], command["value"]
    with vakio_bridge_guard:
        try:
            commands = ([{"command": "state", "value": "on"}] if key in {"workmode", "speed"} else []) + [command]
            for requested in commands:
                requested_topic = f"{VAKIO_TOPIC}/{requested['command']}"
                with lock:
                    fresh = fresh_topic_values.get(requested_topic)
                if fresh is not None and fresh[0] == requested["value"] and (
                    time.monotonic() - fresh[1] <= VAKIO_TELEMETRY_MAX_AGE
                ):
                    continue
                publish_vakio(requested)
            LOG.warning("VAKIO command from Larnitech confirmed: %s=%s", key, value)
        except (PermissionError, RuntimeError, ValueError) as exc:
            LOG.warning("VAKIO command from Larnitech failed: %s=%s: %s", key, value, exc)
            with lock:
                state["vakio"]["error"] = f"Larnitech command failed: {exc}"
    # Always restore the selectors from the last confirmed telemetry. The MQTT
    # callback also schedules this after success; the operation is idempotent.
    sync_larnitech_vakio_states(key)


def scenario_state(response: dict[str, Any], addr: str) -> str | None:
    devices = response.get("devices")
    if not isinstance(devices, list):
        return None
    device = next((item for item in devices if item.get("addr") == addr), None)
    if not isinstance(device, dict):
        return None
    status = device.get("status")
    if not isinstance(status, dict):
        return None
    value = status.get("state")
    return str(value) if value is not None else None


def scenario_status_set_succeeded(response: dict[str, Any], addr: str) -> bool:
    devices = response.get("devices")
    if not isinstance(devices, list):
        return False
    return any(
        isinstance(device, dict)
        and device.get("addr") == addr
        and device.get("success") is True
        for device in devices
    )


def scenario_inventory_entity(addr: str) -> dict[str, Any] | None:
    with lock:
        larnitech = state["larnitech"]
        if larnitech.get("status") != "online":
            return None
        inventory_age = age_seconds(larnitech.get("heartbeat_at") or larnitech.get("updated_at"))
        if inventory_age is None or inventory_age > LARNITECH_POLL_SECONDS * 3:
            return None
        devices = larnitech.get("devices", [])
        entity = entity_by_addr(devices, addr) if isinstance(devices, list) else None
        return json.loads(json.dumps(entity)) if entity else None


def trigger_larnitech_scenario(addr: str, request_id: str) -> dict[str, Any]:
    """Trigger one fixed scenario and confirm the API2 result synchronously."""
    if not LARNITECH_SCENARIO_CONTROL_ENABLED:
        raise PermissionError("Larnitech scenario control is disabled")
    if addr not in LARNITECH_SCENARIO_ALLOWLIST:
        raise PermissionError("Larnitech scenario is not allowlisted")
    if not REQUEST_ID_RE.fullmatch(request_id):
        raise ValueError("Invalid request_id")
    if not LARNITECH_API_KEY:
        raise RuntimeError("Larnitech API key is not configured")

    entity = scenario_inventory_entity(addr)
    if entity is None:
        raise RuntimeError("Larnitech inventory is unavailable")
    if entity.get("type") != "script" or entity.get("name") != SCENARIO_REGISTRY[addr]["name"]:
        raise RuntimeError("Larnitech scenario identity mismatch")

    started = time.monotonic()
    with scenario_guard:
        previous = scenario_runs.get(addr)
        if previous and previous.get("in_progress"):
            raise RuntimeError("Larnitech scenario is already running")
        if previous and previous.get("request_id") == request_id:
            raise RuntimeError("Duplicate Larnitech scenario request")
        if previous and started - float(previous.get("started_monotonic", 0)) < LARNITECH_SCENARIO_COOLDOWN_SECONDS:
            raise RuntimeError("Larnitech scenario cooldown is active")
        scenario_runs[addr] = {
            "in_progress": True,
            "request_id": request_id,
            "started_monotonic": started,
            "started_at": utc_timestamp(),
        }

    LOG.warning("Larnitech scenario requested addr=%s name=%s request_id=%s", addr, SCENARIO_REGISTRY[addr]["name"], request_id)
    connection: websocket.WebSocket | None = None
    try:
        connection = websocket.create_connection(LARNITECH_WS_URL, timeout=10)
        authorization = larnitech_exchange(
            connection, {"request": "authorize", "key": LARNITECH_API_KEY}
        )
        if authorization.get("response") != "authorize":
            raise ValueError("Larnitech authorization was not confirmed")

        accepted = larnitech_exchange(
            connection,
            {"request": "status-set", "addr": addr, "status": {"state": "on"}},
        )
        if accepted.get("response") != "status-set":
            raise ValueError("Larnitech status-set was not acknowledged")
        if not scenario_status_set_succeeded(accepted, addr):
            raise ValueError("Larnitech status-set did not report success")
        accepted_state = scenario_state(accepted, addr)

        observed = larnitech_exchange(
            connection, {"request": "status-get", "addr": addr, "status": "detailed"}
        )
        if observed.get("response") != "status-get":
            raise ValueError("Larnitech status-get confirmation failed")
        observed_state = scenario_state(observed, addr)
        if observed_state not in {"on", "off"} and accepted_state not in {"on", "off"}:
            raise ValueError("Larnitech scenario state was not confirmed")

        result = {
            "accepted": True,
            "confirmed": True,
            "addr": addr,
            "name": SCENARIO_REGISTRY[addr]["name"],
            "request_id": request_id,
            "accepted_state": accepted_state,
            "observed_state": observed_state,
            "confirmed_at": utc_timestamp(),
            "physical_result_verified": False,
        }
        LOG.warning(
            "Larnitech scenario confirmed addr=%s name=%s request_id=%s observed_state=%s",
            addr, SCENARIO_REGISTRY[addr]["name"], request_id, observed_state,
        )
        return result
    except Exception:
        LOG.exception("Larnitech scenario failed addr=%s request_id=%s", addr, request_id)
        raise
    finally:
        if connection is not None:
            connection.close()
        with scenario_guard:
            current = scenario_runs.get(addr, {})
            if current.get("request_id") == request_id:
                current["in_progress"] = False
                current["completed_at"] = utc_timestamp()


def larnitech_worker() -> None:
    if not LARNITECH_API_KEY:
        return
    while True:
        connection: websocket.WebSocket | None = None
        try:
            connection, devices = open_larnitech_connection()
            now = utc_timestamp()
            with lock:
                state["larnitech"].update(
                    status="online", updated_at=now, heartbeat_at=now,
                    subscribed_addrs=list(LARNITECH_SUBSCRIBE_ADDRS), devices=devices, error=None,
                )
            LOG.info("Larnitech API2 subscribed to %s", ",".join(LARNITECH_SUBSCRIBE_ADDRS))

            keepalive_pending = False
            while True:
                try:
                    response = larnitech_response(connection)
                except websocket.WebSocketTimeoutException:
                    if keepalive_pending:
                        raise TimeoutError("Larnitech keepalive timed out")
                    if not LARNITECH_SUBSCRIBE_ADDRS:
                        connection.ping()
                        with lock:
                            state["larnitech"]["heartbeat_at"] = utc_timestamp()
                        continue
                    connection.send(json.dumps({
                        "request": "status-get", "addr": LARNITECH_SUBSCRIBE_ADDRS[0],
                        "status": "detailed",
                    }))
                    keepalive_pending = True
                    continue

                response_type = response.get("response")
                event_type = response.get("event")
                updates = response.get("devices", [])
                now = utc_timestamp()
                with lock:
                    larnitech = state["larnitech"]
                    larnitech.update(status="online", heartbeat_at=now, error=None)
                    changed = merge_larnitech_devices(larnitech["devices"], updates) if isinstance(updates, list) else []
                    if event_type == "statuses" and changed:
                        larnitech.update(updated_at=now, last_event_at=now)
                detailed_refreshes = (
                    LARNITECH_DETAILED_REFRESH_ADDRS.intersection(changed)
                    if event_type == "statuses"
                    else set()
                )
                for addr in sorted(detailed_refreshes):
                    connection.send(json.dumps({
                        "request": "status-get", "addr": addr, "status": "detailed",
                    }))
                if response_type == "status-get":
                    keepalive_pending = False
                elif event_type == "statuses" and changed:
                    LOG.info("Larnitech event received for %s", ",".join(changed))
                    if VAKIO_LARNITECH_BRIDGE_ENABLED and isinstance(updates, list):
                        for update in updates:
                            command = vakio_command_from_larnitech_update(update, devices)
                            if command is not None:
                                threading.Thread(
                                    target=vakio_larnitech_command_worker,
                                    args=(command,), daemon=True,
                                ).start()
        except (OSError, TimeoutError, ValueError, json.JSONDecodeError, websocket.WebSocketException) as exc:
            LOG.warning("Larnitech API2 connection failed: %s", exc)
            with lock:
                reconnects = int(state["larnitech"].get("reconnects", 0)) + 1
                state["larnitech"].update(status="error", error=str(exc), reconnects=reconnects)
        finally:
            if connection is not None:
                connection.close()
        time.sleep(min(LARNITECH_POLL_SECONDS, 10))


def on_connect(client: mqtt.Client, userdata: object, flags: dict[str, Any], reason_code: Any, properties: Any = None) -> None:
    del userdata, flags, properties
    # Paho v2 ReasonCode compares to an integer but cannot be cast with int().
    if reason_code != 0:
        with lock:
            state["mqtt"].update(status="error", updated_at=utc_timestamp(), error=f"MQTT connect: {reason_code}")
        return
    client.subscribe(
        f"{VAKIO_TOPIC}/#",
        options=mqtt.SubscribeOptions(qos=1, noLocal=True),
    )
    with lock:
        state["mqtt"].update(status="online", updated_at=utc_timestamp(), error=None)
        state["vakio"].update(status="waiting", error=None)


def on_disconnect(client: mqtt.Client, userdata: object, disconnect_flags: Any, reason_code: Any, properties: Any = None) -> None:
    del client, userdata, disconnect_flags, properties
    with lock:
        state["mqtt"].update(status="offline", updated_at=utc_timestamp(), error=f"MQTT disconnected: {reason_code}")


def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
    del client, userdata
    global last_device_message_monotonic
    value = message.payload.decode("utf-8", errors="replace")
    retained = bool(getattr(message, "retain", False))
    with confirmation:
        if not retained:
            last_device_message_monotonic = time.monotonic()
            fresh_topic_versions[message.topic] = fresh_topic_versions.get(message.topic, 0) + 1
            fresh_topic_values[message.topic] = (value, last_device_message_monotonic)
            state["vakio"]["confirmed_topics"][message.topic] = {
                "value": value, "updated_at": utc_timestamp(), "source": "device",
            }
            state["vakio"]["commanded_topics"].pop(message.topic, None)
        state["vakio"]["topics"][message.topic] = value
        state["vakio"].update(updated_at=utc_timestamp())
        if not retained:
            state["vakio"].update(status="online", error=None)
        if not retained and pending_confirmation == (message.topic, value):
            confirmation.notify_all()
        else:
            # Wake a presence refresh waiting for any message emitted by the
            # device. noLocal prevents our own publish from satisfying it.
            confirmation.notify_all()
    prefix = f"{VAKIO_TOPIC}/"
    command = message.topic[len(prefix):] if message.topic.startswith(prefix) else ""
    allowed_values = {
        "state": {"on", "off"},
        "workmode": set(VAKIO_MODES),
        "speed": set(VAKIO_SPEEDS),
    }
    # Retained values are only the broker's last snapshot. They must not drive
    # Larnitech selectors because they do not prove the fan's current state.
    if (
        VAKIO_LARNITECH_BRIDGE_ENABLED
        and not retained
        and value in allowed_values.get(command, set())
    ):
        threading.Thread(
            target=sync_larnitech_vakio_states, args=(command,), daemon=True,
        ).start()


def start_mqtt() -> mqtt.Client:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="smarthome-gateway",
        protocol=mqtt.MQTTv5,
    )
    if MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    # The broker is a required local systemd dependency, so a synchronous
    # initial connect is deterministic and lets systemd retry on failure.
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    return client


def ensure_vakio_fresh_telemetry() -> None:
    """Request a harmless re-registration before accepting a stale command."""
    global last_device_message_monotonic
    if last_device_message_monotonic is not None and (
        time.monotonic() - last_device_message_monotonic <= VAKIO_TELEMETRY_MAX_AGE
    ):
        return
    if mqtt_client is None:
        raise RuntimeError("MQTT is not available")
    deadline = time.monotonic() + VAKIO_CONFIRM_TIMEOUT
    with confirmation:
        previous = last_device_message_monotonic
        result = mqtt_client.publish(f"{VAKIO_TOPIC}/system", "0687", qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT presence request failed: {result.rc}")
        while last_device_message_monotonic is None or last_device_message_monotonic == previous:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("VAKIO telemetry is not fresh")
            confirmation.wait(remaining)


def vakio_presence_worker() -> None:
    """Keep device presence current without changing power, mode, or speed."""
    while True:
        try:
            ensure_vakio_fresh_telemetry()
        except RuntimeError as exc:
            LOG.warning("VAKIO presence refresh failed: %s", exc)
            with lock:
                state["vakio"].update(status="waiting", error=str(exc))
        time.sleep(VAKIO_PRESENCE_POLL_SECONDS)


def publish_vakio(command: dict[str, Any]) -> tuple[str, str]:
    global pending_confirmation
    if not CONTROL_ENABLED:
        raise PermissionError("VAKIO control is disabled")
    if mqtt_client is None:
        raise RuntimeError("MQTT is not available")
    allowed: dict[str, set[str]] = {
        "state": {"on", "off"},
        "workmode": set(VAKIO_MODES),
        "speed": set(VAKIO_SPEEDS),
    }
    key = str(command.get("command", ""))
    value = str(command.get("value", ""))
    if key not in allowed or value not in allowed[key]:
        raise ValueError("Unsupported VAKIO command")
    ensure_vakio_fresh_telemetry()
    topic = f"{VAKIO_TOPIC}/{key}"
    raw_topic = f"{VAKIO_TOPIC}/mode"
    raw_value = VAKIO_RAW_COMMANDS[(key, value)]
    deadline = time.monotonic() + VAKIO_CONFIRM_TIMEOUT
    with confirmation:
        previous_version = fresh_topic_versions.get(topic, 0)
        pending_confirmation = (topic, value)
        result = mqtt_client.publish(raw_topic, raw_value, qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            pending_confirmation = None
            raise RuntimeError(f"MQTT publish failed: {result.rc}")
        while not (
            fresh_topic_versions.get(topic, 0) > previous_version
            and fresh_topic_values.get(topic, (None, 0))[0] == value
        ):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                pending_confirmation = None
                if key == "state" and value == "off":
                    # This Base Smart revision executes 06000 but does not
                    # publish state=off afterwards. Persist the commanded safe
                    # state only after the raw QoS1 publish was accepted.
                    retained_result = mqtt_client.publish(topic, value, qos=1, retain=True)
                    if retained_result.rc != mqtt.MQTT_ERR_SUCCESS:
                        raise RuntimeError(f"MQTT off-state persistence failed: {retained_result.rc}")
                    state["vakio"]["topics"][topic] = value
                    state["vakio"]["confirmed_topics"].pop(topic, None)
                    state["vakio"]["commanded_topics"][topic] = {
                        "value": value, "updated_at": utc_timestamp(),
                        "source": "accepted_without_device_confirmation",
                    }
                    state["vakio"].update(updated_at=utc_timestamp(), error=None)
                    break
                raise RuntimeError("VAKIO did not confirm the command")
            confirmation.wait(remaining)
        pending_confirmation = None
    return topic, value


def snapshot() -> dict[str, Any]:
    with lock:
        result = json.loads(json.dumps(state))
    result.update(
        status="online" if result["larnitech"]["status"] == "online" and result["mqtt"]["status"] == "online" else "degraded",
        # Public HTTP control is disabled while Larnitech owns the VAKIO
        # control plane. The bridge still uses publish_vakio internally.
        control_enabled=CONTROL_ENABLED and not VAKIO_LARNITECH_BRIDGE_ENABLED,
        larnitech_url=LARNITECH_URL,
        vakio_topic=VAKIO_TOPIC,
        scenario_control={
            "enabled": LARNITECH_SCENARIO_CONTROL_ENABLED,
            "cooldown_seconds": LARNITECH_SCENARIO_COOLDOWN_SECONDS,
            "scenarios": [
                {
                    "addr": addr,
                    **details,
                    "allowed": addr in LARNITECH_SCENARIO_ALLOWLIST,
                }
                for addr, details in SCENARIO_REGISTRY.items()
            ],
        },
        vakio_larnitech_bridge={
            "enabled": VAKIO_LARNITECH_BRIDGE_ENABLED,
            "power_addr": VAKIO_LARNITECH_POWER_ADDR or None,
            "mode_addrs": VAKIO_LARNITECH_MODE_ADDRS,
            "speed_addrs": VAKIO_LARNITECH_SPEED_ADDRS,
        },
        vakio_larnitech_state=larnitech_vakio_state(
            result.get("larnitech", {}).get("devices", [])
        ),
    )
    if not LARNITECH_API_KEY:
        result["larnitech"]["status"] = "api_key_required"
    elif result["larnitech"]["status"] == "not_configured":
        result["larnitech"]["status"] = "waiting"
    result["observed"] = observed_map(result)
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = "smarthome-gateway/1"

    def json_response(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/healthz", "/map"}:
            self.send_error(404)
            return
        self.json_response(200, snapshot())

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/vakio/command", "/larnitech/scenario"}:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1024:
                raise ValueError("Invalid request size")
            command = json.loads(self.rfile.read(length))
            if not isinstance(command, dict):
                raise ValueError("Request body must be an object")
            if self.path == "/vakio/command":
                if VAKIO_LARNITECH_BRIDGE_ENABLED:
                    raise PermissionError("Direct VAKIO control is disabled; use Larnitech")
                topic, value = publish_vakio(command)
                self.json_response(200, {"accepted": True, "confirmed": True, "topic": topic, "value": value})
                return
            if set(command) != {"addr", "request_id"}:
                raise ValueError("Only addr and request_id are accepted")
            result = trigger_larnitech_scenario(str(command["addr"]), str(command["request_id"]))
            self.json_response(200, result)
        except PermissionError as exc:
            self.json_response(403, {"error": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            self.json_response(400, {"error": str(exc)})
        except RuntimeError as exc:
            self.json_response(503, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        LOG.info("HTTP %s - %s", self.address_string(), format % args)


if __name__ == "__main__":
    if LARNITECH_API_KEY:
        threading.Thread(target=larnitech_worker, daemon=True).start()
    mqtt_client = start_mqtt()
    threading.Thread(target=vakio_presence_worker, daemon=True).start()
    ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), Handler).serve_forever()
