# Story Memory

Teman menulis cerita dengan AI yang selalu ingat ceritamu. Jalan 100% di komputermu sendiri memakai [Ollama](https://ollama.com), gratis dan privat, tanpa API key.

## Cara kerja "ingatan"

Model AI tidak benar-benar mengingat apa pun di antara permintaan. Aplikasi ini menyiasatinya dengan menyimpan cerita di luar model, lalu mengirim bagian yang penting setiap kali kamu minta AI menulis:

1. **Story Bible**: tokoh, sifat, latar, aturan dunia. Selalu dikirim.
2. **Ringkasan bab sebelumnya**: bab lama diringkas supaya hemat memori.
3. **Teks terbaru**: beberapa paragraf terakhir dari bab yang sedang ditulis.

Dengan begitu cerita bisa panjang, tapi model kecil tetap muat membacanya.

## Persyaratan

- Windows, Mac, atau Linux
- [Python 3.8+](https://www.python.org/downloads/) (tanpa library tambahan)
- [Ollama](https://ollama.com/download)
- RAM minimal 8 GB (pakai model kecil 3B sampai 4B)

## Cara menjalankan

1. Install Ollama, lalu unduh model kecil lewat Command Prompt atau PowerShell:

   ```
   ollama pull llama3.2:3b
   ```

   Alternatif: `ollama pull gemma3:4b`. Daftar model: https://ollama.com/library

2. Jalankan server di folder project ini:

   ```
   python server.py
   ```

3. Buka http://localhost:8000 di browser.

## Pengaturan (opsional)

Atur lewat environment variable sebelum menjalankan server:

| Variabel | Fungsi | Bawaan |
|---|---|---|
| `OLLAMA_MODEL` | Model bawaan | `llama3.2:3b` |
| `OLLAMA_URL` | Alamat Ollama | `http://localhost:11434` |
| `RECENT_CHARS` | Panjang teks terbaru yang dikirim ke AI | `3000` |
| `NUM_CTX` | Ukuran konteks model | `4096` |
| `PORT` | Port server | `8000` |

Contoh di PowerShell:

```
$env:OLLAMA_MODEL = "gemma3:4b"; python server.py
```

## Tips pemakaian

- Isi Story Bible dulu, makin jelas makin konsisten.
- Setelah selesai satu bab, klik **Rangkum otomatis**, lalu perbaiki ringkasannya kalau ada yang salah.
- Hasil AI muncul sebagai pratinjau. Kamu bisa edit, coba lagi, atau buang sebelum masuk ke cerita.
- Kalau laptop terasa lambat, tutup aplikasi berat lain atau pakai model yang lebih kecil.

## Upload ke GitHub

```
git init
git add .
git commit -m "Story Memory pertama"
git branch -M main
git remote add origin https://github.com/USERNAME/story-memory.git
git push -u origin main
```

File `story.json` (ceritamu) sudah masuk `.gitignore`, jadi tidak ikut terupload.

## Struktur file

- `server.py`: server Python, penyimpan cerita, jembatan ke Ollama
- `index.html`, `style.css`, `app.js`: tampilan web
- `story.json`: dibuat otomatis, berisi ceritamu
