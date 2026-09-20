import importlib.util
import os
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
        return FakeResult()


class GatewayTests(unittest.TestCase):
    def setUp(self):
        app.mqtt_client = FakeClient()

    def test_allowed_vakio_command(self):
        self.assertEqual(app.publish_vakio({"command": "speed", "value": 4}), ("vakio/speed", "4"))

    def test_rejects_unknown_command(self):
        with self.assertRaises(ValueError):
            app.publish_vakio({"command": "reset", "value": "1"})

    def test_snapshot_requires_larnitech_key(self):
        self.assertEqual(app.snapshot()["larnitech"]["status"], "api_key_required")


if __name__ == "__main__":
    unittest.main()
