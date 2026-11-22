<!--
  SPDX-License-Identifier: Tom05ivier-commits-1.0
  Copyright (c) 2026 Tomi vier
  Lisensi: Tom05ivier-commits v1.0 — lihat file LICENSE di root proyek.
-->

# tom05-selfhost — server inferensi mandiri Tom05

Server OpenAI-compatible mandiri untuk identitas **Tom05 flash Free**.
Tidak terhubung ke model pihak ketiga mana pun.

## Prinsip

- Hanya mengiklankan `tom05-flash-free`.
- Menolak chat dengan HTTP 503 sampai endpoint inferensi milik pemilik diset.
- Endpoint wajib **loopback** (`http://127.0.0.1` / `http://localhost`);
  alamat eksternal ditolak.
- Tidak membaca, menyimpan, atau mencetak kredensial. Prompt tidak masuk log.

## Menjalankan

```bash
TOM05_SELFHOST_PORT=8773 python3 tom05_selfhost.py
curl http://127.0.0.1:8773/health
curl http://127.0.0.1:8773/v1/models
```

Tanpa endpoint, `POST /v1/chat/completions` mengembalikan 503. Ini disengaja:
tidak ada model terlatih yang diklaim, dan tidak ada forward ke pihak ketiga.

## Menghubungkan server inferensi sendiri

```bash
TOM05_SELFHOST_ENDPOINT=http://127.0.0.1:8000 python3 tom05_selfhost.py
```

Server lokal di `:8000` harus menyediakan `/v1/chat/completions` dan berada di
loopback. Setelah terhubung, `/health` menampilkan
`"endpoint_terhubung": true`.

## Pengujian

```bash
python3 -m unittest test_tom05_selfhost -v
```

## Lisensi

**Tom05ivier-commits-1.0**, pemilik **Tomi vier**. Lihat `LICENSE` dan
`TOM05-FLASH-FREE-NOTICE.md`. Ini bukan model terlatih baru; backend inferensi
disiapkan terpisah oleh pemilik.
