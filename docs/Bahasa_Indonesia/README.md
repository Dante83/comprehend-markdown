# comprehend-markdown

*Sentuhlah gulungan itu dan ucapkan mantra rahasianya. Beberapa menit hingga satu jam kemudian (tergantung ketebalan gulungannya), Anda akan memahami Markdown dalam bahasa apa pun.*

Sebuah server MCP yang menerjemahkan `README.md` sebuah proyek ke dalam bahasa lain, serta pipeline mandiri yang menjalankan siklus penulis/peninjau terhadap dokumen tersebut menggunakan model LM Studio lokal.

Bahasa sumber dan target keduanya dapat dikonfigurasi — Bahasa Inggris hanyalah setelan bawaan. Atur `source_language` untuk menerjemahkan *dari* bahasa Mandarin, Indonesia, atau bahasa lainnya, dan `target_languages` untuk memilih bahasa tujuan (lihat [Memilih bahasa sumber dan target](#memilih-bahasa-sumber-dan-target)).

Untuk proyek target apa pun, sistem ini mengharapkan (dan akan membuatnya jika diperlukan):

```
<project-root>/docs/<source>/README.md  sumber kanonik (default: Bahasa Inggris)
<project-root>/docs/<lang>/README.md    versi terjemahan, satu per bahasa
<project-root>/README.md                halaman arahan pemilih bahasa (dihasilkan otomatis)
```

Proyek yang belum dimigrasi — di mana sumbernya masih berada di root — juga tetap bisa digunakan: `README.md` di root akan digunakan sebagai sumber, dan pada akhir proses `pipeline`, file tersebut akan dipindahkan ke `docs/<source>/` (misalnya `docs/English/`) dan digantikan oleh halaman arahan singkat yang menautkan setiap terjemahan yang tersedia.

## Setup

Semua proses (pembuatan venv, instalasi/sinkronisasi dependensi) ditangani oleh `run.sh` — tidak ada langkah instalasi terpisah. Skrip ini membaca paket dari `requirements.txt` dan menginstalnya kembali pada setiap eksekusi, jadi untuk memperbarui dependensi cukup dengan menjalankannya kembali.

Jika Anda ingin menggunakan model LM Studio lokal selain model bawaan, salin contoh konfigurasi dan edit:

```bash
cp config.local.json.example config.local.json
```

`config.local.json` masuk dalam `.gitignore` dan akan menimpa kunci di `config.json` satu per satu, sehingga Anda dapat menyesuaikan `lm_studio_url` / `model_name` / `api_key` secara lokal tanpa mengubah setelan bawaan yang sudah dikomit.

### Memilih bahasa sumber dan target

Dua kunci konfigurasi mengontrol arah penerjemahan, dan baik server maupun pipeline membacanya (dari `config.py`), sehingga keduanya selalu sinkron:

- **`source_language`** — bahasa yang digunakan dalam `README.md` kanonik Anda, sekaligus nama folder `docs/<source_language>/`. Defaultnya adalah `"English"`. Atur menjadi `"中文"`, `"Bahasa Indonesia"`, atau lainnya untuk menerjemahkan *dari* bahasa tersebut.
- **`target_languages`** — daftar bahasa tujuan penerjemahan pipeline. Entri apa pun yang sama dengan `source_language` akan dilewati secara otomatis, jadi tidak masalah jika bahasa sumber tetap ada dalam daftar ini.

Sebagai contoh, untuk menerjemahkan README bahasa Mandarin ke dalam bahasa Inggris dan Spanyol:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Jika `target_languages` dikosongkan, pipeline akan menggunakan daftar bawaan yang terdiri dari 18 bahasa.

`api_key` hanya berpengaruh jika Anda mengaktifkan "Require API Key" pada pengaturan server Developer di LM Studio — jika tidak, biarkan tetap `"lm-studio"`, karena LM Studio akan mengabaikannya. Perlu dicatat bahwa ini hanya berlaku untuk mode `pipeline`, satu-satunya bagian yang memanggil endpoint kompatibel OpenAI milik LM Studio secara langsung; mode `serve` tidak pernah berkomunikasi dengan API LM Studio karena LM Studio *adalah* klien MCP yang memanggilnya.

## Penggunaan

```bash
./run.sh serve    /absolute/path/to/project   # server MCP stdio
./run.sh pipeline /absolute/path/to/project   # menjalankan main.py end-to-end
```

Kedua mode memerlukan jalur **absolut** ke folder proyek yang berisi `README.md` yang akan diterjemahkan. Dalam mode `pipeline`, Anda dapat mengosongkannya dan akan diminta memasukkannya nanti, asalkan Anda menjalankannya secara interaktif di terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(Mode `serve` tidak pernah meminta input — setelah dimulai, stdin/stdout menjadi saluran JSON-RPC MCP itu sendiri, dan host MCP meluncurkannya secara non-interaktif.)

### `serve` — sebagai tool host MCP

Inilah yang harus dituju oleh `command` server pada host MCP (misalnya LM Studio), dengan jalur absolut proyek target sebagai argumen tetap. Mode ini menyediakan:

- **tool** `write_readme(language, content)` — menulis file `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — menulis `README.md` di root (halaman arahan pemilih bahasa)
- **resource** `docs://readme` — sumber utama (`docs/<source_language>/README.md`, atau fallback ke `README.md` di root)
- **resource** `docs://readme/{language}` — terjemahan yang sudah ada, jika tersedia
- **resource** `docs://dir_readme` — file `README.md` di root
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — siklus penerjemahan baru
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — jalur pembaruan: membandingkan terjemahan yang ada dengan sumber saat ini dan memperbaikinya dengan perubahan minimal
- **prompt** `create_docs_language_directory` — membangun halaman pemilih bahasa di root dari daftar terjemahan yang tersedia

Model milik host-lah yang menggerakkan pemanggilan tool; server ini hanya menyediakan I/O file dan templat prompt.

#### Menambahkannya ke LM Studio

Konfigurasi MCP LM Studio berada di `~/.lmstudio/mcp.json`. Tambahkan entri seperti ini:

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/absolute/path/to/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/absolute/path/to/the/project/you/want/to/translate"
      ]
    }
  }
}
```

Entri `args` kedua ditetapkan saat koneksi — konfigurasi LM Studio adalah JSON statis tanpa dukungan prompt interaktif, jadi itu harus berupa jalur aktual yang ingin Anda terjemahkan, bukan jalur repo ini (kecuali jika repo inilah proyek yang ingin Anda terjemahkan).

### `pipeline` — mandiri, tanpa host MCP

Menjalankan siklus lengkap translate $\rightarrow$ critique $\rightarrow$ revise untuk `target_languages` yang dikonfigurasi (daftar default 18 bahasa: Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — lihat [Memilih bahasa sumber dan target](#memilih-bahasa-sumber-dan-target) untuk mengubah daftar atau bahasa sumber), dengan memanggil endpoint kompatibel OpenAI milik LM Studio secara langsung untuk giliran penulis/peninjau, serta menjalankan salinan internal `server.py` melalui stdio untuk melakukan I/O file. Berguna untuk penerjemahan massal tanpa harus mengoperasikannya melalui UI LM Studio. Waktu eksekusi bergantung pada ukuran dokumen pada model lokal — beberapa menit untuk README kecil, hingga sekitar satu jam untuk dokumen besar yang dibagi menjadi beberapa bagian (chunked).

Bahasa yang sudah memiliki `docs/<language>/README.md` tidak akan diterjemahkan ulang dari awal: peninjau membandingkan terjemahan yang ada dengan sumber saat ini dan, hanya jika ada perubahan, penulis memperbaikinya dengan pengeditan minimal. Terjemahan yang sudah mutakhir akan dilewati sepenuhnya, sehingga menjalankan ulang pipeline setelah mengedit README hanya akan memproses bagian yang usang.

Setelah pekerjaan per bahasa selesai, proses diakhiri dengan (jika perlu) memindahkan `README.md` sumber dari root ke `docs/<source_language>/` dan menghasilkan ulang `README.md` di root sebagai halaman pemilih bahasa singkat yang menautkan setiap terjemahan yang tidak kosong.

Memerlukan server lokal LM Studio yang sedang berjalan (lihat `config.json`) dengan model chat apa pun yang sudah dimuat — pipeline menggerakkan model dengan penyelesaian teks biasa (plain text completions) dan melakukan penulisan file sendiri, sehingga model **tidak** perlu mendukung pemanggilan tool gaya OpenAI (lihat "Penanganan README Besar" di bawah). Tetap disarankan untuk menguji satu bahasa terlebih dahulu sebelum mempercayakan eksekusi penuh ke seluruh daftar.

### Penanganan README Besar

Menerjemahkan README besar (seperti dokumen `A-Starry-Sky` / `a-restless-ocean` yang berukuran ~35–60 KB) dalam satu kali penyelesaian adalah risiko reliabilitas utama pada model lokal: token output atau konteks bisa habis di tengah jalan dan bagian akhirnya terpotong secara diam-diam. Mode `pipeline` dirancang untuk menghindari hal tersebut:

- **Dirancang tanpa tool.** Model hanya menghasilkan teks biasa — setiap terjemahan, penulisan ulang, dan halaman direktori dikembalikan sebagai balasannya, dan orchestrator menyimpannya sendiri melalui tool `write_readme` / `write_directory_readme` milik server. Tidak ada yang meminta model untuk memasukkan seluruh dokumen ke dalam argumen pemanggilan tool. Pada model *reasoning* lokal (misalnya Gemma 4), jalur tersebut akan memotong JSON argumen dan endpoint akan menolaknya dengan kesalahan `peg-gemma4 format` / output malformed; mengembalikan teks biasa menghindari masalah ini sepenuhnya.
- **`max_tokens`** (default `32768`) dikirim secara eksplisit pada setiap penyelesaian sehingga satu bagian/draf penuh dapat selesai alih-alih terpotong oleh default per permintaan LM Studio yang lebih kecil. Pipeline akan memberi peringatan jika penyelesaian tetap berhenti karena `length`, sehingga Anda tahu harus menaikkan nilainya.
- **Pembagian Bagian (Section chunking)** — ketika sumber melebihi `chunk_threshold_chars` (default `12000`) dan `chunk_translation` bernilai `true`, sumber akan dibagi berdasarkan header Markdown tingkat atas (`## `) (sadar akan pembatas kode, sehingga `##` di dalam blok kode tidak akan diproses), setiap bagian diterjemahkan dalam penyelesaian tersendiri, dan orchestrator menyusun potongan-potongan tersebut lalu menyimpannya. Tidak ada satu pun panggilan model yang harus mengeluarkan seluruh dokumen sekaligus.
- **Peninjauan per Bagian** — dengan `review_sections` bernilai `true` (default), setiap bagian menjalankan siklus critique $\rightarrow$ revise yang sama dengan jalur single-shot, namun hanya terbatas pada bagian tersebut: peninjau membandingkan bagian yang diterjemahkan dengan sumbernya dan penulis merevisi hingga peninjau setuju (atau mencapai `MAX_ITERATIONS`). Karena satu bagian berukuran kecil, proses peninjauan dan penulisan ulang tetap berada jauh di bawah batas pemotongan yang membuat peninjauan seluruh dokumen pada README besar menjadi tidak aman.

Jalur chunked sengaja **tidak** menjalankan peninjauan seluruh dokumen kedua kalinya setelah selesai — mengeluarkan kembali seluruh README besar dalam satu penyelesaian akan memicu masalah pemotongan yang sama, dan proses per bagian sudah mencakup hal tersebut. Atur `review_sections` ke `false` untuk menerjemahkan dokumen besar tanpa peninjauan, atau `chunk_translation` ke `false` untuk memaksa perilaku single-shot asli (yang tetap menjalankan siklus peninjauan seluruh dokumen). Jalur single-shot di bawah ambang batas tidak berubah.