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
LARNITECH_SUBSCRIBE_ADDRS = tuple(
    addr.strip()
    for addr in os.environ.get("LARNITECH_SUBSCRIBE_ADDRS", "315:36").split(",")
    if addr.strip()
)
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "gateway")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
VAKIO_TOPIC = os.environ.get("VAKIO_TOPIC", "vakio").strip("/")
CONTROL_ENABLED = os.environ.get("CONTROL_ENABLED", "false").lower() == "true"
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
state: dict[str, Any] = {
    "started_at": time.time(),
    "mqtt": {"status": "waiting", "updated_at": None, "error": None},
    "larnitech": {
        "status": "not_configured", "updated_at": None, "heartbeat_at": None,
        "last_event_at": None, "subscribed_addrs": [], "reconnects": 0,
        "devices": [], "error": None,
    },
    "vakio": {"status": "waiting", "updated_at": None, "topics": {}, "error": None},
}
mqtt_client: mqtt.Client | None = None
scenario_guard = threading.Lock()
scenario_runs: dict[str, dict[str, Any]] = {}


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
    return raw_status


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
                if response_type == "status-get":
                    keepalive_pending = False
                elif event_type == "statuses" and changed:
                    LOG.info("Larnitech event received for %s", ",".join(changed))
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
    client.subscribe(f"{VAKIO_TOPIC}/#")
    with lock:
        state["mqtt"].update(status="online", updated_at=utc_timestamp(), error=None)
        state["vakio"].update(status="waiting", error=None)


def on_disconnect(client: mqtt.Client, userdata: object, disconnect_flags: Any, reason_code: Any, properties: Any = None) -> None:
    del client, userdata, disconnect_flags, properties
    with lock:
        state["mqtt"].update(status="offline", updated_at=utc_timestamp(), error=f"MQTT disconnected: {reason_code}")


def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
    del client, userdata
    value = message.payload.decode("utf-8", errors="replace")
    with lock:
        state["vakio"]["topics"][message.topic] = value
        state["vakio"].update(status="online", updated_at=utc_timestamp(), error=None)


def start_mqtt() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="smarthome-gateway")
    if MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    return client


def publish_vakio(command: dict[str, Any]) -> tuple[str, str]:
    if not CONTROL_ENABLED:
        raise PermissionError("VAKIO control is disabled")
    if mqtt_client is None:
        raise RuntimeError("MQTT is not available")
    allowed: dict[str, set[str]] = {
        "state": {"on", "off"},
        "workmode": {"inflow", "inflow_max", "recuperator", "winter", "outflow", "outflow_max"},
        "speed": {str(value) for value in range(1, 8)},
    }
    key = str(command.get("command", ""))
    value = str(command.get("value", ""))
    if key not in allowed or value not in allowed[key]:
        raise ValueError("Unsupported VAKIO command")
    topic = f"{VAKIO_TOPIC}/{key}"
    result = mqtt_client.publish(topic, value, qos=1)
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError(f"MQTT publish failed: {result.rc}")
    return topic, value


def snapshot() -> dict[str, Any]:
    with lock:
        result = json.loads(json.dumps(state))
    result.update(
        status="online" if result["larnitech"]["status"] == "online" and result["mqtt"]["status"] == "online" else "degraded",
        control_enabled=CONTROL_ENABLED,
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
                topic, value = publish_vakio(command)
                self.json_response(202, {"accepted": True, "topic": topic, "value": value})
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
    ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), Handler).serve_forever()
