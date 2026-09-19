#!/usr/bin/env python3

"""Minimal safe placeholder for the future Larnitech/VAKIO adapter."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from os import environ


HOST = environ.get("GATEWAY_HTTP_HOST", "127.0.0.1")
PORT = int(environ.get("GATEWAY_HTTP_PORT", "8080"))


class Handler(BaseHTTPRequestHandler):
    server_version = "smarthome-gateway/0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/healthz":
            self.send_error(404)
            return

        payload = json.dumps(
            {
                "status": "waiting_for_configuration",
                "larnitech": "not_configured",
                "vakio": "not_configured",
                "control_enabled": False,
            },
            separators=(",", ":"),
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
