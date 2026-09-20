#!/usr/bin/env python3
"""Local Larnitech inventory and VAKIO Base Smart gateway."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
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
VAKIO_TELEMETRY_MAX_AGE = max(15, int(os.environ.get("VAKIO_TELEMETRY_MAX_AGE", "90")))
VAKIO_CONFIRM_TIMEOUT = max(1, int(os.environ.get("VAKIO_CONFIRM_TIMEOUT", "8")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("smarthome-gateway")
lock = threading.Lock()
confirmation = threading.Condition(lock)
state: dict[str, Any] = {
    "started_at": time.time(),
    "larnitech": {"status": "not_configured", "updated_at": None, "devices": [], "error": None},
    "vakio": {"status": "waiting", "updated_at": None, "topics": {}, "error": None},
}
mqtt_client: mqtt.Client | None = None
last_device_message_monotonic: float | None = None
pending_confirmation: tuple[str, str] | None = None


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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
    if getattr(reason_code, "is_failure", False):
        with lock:
            state["vakio"].update(status="error", error=f"MQTT connect: {reason_code}")
        return
    client.subscribe(
        f"{VAKIO_TOPIC}/#",
        options=mqtt.SubscribeOptions(qos=1, noLocal=True),
    )
    with lock:
        state["vakio"].update(status="connected", error=None)


def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
    del client, userdata
    global last_device_message_monotonic
    value = message.payload.decode("utf-8", errors="replace")
    with confirmation:
        last_device_message_monotonic = time.monotonic()
        state["vakio"]["topics"][message.topic] = value
        state["vakio"].update(status="online", updated_at=utc_timestamp(), error=None)
        if pending_confirmation == (message.topic, value):
            confirmation.notify_all()


def start_mqtt() -> mqtt.Client:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="smarthome-gateway",
        protocol=mqtt.MQTTv5,
    )
    if MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    # The broker is a required local systemd dependency, so a synchronous
    # initial connect is deterministic and lets systemd retry on failure.
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    return client


def publish_vakio(command: dict[str, Any]) -> tuple[str, str]:
    global pending_confirmation
    if not CONTROL_ENABLED:
        raise PermissionError("VAKIO control is disabled")
    if mqtt_client is None:
        raise RuntimeError("MQTT is not available")
    allowed: dict[str, set[str]] = {
        "state": {"off", "on"},
        "workmode": {
            "recuperator",
            "winter",
            "inflow",
            "inflow_max",
            "outflow",
            "outflow_max",
            "night",
        },
        "speed": {str(value) for value in range(1, 8)},
    }
    key = str(command.get("command", ""))
    value = str(command.get("value", ""))
    if key not in allowed or value not in allowed[key]:
        raise ValueError("Unsupported VAKIO command")
    if last_device_message_monotonic is None or (
        time.monotonic() - last_device_message_monotonic > VAKIO_TELEMETRY_MAX_AGE
    ):
        raise RuntimeError("VAKIO telemetry is not fresh")

    topic = f"{VAKIO_TOPIC}/{key}"
    payload = value
    deadline = time.monotonic() + VAKIO_CONFIRM_TIMEOUT
    with confirmation:
        pending_confirmation = (topic, payload)
        result = mqtt_client.publish(topic, payload, qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            pending_confirmation = None
            raise RuntimeError(f"MQTT publish failed: {result.rc}")
        while pending_confirmation is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                pending_confirmation = None
                raise RuntimeError("VAKIO did not confirm the command")
            confirmation.wait(remaining)
            if state["vakio"]["topics"].get(topic) == payload:
                pending_confirmation = None
    return topic, payload


def snapshot() -> dict[str, Any]:
    with lock:
        result = json.loads(json.dumps(state))
    result.update(
        status="online" if result["vakio"]["status"] in {"connected", "online"} else "degraded",
        control_enabled=CONTROL_ENABLED,
        larnitech_url=LARNITECH_URL,
        vakio_topic=VAKIO_TOPIC,
    )
    if not LARNITECH_API_KEY:
        result["larnitech"]["status"] = "api_key_required"
    elif result["larnitech"]["status"] == "not_configured":
        result["larnitech"]["status"] = "waiting"
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
            self.json_response(200, {"confirmed": True, "topic": topic, "value": value})
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
