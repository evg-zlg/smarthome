#!/usr/bin/env python3
"""Preserve the VAKIO web form and point its anonymous MQTT client locally."""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
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


def build_settings(html: str, broker: str, topic: str) -> dict[str, str]:
    form = FormParser()
    form.feed(html)
    form.values.update(
        {
            "choose-type-mqtt": "1",
            "MQTTNAME": broker,
            "MQTTPORT": "1883",
            # The tested Base Smart firmware does not persist these fields.
            # Keep them explicitly empty and protect its listener by source IP.
            "MQTTLOGIN": "",
            "MQTTPASSWORD": "",
            "topic": topic,
        }
    )
    return form.values


def settings_are_online(html: str, broker: str, topic: str) -> bool:
    form = FormParser()
    form.feed(html)
    expected = {
        "choose-type-mqtt": "1",
        "MQTTNAME": broker,
        "MQTTPORT": "1883",
        "MQTTLOGIN": "",
        "MQTTPASSWORD": "",
        "topic": topic,
    }
    return all(form.values.get(key) == value for key, value in expected.items()) and (
        "Статус подключения: Онлайн" in html
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.1.164")
    parser.add_argument("--broker", default="192.168.1.183")
    parser.add_argument("--topic", default="vakio")
    args = parser.parse_args()

    url = f"http://{args.host}/"
    with urllib.request.urlopen(url, timeout=8) as response:
        html = response.read().decode("utf-8")
    settings = build_settings(html, args.broker, args.topic)
    request = urllib.request.Request(
        f"http://{args.host}/newdata",
        data=json.dumps(settings).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status != 200:
                raise SystemExit(f"VAKIO returned HTTP {response.status}")
    except (TimeoutError, urllib.error.URLError):
        # This firmware often reboots before completing the HTTP response.
        pass

    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        time.sleep(2)
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                current_html = response.read().decode("utf-8")
            if settings_are_online(current_html, args.broker, args.topic):
                print("VAKIO anonymous MQTT settings updated and online")
                return
        except (TimeoutError, urllib.error.URLError):
            continue
    raise SystemExit("VAKIO did not return online with the requested MQTT settings")


if __name__ == "__main__":
    main()
