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


if __name__ == "__main__":
    unittest.main()
