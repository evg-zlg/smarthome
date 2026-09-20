import importlib.util
import os
import threading
import time
import unittest
from pathlib import Path

os.environ["CONTROL_ENABLED"] = "true"
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


class GatewayTests(unittest.TestCase):
    def setUp(self):
        app.mqtt_client = FakeClient()
        app.last_device_message_monotonic = time.monotonic()
        app.pending_confirmation = None
        app.state["mqtt"].update(status="waiting", updated_at=None, error=None)
        app.state["larnitech"].update(status="not_configured", updated_at=None, devices=[], error=None)
        app.state["vakio"]["topics"] = {}

    def test_allowed_vakio_command(self):
        self.assertEqual(app.publish_vakio({"command": "speed", "value": 4}), ("vakio/speed", "4"))

    def test_rejects_unknown_command(self):
        with self.assertRaises(ValueError):
            app.publish_vakio({"command": "reset", "value": "1"})

    def test_snapshot_requires_larnitech_key(self):
        self.assertEqual(app.snapshot()["larnitech"]["status"], "api_key_required")

    def test_successful_connect_subscribes_with_no_local(self):
        class Client:
            def subscribe(self, topic, options):
                self.subscription = (topic, options)

        client = Client()
        reason = type("Reason", (), {"is_failure": False})()
        app.on_connect(client, None, {}, reason)
        self.assertEqual(client.subscription[0], "vakio/#")
        self.assertTrue(client.subscription[1].noLocal)

    def test_rejects_command_without_fresh_telemetry(self):
        app.last_device_message_monotonic = None
        with self.assertRaisesRegex(RuntimeError, "telemetry is not fresh"):
            app.publish_vakio({"command": "state", "value": "on"})

    def test_snapshot_contains_dashboard_contract(self):
        app.state["mqtt"].update(status="online", updated_at=app.utc_timestamp())
        app.state["larnitech"].update(
            status="online",
            updated_at=app.utc_timestamp(),
            devices=[
                {"addr": "315:36", "type": "co2", "status": {"state": 640}},
                {"addr": "456:237", "type": "connection", "status": {"state": "opened"}},
                {"addr": "456:249", "type": "conditioner", "status": {"state": "off"}},
            ],
        )
        result = app.snapshot()
        observed = result["observed"]

        self.assertEqual(observed["services"]["mqtt"]["status"], "online")
        self.assertEqual(observed["api_channels"]["total"], 3)
        self.assertEqual(observed["climate"][0]["value"], 640)
        self.assertTrue(observed["air_conditioner"]["connected"])
        self.assertTrue(observed["read_only"])


if __name__ == "__main__":
    unittest.main()
