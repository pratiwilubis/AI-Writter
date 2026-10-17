"""
Story Memory - server kecil tanpa dependensi tambahan.

Tugasnya:
1. Menyajikan halaman web (index.html, style.css, app.js)
2. Menyimpan cerita ke file story.json
3. Menjadi jembatan ke Ollama (model AI lokal, gratis)

Jalankan:  python server.py
Buka:      http://localhost:8000
"""

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "story.json"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
PORT = int(os.environ.get("PORT", "8000"))

# Seberapa banyak teks bab yang sedang ditulis ikut dikirim ke AI (dalam karakter).
# Untuk RAM 8 GB, biarkan kecil. Naikkan kalau komputermu kuat.
RECENT_CHARS = int(os.environ.get("RECENT_CHARS", "3000"))
NUM_CTX = int(os.environ.get("NUM_CTX", "4096"))

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}

EMPTY_STORY = {
    "title": "Ceritaku",
    "bible": "",
    "chapters": [{"title": "Bab 1", "text": "", "summary": ""}],
}

SYSTEM_PROMPT = (
    "Kamu adalah rekan menulis cerita yang teliti. "
    "Tulis dalam bahasa yang sama dengan cerita yang sudah ada. "
    "Patuhi STORY BIBLE dan RINGKASAN BAB SEBELUMNYA: jangan mengubah nama, sifat, "
    "atau fakta yang sudah ditetapkan, dan jangan bertentangan dengan kejadian sebelumnya. "
    "Hanya tulis lanjutan ceritanya saja, tanpa pembuka, penjelasan, atau komentar."
)


def load_story():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return json.loads(json.dumps(EMPTY_STORY))


def save_story(story):
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)


def ollama_request(path, payload=None, timeout=600):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        OLLAMA_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ollama_chat(model, messages, temperature=0.8):
    result = ollama_request(
        "/api/chat",
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": NUM_CTX, "temperature": temperature},
        },
    )
    return result["message"]["content"].strip()


def build_write_messages(story, chapter_index, instruction):
    """Menyusun 'ingatan' untuk AI: bible + ringkasan bab lama + teks terbaru."""
    chapters = story.get("chapters", [])
    parts = []

    bible = (story.get("bible") or "").strip()
    if bible:
        parts.append("=== STORY BIBLE ===\n" + bible)

    summaries = []
    for i, ch in enumerate(chapters[:chapter_index]):
        summary = (ch.get("summary") or "").strip()
        if summary:
            summaries.append(f"- {ch.get('title') or f'Bab {i + 1}'}: {summary}")
    if summaries:
        parts.append("=== RINGKASAN BAB SEBELUMNYA ===\n" + "\n".join(summaries))

    current = chapters[chapter_index] if 0 <= chapter_index < len(chapters) else {}
    text = (current.get("text") or "").strip()
    if text:
        recent = text[-RECENT_CHARS:]
        parts.append(
            f"=== TEKS TERBARU ({current.get('title') or 'bab ini'}) ===\n{recent}"
        )

    context = "\n\n".join(parts) if parts else "(Belum ada konteks. Ini awal cerita.)"
    task = instruction.strip() or "Lanjutkan cerita secara natural."

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{context}\n\n=== PERMINTAAN ===\n{task}\n\nTulis lanjutan ceritanya sekarang.",
        },
    ]


class Handler(BaseHTTPRequestHandler):
    server_version = "StoryMemory/1.0"

    # ---------- helper ----------
    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _ollama_error(self, exc):
        if isinstance(exc, urllib.error.URLError):
            msg = (
                "Tidak bisa terhubung ke Ollama. Pastikan Ollama sudah terinstall "
                "dan sedang berjalan, lalu coba lagi."
            )
        else:
            msg = f"Ollama bermasalah: {exc}"
        self._send(502, {"error": msg})

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    # ---------- GET ----------
    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path in STATIC_FILES:
            filename, ctype = STATIC_FILES[path]
            file_path = BASE_DIR / filename
            if not file_path.exists():
                return self._send(404, {"error": "File tidak ditemukan"})
            return self._send(200, file_path.read_bytes(), ctype)

        if path == "/api/story":
            return self._send(200, load_story())

        if path == "/api/models":
            try:
                tags = ollama_request("/api/tags", timeout=10)
                names = [m["name"] for m in tags.get("models", [])]
                return self._send(200, {"models": names, "default": DEFAULT_MODEL})
            except Exception as exc:  # noqa: BLE001
                return self._ollama_error(exc)

        self._send(404, {"error": "Tidak ditemukan"})

    # ---------- POST ----------
    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            body = self._read_json()
        except (json.JSONDecodeError, ValueError):
            return self._send(400, {"error": "JSON tidak valid"})

        if path == "/api/story":
            if not isinstance(body, dict) or "chapters" not in body:
                return self._send(400, {"error": "Format cerita tidak valid"})
            save_story(body)
            return self._send(200, {"ok": True})

        if path == "/api/write":
            story = load_story()
            index = int(body.get("chapter", 0))
            model = body.get("model") or DEFAULT_MODEL
            messages = build_write_messages(story, index, body.get("instruction", ""))
            try:
                text = ollama_chat(model, messages)
                return self._send(200, {"text": text})
            except Exception as exc:  # noqa: BLE001
                return self._ollama_error(exc)

        if path == "/api/summarize":
            story = load_story()
            index = int(body.get("chapter", 0))
            model = body.get("model") or DEFAULT_MODEL
            chapters = story.get("chapters", [])
            if not (0 <= index < len(chapters)):
                return self._send(400, {"error": "Bab tidak ditemukan"})
            text = (chapters[index].get("text") or "").strip()
            if not text:
                return self._send(400, {"error": "Bab ini masih kosong"})
            messages = [
                {
                    "role": "system",
                    "content": "Kamu meringkas bab cerita dengan akurat dan padat.",
                },
                {
                    "role": "user",
                    "content": (
                        "Rangkum bab berikut dalam 4 sampai 6 kalimat. Fokus pada kejadian penting, "
                        "keputusan tokoh, fakta baru, dan perubahan hubungan antar tokoh. "
                        "Tulis dalam bahasa yang sama dengan bab. Hanya ringkasannya saja.\n\n"
                        + text[-8000:]
                    ),
                },
            ]
            try:
                summary = ollama_chat(model, messages, temperature=0.3)
                return self._send(200, {"summary": summary})
            except Exception as exc:  # noqa: BLE001
                return self._ollama_error(exc)

        self._send(404, {"error": "Tidak ditemukan"})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Story Memory berjalan di http://localhost:{PORT}")
    print(f"Ollama: {OLLAMA_URL} | model bawaan: {DEFAULT_MODEL}")
    print("Tekan Ctrl+C untuk berhenti.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
