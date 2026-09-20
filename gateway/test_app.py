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
os.environ["VAKIO_LARNITECH_POWER_ADDR"] = "407:220"
os.environ["VAKIO_LARNITECH_MODE_ADDRS"] = ",".join(
    f"{mode}=407:{221 + index}"
    for index, mode in enumerate((
        "inflow", "inflow_max", "recuperator", "winter",
        "outflow", "outflow_max", "night",
    ))
)
os.environ["VAKIO_LARNITECH_SPEED_ADDRS"] = ",".join(
    f"{speed}=407:{227 + speed}" for speed in range(1, 8)
)
spec = importlib.util.spec_from_file_location("gateway_app", Path(__file__).with_name("app.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class FakeResult:
    rc = app.mqtt.MQTT_ERR_SUCCESS


class FakeClient:
    def publish(self, topic, value, qos, retain=False):
        self.message = (topic, value, qos, retain)
        semantic = {
            "06000": ("state", "off"), "06001": ("state", "on"),
            "06010": ("workmode", "recuperator"), "06011": ("workmode", "winter"),
            "06021": ("workmode", "inflow"), "06022": ("workmode", "inflow_max"),
            "06031": ("workmode", "outflow"), "06032": ("workmode", "outflow_max"),
            "06041": ("workmode", "night"),
            **{f"0650{speed}": ("speed", str(speed)) for speed in range(1, 8)},
        }.get(value)
        if semantic:
            key, confirmed = semantic
            message = SimpleNamespace(
                topic=f"{app.VAKIO_TOPIC}/{key}", payload=confirmed.encode(),
            )
        else:
            message = SimpleNamespace(topic=topic, payload=value.encode())
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
        app.fresh_topic_versions.clear()
        app.fresh_topic_values.clear()
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

        subscription = {}

        def subscribe(topic, options=None):
            subscription.update(topic=topic, options=options)

        client = SimpleNamespace(subscribe=subscribe)
        app.on_connect(client, None, {}, SuccessReasonCode())
        self.assertEqual(app.state["mqtt"]["status"], "online")
        self.assertEqual(subscription["topic"], "vakio/#")
        self.assertTrue(subscription["options"].noLocal)

    def test_rejects_command_without_fresh_telemetry(self):
        class SilentClient:
            def publish(self, topic, value, qos):
                return FakeResult()

        original_client = app.mqtt_client
        original_timeout = app.VAKIO_CONFIRM_TIMEOUT
        try:
            app.mqtt_client = SilentClient()
            app.VAKIO_CONFIRM_TIMEOUT = 0.01
            app.last_device_message_monotonic = None
            with self.assertRaisesRegex(RuntimeError, "telemetry is not fresh"):
                app.publish_vakio({"command": "state", "value": "on"})
        finally:
            app.mqtt_client = original_client
            app.VAKIO_CONFIRM_TIMEOUT = original_timeout

    def test_stale_command_requests_presence_before_control(self):
        app.last_device_message_monotonic = None
        self.assertEqual(
            app.publish_vakio({"command": "state", "value": "on"}),
            ("vakio/state", "on"),
        )
        self.assertEqual(app.mqtt_client.message, ("vakio/mode", "06001", 1, False))

    def test_every_operating_command_has_a_raw_device_command(self):
        expected = {
            *(('state', value) for value in ('on', 'off')),
            *(('workmode', value) for value in app.VAKIO_MODES),
            *(('speed', value) for value in app.VAKIO_SPEEDS),
        }
        self.assertEqual(set(app.VAKIO_RAW_COMMANDS), expected)

    def test_retained_message_does_not_make_telemetry_fresh(self):
        app.last_device_message_monotonic = None
        original_bridge = app.VAKIO_LARNITECH_BRIDGE_ENABLED
        original_sync = app.sync_larnitech_vakio_states
        synced = []
        try:
            app.VAKIO_LARNITECH_BRIDGE_ENABLED = True
            app.sync_larnitech_vakio_states = synced.append
            message = SimpleNamespace(topic="vakio/state", payload=b"on", retain=True)
            app.on_message(app.mqtt_client, None, message)
        finally:
            app.VAKIO_LARNITECH_BRIDGE_ENABLED = original_bridge
            app.sync_larnitech_vakio_states = original_sync
        self.assertIsNone(app.last_device_message_monotonic)
        self.assertEqual(synced, [])
        self.assertNotIn("vakio/state", app.fresh_topic_values)

    def test_retained_value_cannot_confirm_a_new_command(self):
        class PresenceOnlyClient:
            def publish(self, topic, value, qos, retain=False):
                if value == "0687":
                    message = SimpleNamespace(topic="vakio/system", payload=b"0685", retain=False)
                    threading.Timer(0.001, app.on_message, args=(self, None, message)).start()
                return FakeResult()

        original_client = app.mqtt_client
        original_timeout = app.VAKIO_CONFIRM_TIMEOUT
        try:
            app.mqtt_client = PresenceOnlyClient()
            app.VAKIO_CONFIRM_TIMEOUT = 0.02
            app.last_device_message_monotonic = None
            app.on_message(
                app.mqtt_client, None,
                SimpleNamespace(topic="vakio/state", payload=b"on", retain=True),
            )
            with self.assertRaisesRegex(RuntimeError, "did not confirm"):
                app.publish_vakio({"command": "state", "value": "on"})
        finally:
            app.mqtt_client = original_client
            app.VAKIO_CONFIRM_TIMEOUT = original_timeout

    def test_mode_from_larnitech_ensures_power_before_mode(self):
        published = []
        original_publish = app.publish_vakio
        original_sync = app.sync_larnitech_vakio_states
        try:
            app.publish_vakio = lambda command: published.append(command.copy()) or ("topic", "value")
            app.sync_larnitech_vakio_states = lambda command: None
            app.vakio_larnitech_command_worker({"command": "workmode", "value": "night"})
        finally:
            app.publish_vakio = original_publish
            app.sync_larnitech_vakio_states = original_sync
        self.assertEqual(published, [
            {"command": "state", "value": "on"},
            {"command": "workmode", "value": "night"},
        ])

    def test_larnitech_bridge_disables_public_vakio_control(self):
        original_bridge = app.VAKIO_LARNITECH_BRIDGE_ENABLED
        original_control = app.CONTROL_ENABLED
        try:
            app.VAKIO_LARNITECH_BRIDGE_ENABLED = True
            app.CONTROL_ENABLED = True
            self.assertFalse(app.snapshot()["control_enabled"])
            self.assertTrue(app.snapshot()["vakio_larnitech_bridge"]["enabled"])
        finally:
            app.VAKIO_LARNITECH_BRIDGE_ENABLED = original_bridge
            app.CONTROL_ENABLED = original_control

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

    def test_lamp_event_status_is_decoded(self):
        self.assertEqual(app.decode_larnitech_event_state("lamp", "0x01"), "on")
        self.assertEqual(app.decode_larnitech_event_state("lamp", "0x00"), "off")

    def test_larnitech_power_button_maps_both_states(self):
        devices = [{"addr": "407:220", "type": "lamp"}]
        for state, raw in (("on", "0x01"), ("off", "0x00")):
            command = app.vakio_command_from_larnitech_update(
                {"addr": "407:220", "status": raw}, devices,
            )
            self.assertEqual(command, {"command": "state", "value": state})

    def test_all_larnitech_mode_buttons_map_to_supported_commands(self):
        devices = [
            {"addr": addr, "type": "lamp"}
            for addr in app.VAKIO_LARNITECH_MODE_ADDRS.values()
        ]
        commands = {
            app.vakio_command_from_larnitech_update(
                {"addr": addr, "status": "0x01"}, devices,
            )["value"]
            for addr in app.VAKIO_LARNITECH_MODE_ADDRS.values()
        }
        self.assertEqual(commands, set(app.VAKIO_MODES))

    def test_all_larnitech_speed_buttons_map_to_supported_commands(self):
        devices = [
            {"addr": addr, "type": "lamp"}
            for addr in app.VAKIO_LARNITECH_SPEED_ADDRS.values()
        ]
        commands = {
            app.vakio_command_from_larnitech_update(
                {"addr": addr, "status": {"state": "on"}}, devices,
            )["value"]
            for addr in app.VAKIO_LARNITECH_SPEED_ADDRS.values()
        }
        self.assertEqual(commands, set(app.VAKIO_SPEEDS))

    def test_mode_and_speed_off_events_do_not_send_commands(self):
        addr = app.VAKIO_LARNITECH_MODE_ADDRS["night"]
        devices = [{"addr": addr, "type": "lamp"}]
        self.assertIsNone(app.vakio_command_from_larnitech_update(
            {"addr": addr, "status": "0x00"}, devices,
        ))

    def test_unknown_larnitech_address_cannot_control_vakio(self):
        self.assertIsNone(app.vakio_command_from_larnitech_update(
            {"addr": "407:199", "status": "0x01"},
            [{"addr": "407:199", "type": "lamp"}],
        ))

    def test_real_status_event_shape_updates_co2(self):
        devices = [{"addr": "315:36", "type": "co2-sensor", "status": {"state": 687}}]
        event = {"event": "statuses", "devices": [{"addr": "315:36", "status": "0x0B03"}]}
        changed = app.merge_larnitech_devices(devices, event["devices"])
        self.assertEqual(changed, ["315:36"])
        self.assertEqual(devices[0]["status"]["state"], 779)


if __name__ == "__main__":
    unittest.main()
