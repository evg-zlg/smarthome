#!/usr/bin/env python3
"""Add the allowlisted VAKIO virtual controls to a Larnitech logic.xml."""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

AREA_ADDR = "65536262"
POWER_ADDR = "407:220"
MODES = {
    "inflow": ("407:221", "VAKIO · Режим · Приток"),
    "inflow_max": ("407:222", "VAKIO · Режим · Приток MAX"),
    "recuperator": ("407:223", "VAKIO · Режим · Рекуперация лето"),
    "winter": ("407:224", "VAKIO · Режим · Рекуперация зима"),
    "outflow": ("407:225", "VAKIO · Режим · Вытяжка"),
    "outflow_max": ("407:226", "VAKIO · Режим · Вытяжка MAX"),
    "night": ("407:227", "VAKIO · Режим · Ночной"),
}
SPEEDS = {
    str(speed): (f"407:{227 + speed}", f"VAKIO · Скорость · {speed}")
    for speed in range(1, 8)
}


def vakio_area_xml() -> str:
    items = [
        f'\t\t<item addr="{POWER_ADDR}" image="air-fan" name="VAKIO · Питание" type="lamp" virtual="yes"/>'
    ]
    items.extend(
        f'\t\t<item addr="{addr}" image="air-fan" name="{name}" type="lamp" virtual="yes"/>'
        for addr, name in MODES.values()
    )
    items.extend(
        f'\t\t<item addr="{addr}" image="air-fan" name="{name}" type="lamp" virtual="yes"/>'
        for addr, name in SPEEDS.values()
    )
    return f'\t<area addr="{AREA_ADDR}" name="VAKIO">\n' + "\n".join(items) + "\n\t</area>\n"


def add_vakio_area(xml: str) -> str:
    root = ET.fromstring(xml)
    if any(area.get("name") == "VAKIO" for area in root.findall("area")):
        raise ValueError("VAKIO area already exists")
    used_addresses = {
        item.get("addr") for item in root.iter() if item.get("addr")
    }
    requested = {AREA_ADDR, POWER_ADDR}
    requested.update(addr for addr, _ in MODES.values())
    requested.update(addr for addr, _ in SPEEDS.values())
    collisions = sorted(used_addresses & requested)
    if collisions:
        raise ValueError(f"Larnitech address collision: {', '.join(collisions)}")
    marker = "</smart-house>"
    if xml.count(marker) != 1:
        raise ValueError("Unexpected Larnitech XML root")
    result = xml.replace(marker, vakio_area_xml() + marker)
    ET.fromstring(result)
    return result


def rename_vakio_items(xml: str) -> str:
    """Prefix every existing VAKIO selector without changing its address."""
    root = ET.fromstring(xml)
    area = next((item for item in root.findall("area") if item.get("name") == "VAKIO"), None)
    if area is None:
        raise ValueError("VAKIO area does not exist")
    expected = {POWER_ADDR: "VAKIO · Питание"}
    expected.update({addr: name for addr, name in MODES.values()})
    expected.update({addr: name for addr, name in SPEEDS.values()})
    by_addr = {item.get("addr"): item for item in area.findall("item")}
    missing = sorted(set(expected) - set(by_addr))
    if missing:
        raise ValueError(f"Missing VAKIO addresses: {', '.join(missing)}")
    result = xml
    for addr, name in expected.items():
        pattern = rf'(<item\b(?=[^>]*\baddr="{re.escape(addr)}")[^>]*\bname=")[^"]*(")'
        result, count = re.subn(pattern, rf'\g<1>{name}\g<2>', result, count=1)
        if count != 1:
            raise ValueError(f"Could not rename VAKIO address: {addr}")
    ET.fromstring(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rename-existing", action="store_true")
    args = parser.parse_args()
    transform = rename_vakio_items if args.rename_existing else add_vakio_area
    args.output.write_text(transform(args.input.read_text()), encoding="utf-8")


if __name__ == "__main__":
    main()
