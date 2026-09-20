import importlib.util
import os
import sys
import threading
import time
import unittest
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace

# Unit tests exercise the pure observation model and command validation. Keep
# them runnable on a development machine without the Raspberry Pi adapters.
try:
    import paho.mqtt.client  # noqa: F401
except ModuleNotFoundError:
    paho = ModuleType("paho")
    paho_mqtt = ModuleType("paho.mqtt")
    paho_client = ModuleType("paho.mqtt.client")
    paho_client.MQTT_ERR_SUCCESS = 0
    paho_client.MQTTv5 = 5
    paho_client.CallbackAPIVersion = SimpleNamespace(VERSION2=2)
    paho_client.SubscribeOptions = lambda qos, noLocal: SimpleNamespace(qos=qos, noLocal=noLocal)
    paho_client.Client = object
    paho_mqtt.client = paho_client
    paho.mqtt = paho_mqtt
    sys.modules.update({"paho": paho, "paho.mqtt": paho_mqtt, "paho.mqtt.client": paho_client})

try:
    import websocket  # noqa: F401
except ModuleNotFoundError:
    sys.modules["websocket"] = ModuleType("websocket")

os.environ["CONTROL_ENABLED"] = "true"
os.environ["LARNITECH_SCENARIO_CONTROL_ENABLED"] = "true"
os.environ["LARNITECH_SCENARIO_ALLOWLIST"] = "315:250"
spec = importlib.util.spec_from_file_location("gateway_app", Path(__file__).with_name("app.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class FakeResult:
    rc = app.mqtt.MQTT_ERR_SUCCESS


class FakeClient:
    def publish(self, topic, value, qos):
        self.message = (topic, value, qos)
        message = type("Message", (), {"topic": topic, "payload": value.encode()})()
        threading.Timer(0.01, app.on_message, args=(self, None, message)).start()
        return FakeResult()


class FakeWebSocket:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.sent = []
        self.closed = False

    def send(self, payload):
        self.sent.append(json.loads(payload))

    def recv(self):
        return json.dumps(next(self.responses))

    def close(self):
        self.closed = True


class GatewayTests(unittest.TestCase):
    def setUp(self):
        app.mqtt_client = FakeClient()
        app.last_device_message_monotonic = time.monotonic()
        app.pending_confirmation = None
        app.scenario_runs.clear()

    def test_allowed_vakio_command(self):
        self.assertEqual(app.publish_vakio({"command": "speed", "value": 4}), ("vakio/speed", "4"))

    def test_rejects_unknown_command(self):
        with self.assertRaises(ValueError):
            app.publish_vakio({"command": "reset", "value": "1"})

    def test_snapshot_requires_larnitech_key(self):
        self.assertEqual(app.snapshot()["larnitech"]["status"], "api_key_required")

    def test_mqtt_v2_reason_code_marks_broker_online(self):
        class SuccessReasonCode:
            def __eq__(self, other):
                return other == 0

        client = SimpleNamespace(subscribe=lambda topic, options=None: None)
        app.on_connect(client, None, {}, SuccessReasonCode())
        self.assertEqual(app.state["mqtt"]["status"], "online")

    def test_observed_map_separates_physical_modules_and_api_channels(self):
        inventory = json.loads(
            (Path(__file__).parents[1] / "docs/inventory/larnitech-entities.json").read_text()
        )
        source = {
            "larnitech": {"status": "online", "updated_at": app.utc_timestamp(), "devices": inventory["entities"], "error": None},
            "mqtt": {"status": "online", "updated_at": app.utc_timestamp(), "error": None},
            "vakio": {"status": "waiting", "updated_at": None, "topics": {}, "error": None},
        }
        observed = app.observed_map(source)
        self.assertEqual(len(observed["physical_modules"]), 4)
        self.assertEqual(observed["api_channels"]["total"], 83)
        self.assertEqual(observed["climate"][0]["value"], 742)
        self.assertTrue(observed["air_conditioner"]["connected"])
        self.assertEqual(observed["air_conditioner"]["status"]["target"], 22.0)

    def test_stale_larnitech_data_is_reported(self):
        source = {
            "larnitech": {"status": "online", "updated_at": "2020-01-01T00:00:00Z", "devices": [], "error": None},
            "mqtt": {"status": "online", "updated_at": app.utc_timestamp(), "error": None},
            "vakio": {"status": "waiting", "updated_at": None, "topics": {}, "error": None},
        }
        errors = app.observed_map(source)["errors"]
        self.assertIn("Данные Larnitech устарели", [error["message"] for error in errors])

    def test_scenario_registry_contains_only_discovered_addresses(self):
        self.assertEqual(
            set(app.SCENARIO_REGISTRY),
            {"315:246", "315:250", "407:246", "407:247", "407:248", "456:46", "456:47"},
        )

    def test_scenario_rejects_address_outside_runtime_allowlist(self):
        with self.assertRaises(PermissionError):
            app.trigger_larnitech_scenario("407:248", "request-12345678")

    def test_scenario_sends_fixed_status_set_and_confirms_state(self):
        original_key = app.LARNITECH_API_KEY
        original_connect = getattr(app.websocket, "create_connection", None)
        fake = FakeWebSocket([
            {"response": "authorize"},
            {"response": "status-set", "devices": [{"addr": "315:250", "success": True}]},
            {"response": "status-get", "devices": [{"addr": "315:250", "status": {"state": "off"}}]},
        ])
        try:
            app.LARNITECH_API_KEY = "test-key"
            app.websocket.create_connection = lambda url, timeout: fake
            with app.lock:
                app.state["larnitech"].update(
                    status="online",
                    updated_at=app.utc_timestamp(),
                    devices=[{"addr": "315:250", "type": "script", "name": "Доброе утро", "status": {"state": "off"}}],
                )
            result = app.trigger_larnitech_scenario("315:250", "request-12345678")
        finally:
            app.LARNITECH_API_KEY = original_key
            if original_connect is None:
                delattr(app.websocket, "create_connection")
            else:
                app.websocket.create_connection = original_connect

        self.assertTrue(result["confirmed"])
        self.assertFalse(result["physical_result_verified"])
        self.assertEqual(result["observed_state"], "off")
        self.assertEqual(
            fake.sent[1],
            {"request": "status-set", "addr": "315:250", "status": {"state": "on"}},
        )
        self.assertNotIn("status", {"addr": result["addr"], "request_id": result["request_id"]})

    def test_scenario_duplicate_request_is_rejected_before_api2(self):
        original_key = app.LARNITECH_API_KEY
        try:
            app.LARNITECH_API_KEY = "test-key"
            with app.lock:
                app.state["larnitech"].update(
                    status="online",
                    updated_at=app.utc_timestamp(),
                    devices=[{"addr": "315:250", "type": "script", "name": "Доброе утро"}],
                )
            app.scenario_runs["315:250"] = {
                "request_id": "request-12345678",
                "in_progress": False,
                "started_monotonic": app.time.monotonic() - 60,
            }
            with self.assertRaises(RuntimeError):
                app.trigger_larnitech_scenario("315:250", "request-12345678")
        finally:
            app.LARNITECH_API_KEY = original_key

    def test_decodes_co2_subscription_event(self):
        self.assertEqual(app.decode_larnitech_event_state("co2-sensor", "0xFB02"), 763)

    def test_merges_subscription_event_into_inventory(self):
        devices = [{"addr": "315:36", "type": "co2-sensor", "status": {"state": 700}}]
        changed = app.merge_larnitech_devices(devices, [{"addr": "315:36", "status": "0xFB02"}])
        self.assertEqual(changed, ["315:36"])
        self.assertEqual(devices[0]["status"], {"state": 763, "raw": "0xFB02"})

    def test_unknown_event_status_stays_raw(self):
        self.assertEqual(app.decode_larnitech_event_state("lamp", "0x01"), "0x01")

    def test_real_status_event_shape_updates_co2(self):
        devices = [{"addr": "315:36", "type": "co2-sensor", "status": {"state": 687}}]
        event = {"event": "statuses", "devices": [{"addr": "315:36", "status": "0x0B03"}]}
        changed = app.merge_larnitech_devices(devices, event["devices"])
        self.assertEqual(changed, ["315:36"])
        self.assertEqual(devices[0]["status"]["state"], 779)


if __name__ == "__main__":
    unittest.main()
