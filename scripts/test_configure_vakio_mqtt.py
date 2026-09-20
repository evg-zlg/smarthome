import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("configure-vakio-mqtt.py")
spec = importlib.util.spec_from_file_location("configure_vakio_mqtt", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VakioSettingsTests(unittest.TestCase):
    def test_preserves_unrelated_fields_and_clears_credentials(self):
        html = """
        <input name="SSID" value="office">
        <input name="MQTTLOGIN" value="old-user">
        <input name="MQTTPASSWORD" value="old-secret">
        <input type="checkbox" name="BUTTONS" checked>
        """

        settings = module.build_settings(html, "192.0.2.10", "test-topic")

        self.assertEqual(settings["SSID"], "office")
        self.assertEqual(settings["BUTTONS"], "on")
        self.assertEqual(settings["MQTTNAME"], "192.0.2.10")
        self.assertEqual(settings["topic"], "test-topic")
        self.assertEqual(settings["MQTTLOGIN"], "")
        self.assertEqual(settings["MQTTPASSWORD"], "")

    def test_ignores_unchecked_checkbox(self):
        settings = module.build_settings(
            '<input type="checkbox" name="BUTTONS">', "192.0.2.10", "test-topic"
        )
        self.assertNotIn("BUTTONS", settings)

    def test_detects_requested_online_settings(self):
        html = """
        <input type="radio" name="choose-type-mqtt" value="1" checked>
        <input name="MQTTNAME" value="192.0.2.10">
        <input name="MQTTPORT" value="1883">
        <input name="MQTTLOGIN" value="">
        <input name="MQTTPASSWORD" value="">
        <input name="topic" value="test-topic">
        <label>Статус подключения: Онлайн</label>
        """
        self.assertTrue(module.settings_are_online(html, "192.0.2.10", "test-topic"))
        self.assertFalse(module.settings_are_online(html, "192.0.2.11", "test-topic"))


if __name__ == "__main__":
    unittest.main()
