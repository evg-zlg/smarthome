#!/usr/bin/env python3
"""Preserve the current VAKIO web form and change only its MQTT settings."""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from html.parser import HTMLParser


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}
        self.select: str | None = None
        self.first_option: str | None = None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_list)
        if tag == "input" and attrs.get("name"):
            kind = attrs.get("type", "text")
            if kind in {"radio", "checkbox"} and "checked" not in attrs:
                return
            self.values[attrs["name"]] = attrs.get("value", "on") or ""
        elif tag == "select" and attrs.get("name"):
            self.select = attrs["name"]
            self.first_option = None
        elif tag == "option" and self.select:
            value = attrs.get("value", "") or ""
            self.first_option = self.first_option or value
            if "selected" in attrs:
                self.values[self.select] = value

    def handle_endtag(self, tag: str) -> None:
        if tag == "select" and self.select:
            self.values.setdefault(self.select, self.first_option or "")
            self.select = None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.1.164")
    parser.add_argument("--broker", default="192.168.1.183")
    parser.add_argument("--topic", default="vakio")
    parser.add_argument("--username", default="vakio")
    args = parser.parse_args()
    password = os.environ.get("VAKIO_MQTT_PASSWORD")
    if not password:
        raise SystemExit("VAKIO_MQTT_PASSWORD is required")

    url = f"http://{args.host}/"
    with urllib.request.urlopen(url, timeout=8) as response:
        html = response.read().decode("utf-8")
    form = FormParser()
    form.feed(html)
    form.values.update(
        {
            "choose-type-mqtt": "1",
            "MQTTNAME": args.broker,
            "MQTTPORT": "1883",
            "MQTTLOGIN": args.username,
            "MQTTPASSWORD": password,
            "topic": args.topic,
        }
    )
    request = urllib.request.Request(
        f"http://{args.host}/newdata",
        data=json.dumps(form.values).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise SystemExit(f"VAKIO returned HTTP {response.status}")
    print("VAKIO MQTT settings updated")


if __name__ == "__main__":
    main()
