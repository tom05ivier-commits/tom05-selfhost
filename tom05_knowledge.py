# SPDX-License-Identifier: Tom05ivier-commits-1.0
# Copyright (c) 2026 Tomi vier
# Lisensi: Tom05ivier-commits v1.0 — lihat file LICENSE di root proyek.
"""Model pengetahuan tom05 berbasis retrieval dari data workspace.

Ini BUKAN model neural terlatih. Tidak ada bobot, dataset training, atau
pelatihan. Artefak ini mengindeks berkas teks milik IT Agenty, menyaringnya
dengan ``security.privacy.redact``, lalu menjawab dengan mengambil potongan
ter relevan (TF-IDF ringan, tanpa dependensi eksternal).

Tujuan: menyediakan responder nyata untuk identitas ``tom05-flash-free``
tanpa terhubung ke model pihak ketiga, sekaligus jujur tentang sifatnya.
"""

from __future__ import annotations

import math
import os
import re
import sys
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from security.privacy import redact
except Exception:  # pragma: no cover
    def redact(text: str) -> str:  # type: ignore[misc]
        return text

MODEL_ID = "tom05-flash-free"
KIND = "retrieval-grounded"
TRAINED = False
LICENSE = "Tom05ivier-commits-1.0"
OWNER = "Tomi vier"

EXCLUDE_DIRS = {
    ".git", "node_modules", "opencode-src", "src", "symphony-src",
    "publish", "credentials", "reports", "quarantine", "__pycache__",
    ".playwright-mcp", "site", "chip", "security",
}
ALLOWED_EXT = {".md", ".py", ".json", ".txt", ".sh", ".yml", ".yaml", ".v", ".html", ".css"}
MAX_FILE = 200_000
CHARS = 900
OVERLAP = 150
TOP_N = 3

STOP = {
    "yang", "dan", "atau", "di", "ke", "dari", "untuk", "pada", "dengan", "ini", "itu",
    "adalah", "ada", "bagaimana", "apa", "mengapa", "kapan", "dimana", "siapa", "the",
    "a", "an", "is", "are", "of", "to", "in", "for", "and", "or", "on", "with", "how",
    "what", "why", "when", "where", "who", "can", "do", "does", "tolong", "jelaskan",
    "info", "status", "cek", "lihat", "berikan", "saya", "kamu", "nya", "kan", "lah",
}
TOKEN_RE = re.compile(r"[a-z0-9_./-]{2,}")


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOP]


def _iter_files() -> list[Path]:
    """Telusuri file teks, memangkas direktori besar sejak awal (cepat)."""
    out: list[Path] = []
    for current, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        base = Path(current)
        for name in files:
            path = base / name
            if path.suffix.lower() not in ALLOWED_EXT:
                continue
            try:
                if path.stat().st_size > MAX_FILE:
                    continue
                out.append(path)
            except OSError:
                continue
    return sorted(out)


class KnowledgeModel:
    """Indeks retrieval ringan dari data workspace yang sudah disaring privasi."""

    def __init__(self) -> None:
        self.chunks: list[str] = []
        self.sources: list[str] = []
        self.doc_freq: Counter[str] = Counter()
        self.postings: dict[str, list[int]] = {}
        self._build()

    def _build(self) -> None:
        for path in _iter_files():
            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            clean = redact(raw)
            rel = str(path.relative_to(ROOT))
            start = 0
            while start < len(clean):
                piece = clean[start:start + CHARS].strip()
                if piece:
                    idx = len(self.chunks)
                    self.chunks.append(piece)
                    self.sources.append(rel)
                    for token in set(tokenize(piece)):
                        self.postings.setdefault(token, []).append(idx)
                        self.doc_freq[token] += 1
                start += max(1, CHARS - OVERLAP)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "kind": KIND,
            "trained": TRAINED,
            "chunks": len(self.chunks),
            "berkas": len(set(self.sources)),
            "model": MODEL_ID,
            "license": LICENSE,
            "owner": OWNER,
            "catatan": "Model pengetahuan berbasis retrieval; bukan model neural terlatih.",
        }

    def answer(self, question: str) -> dict[str, Any]:
        tokens = tokenize(question)
        if not tokens:
            content = (
                "Pertanyaan kosong atau hanya memuat kata umum. Saya adalah model "
                "pengetahuan berbasis retrieval dari data workspace IT Agenty, bukan "
                "model neural terlatih."
            )
            return self._wrap(content, [])

        n = max(1, len(self.chunks))
        scores: Counter[int] = Counter()
        for token in tokens:
            postings = self.postings.get(token, [])
            if not postings:
                continue
            idf = math.log(1 + n / (1 + len(postings)))
            for idx in postings:
                scores[idx] += idf * (1 + math.log(1 + self.chunks[idx].lower().count(token)))

        best = scores.most_common(TOP_N)
        if not best:
            content = (
                "Saya tidak menemukan potongan data workspace yang relevan dengan "
                "pertanyaan ini. Saya hanya menjawab dari data IT Agenty yang tersedia "
                "secara lokal (retrieval), bukan model neural terlatih."
            )
            return self._wrap(content, [])

        parts: list[str] = []
        used: list[str] = []
        for idx, _score in best:
            src = self.sources[idx]
            if src not in used:
                used.append(src)
            parts.append(f"[{src}]\n{self.chunks[idx]}")
        content = (
            "Dari data workspace IT Agenty yang tersedia (retrieval, bukan model "
            "neural terlatih):\n\n" + "\n\n---\n\n".join(parts)
        )
        return self._wrap(content, used)

    def _wrap(self, content: str, sources: list[str]) -> dict[str, Any]:
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "model": MODEL_ID,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "tom05": {
                "kind": KIND,
                "trained": TRAINED,
                "sources": sources,
                "license": LICENSE,
                "owner": OWNER,
                "catatan": "Dihasilkan dari data workspace via retrieval; bukan model neural terlatih.",
            },
        }


_MODEL: KnowledgeModel | None = None


def get_model() -> KnowledgeModel:
    global _MODEL
    if _MODEL is None:
        _MODEL = KnowledgeModel()
    return _MODEL


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Model pengetahuan tom05 (retrieval)")
    ap.add_argument("question", nargs="?")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    model = get_model()
    print(json.dumps(model.stats if args.stats else model.answer(args.question or "status"),
                     indent=2, ensure_ascii=False))
