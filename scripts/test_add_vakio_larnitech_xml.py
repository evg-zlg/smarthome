import importlib.util
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT = Path(__file__).with_name("add-vakio-larnitech-xml.py")
spec = importlib.util.spec_from_file_location("add_vakio_larnitech_xml", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AddVakioLarnitechXmlTests(unittest.TestCase):
    def test_adds_all_operating_controls(self):
        result = module.add_vakio_area(
            '<?xml version="1.0"?><smart-house><area addr="1" name="Setup"/></smart-house>'
        )
        root = ET.fromstring(result)
        area = next(area for area in root.findall("area") if area.get("name") == "VAKIO")
        items = area.findall("item")
        self.assertEqual(len(items), 15)
        self.assertEqual(items[0].get("addr"), "407:220")
        self.assertTrue(all(item.get("virtual") == "yes" for item in items))

    def test_rejects_address_collision(self):
        with self.assertRaisesRegex(ValueError, "collision"):
            module.add_vakio_area(
                '<smart-house><area addr="1"><item addr="407:220"/></area></smart-house>'
            )

    def test_rejects_duplicate_area(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            module.add_vakio_area(
                '<smart-house><area addr="1" name="VAKIO"/></smart-house>'
            )


if __name__ == "__main__":
    unittest.main()
