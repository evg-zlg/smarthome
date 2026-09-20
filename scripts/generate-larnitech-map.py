#!/usr/bin/env python3
"""Generate stable human- and machine-readable Larnitech inventory files."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any


def clean(value: Any) -> Any:
    if isinstance(value, str):
        return "".join(character if ord(character) >= 32 else "�" for character in value)
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    return value


def escape(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("json_output", type=Path)
    parser.add_argument("markdown_output", type=Path)
    args = parser.parse_args()

    response = clean(json.loads(args.source.read_text()))
    devices = response.get("devices", [])
    output = {
        "schema_version": 1,
        "source": "Larnitech API2 get-devices detailed",
        "controller": "192.168.1.185",
        "entity_count": len(devices),
        "entities": devices,
    }
    args.json_output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")

    areas = collections.Counter(device.get("area", "") for device in devices)
    types = collections.Counter(device.get("type", "") for device in devices)
    lines = [
        "# Сущности Larnitech",
        "",
        "Источник: API2 `get-devices` с детальным состоянием.",
        f"Всего сущностей: **{len(devices)}**.",
        "",
        "Полный машиночитаемый снимок: [`larnitech-entities.json`](larnitech-entities.json).",
        "",
        "## Помещения и группы",
        "",
        "| Группа | Количество |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {escape(area)} | {count} |" for area, count in sorted(areas.items()))
    lines += ["", "## Типы", "", "| Тип | Количество |", "| --- | ---: |"]
    lines.extend(f"| `{escape(kind)}` | {count} |" for kind, count in sorted(types.items()))
    lines += [
        "",
        "## Полный перечень",
        "",
        "Состояние — снимок на момент выгрузки, а не постоянная характеристика.",
        "",
        "| Адрес | Группа | Название | Тип | Состояние |",
        "| --- | --- | --- | --- | --- |",
    ]
    for device in sorted(devices, key=lambda item: tuple(int(part) for part in item.get("addr", "0:0").split(":"))):
        status = json.dumps(device.get("status", {}), ensure_ascii=False, separators=(",", ":"))
        lines.append(
            f"| `{escape(device.get('addr'))}` | {escape(device.get('area'))} | "
            f"{escape(device.get('name'))} | `{escape(device.get('type'))}` | `{escape(status)}` |"
        )
    args.markdown_output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
