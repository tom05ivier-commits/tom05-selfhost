# SPDX-License-Identifier: Tom05ivier-commits-1.0
# Copyright (c) 2026 Tomi vier
# Lisensi: Tom05ivier-commits v1.0 — lihat file LICENSE di root proyek.
"""Pengujian server inferensi mandiri tom05 (self-hosted, tanpa pihak ketiga)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system import tom05_selfhost as srv  # noqa: E402


class SelfHostLogicTests(unittest.TestCase):
    def test_loopback_validation(self) -> None:
        self.assertFalse(srv.loopback_ok(""))
        self.assertFalse(srv.loopback_ok("https://api.pihak-ketiga.com"))
        self.assertFalse(srv.loopback_ok("http://192.168.1.10:8000"))
        self.assertTrue(srv.loopback_ok("http://127.0.0.1:8000"))
        self.assertTrue(srv.loopback_ok("http://localhost:8000"))
        self.assertTrue(srv.loopback_ok("http://[::1]:8000"))

    def test_registry_entry(self) -> None:
        data = json.loads((ROOT / "system" / "services.json").read_text(encoding="utf-8"))
        entry = next(s for s in data["services"] if s["name"] == "tom05-selfhost")
        self.assertEqual(entry["kind"], "http")
        self.assertEqual(entry["port"], 8773)
        self.assertEqual(entry["command"][-1], "system/tom05_selfhost.py")

    def test_license_header(self) -> None:
        text = (ROOT / "system" / "tom05_selfhost.py").read_text(encoding="utf-8")[:300]
        self.assertIn("SPDX-License-Identifier: Tom05ivier-commits-1.0", text)
        self.assertIn("Copyright (c) 2026 Tomi vier", text)


class SelfHostHttpTests(unittest.TestCase):
    PORT = "8793"

    @classmethod
    def setUpClass(cls) -> None:
        env = dict(os.environ, TOM05_SELFHOST_PORT=cls.PORT)
        env.pop("TOM05_SELFHOST_ENDPOINT", None)  # pastikan belum terhubung
        cls.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "system" / "tom05_selfhost.py")],
            cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(40):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{cls.PORT}/health", timeout=2
                ) as response:
                    cls.health = json.loads(response.read())
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.15)
        else:
            raise RuntimeError("server self-host tidak mulai")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def test_health_and_models(self) -> None:
        self.assertEqual(self.health["backend"], "self-hosted")
        self.assertIs(self.health["pihak_ketiga"], False)
        self.assertIs(self.health["endpoint_terhubung"], False)
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.PORT}/v1/models", timeout=5
        ) as response:
            data = json.loads(response.read())
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["data"][0]["id"], "tom05-flash-free")

    def test_chat_refused_without_endpoint(self) -> None:
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.PORT}/v1/chat/completions",
            data=json.dumps({"model": "tom05-flash-free", "messages": []}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 503)
        body = json.loads(ctx.exception.read())
        self.assertIn("belum terhubung", body["error"])


if __name__ == "__main__":
    unittest.main()
