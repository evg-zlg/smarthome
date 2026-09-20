#!/usr/bin/env python3
"""Local Larnitech inventory and VAKIO Base Smart gateway."""
from __future__ import annotations

import json
import logging
import os
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
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "gateway")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
VAKIO_TOPIC = os.environ.get("VAKIO_TOPIC", "vakio").strip("/")
CONTROL_ENABLED = os.environ.get("CONTROL_ENABLED", "false").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("smarthome-gateway")
lock = threading.Lock()
state: dict[str, Any] = {
    "started_at": time.time(),
    "mqtt": {"status": "waiting", "updated_at": None, "error": None},
    "larnitech": {"status": "not_configured", "updated_at": None, "devices": [], "error": None},
    "vakio": {"status": "waiting", "updated_at": None, "topics": {}, "error": None},
}
mqtt_client: mqtt.Client | None = None


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
    larnitech_age = age_seconds(larnitech.get("updated_at"))
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


def larnitech_request() -> dict[str, Any]:
    connection = websocket.create_connection(LARNITECH_WS_URL, timeout=30)
    try:
        connection.send(json.dumps({"request": "authorize", "key": LARNITECH_API_KEY}))
        authorization = json.loads(connection.recv())
        if authorization.get("response") != "authorize" or authorization.get("error"):
            raise ValueError(f"Larnitech authorization failed: {authorization}")
        connection.send(json.dumps({"request": "get-devices", "status": "detailed"}))
        return json.loads(connection.recv(), strict=False)
    finally:
        connection.close()


def larnitech_worker() -> None:
    if not LARNITECH_API_KEY:
        return
    while True:
        try:
            response = larnitech_request()
            devices = response.get("devices", [])
            if not isinstance(devices, list):
                raise ValueError("Larnitech response has no devices list")
            with lock:
                state["larnitech"].update(status="online", updated_at=utc_timestamp(), devices=devices, error=None)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            LOG.warning("Larnitech inventory failed: %s", exc)
            with lock:
                state["larnitech"].update(status="error", error=str(exc))
        time.sleep(LARNITECH_POLL_SECONDS)


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
        if self.path != "/vakio/command":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1024:
                raise ValueError("Invalid request size")
            command = json.loads(self.rfile.read(length))
            topic, value = publish_vakio(command)
            self.json_response(202, {"accepted": True, "topic": topic, "value": value})
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
