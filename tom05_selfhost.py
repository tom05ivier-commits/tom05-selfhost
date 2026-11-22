# SPDX-License-Identifier: Tom05ivier-commits-1.0
# Copyright (c) 2026 Tomi vier
# Lisensi: Tom05ivier-commits v1.0 — lihat file LICENSE di root proyek.
"""Server inferensi mandiri tom05 (self-hosted), tanpa pihak ketiga.

Server ini sengaja TIDAK meneruskan permintaan ke model opencode maupun pihak
ketiga lainnya. Ia hanya:

* mengiklankan identitas ``tom05-flash-free``;
* menolak chat dengan HTTP 503 sampai pemilik menghubungkan endpoint inferensi
  miliknya sendiri lewat ``TOM05_SELFHOST_ENDPOINT`` (wajib loopback);
* meneruskan ke endpoint lokal itu bila sudah diset — itu pun hanya loopback.

Tidak ada kredensial yang dibaca, disimpan, atau dicetak. Prompt tidak masuk log.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

PORT = int(os.environ.get("TOM05_SELFHOST_PORT", "8773"))
ENDPOINT = os.environ.get("TOM05_SELFHOST_ENDPOINT", "").strip().rstrip("/")
MODEL_ID = "tom05-flash-free"
CTL = int(os.environ.get("TOM05_SELFHOST_CTL", "100000000"))
LICENSE = "Tom05ivier-commits-1.0"
OWNER = "Tomi vier"


def loopback_ok(url: str) -> bool:
    """Terima hanya endpoint loopback; tolak jaringan eksternal."""
    if not url:
        return False
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _send(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return  # senyap: prompt/data tidak ditulis ke log

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")
        if path in ("/health", "/v1/health"):
            _send(self, 200, {
                "status": "ok",
                "provider": "tom05-selfhost",
                "model": MODEL_ID,
                "backend": "self-hosted",
                "endpoint_terhubung": loopback_ok(ENDPOINT),
                "pihak_ketiga": False,
                "license": LICENSE,
                "owner": OWNER,
            })
        elif path in ("/v1/models", "/models"):
            _send(self, 200, {
                "object": "list",
                "total": 1,
                "data": [{
                    "id": MODEL_ID,
                    "object": "model",
                    "owned_by": "tom05",
                    "name": "Tom05 flash Free",
                    "context_length": CTL,
                    "declared_only": True,
                    "license": LICENSE,
                }],
            })
        else:
            _send(self, 404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") not in ("/v1/chat/completions", "/chat/completions"):
            _send(self, 404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            _send(self, 400, {"error": "invalid JSON"})
            return
        if not isinstance(body, dict):
            _send(self, 400, {"error": "invalid body"})
            return
        if not loopback_ok(ENDPOINT):
            _send(self, 503, {
                "error": "backend mandiri belum terhubung",
                "catatan": (
                    "Server ini tidak meneruskan ke model pihak ketiga. Hubungkan "
                    "server inferensi milik pemilik lewat TOM05_SELFHOST_ENDPOINT "
                    "(wajib http://127.0.0.1 atau localhost)."
                ),
                "license": LICENSE,
            })
            return
        request = urllib.request.Request(
            f"{ENDPOINT}/v1/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "application/json")
        except Exception as exc:  # noqa: BLE001
            _send(self, 502, {"error": "endpoint lokal gagal", "jenis": type(exc).__name__})
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[tom05-selfhost] aktif di http://127.0.0.1:{PORT}/v1", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
