# comprehend-markdown

*Kau sentuh gulungan itu dan ucapkan mantra rahasianya. Beberapa menit hingga satu jam kemudian (tergantung ketebalan gulungannya), kau akan memahami Markdown dalam bahasa apa pun.*

Sebuah server MCP yang menerjemahkan `README.md` sebuah proyek ke dalam bahasa lain, serta pipeline mandiri yang menjalankan loop penulis/peninjau terhadap dokumen tersebut menggunakan model LM Studio lokal.

Bahasa sumber dan target keduanya dapat dikonfigurasi — Bahasa Inggris hanyalah setelan bawaan. Atur `source_language` untuk menerjemahkan *dari* bahasa Mandarin, Indonesia, atau bahasa lainnya, dan `target_languages` untuk memilih bahasa tujuan terjemahannya (lihat [Memilih bahasa sumber dan target](#memilih-bahasa-sumber-dan-target)).

Untuk proyek target apa pun, sistem ini mengharapkan (dan akan membuat jika diperlukan):

```
<akar-proyek>/docs/<sumber>/README.md  sumber kanonik (default: Bahasa Inggris)
<akar-proyek>/docs/<bahasa>/README.md    versi terjemahan, satu per bahasa
<akar-proyek>/README.md                halaman arahan pemilih bahasa (dihasilkan otomatis)
```

Proyek yang belum dimigrasi — di mana sumbernya masih berada di akar direktori — juga tetap bisa diproses: `README.md` di akar akan digunakan sebagai sumber, dan pada akhir proses `pipeline`, file tersebut akan dipindahkan ke `docs/<sumber>/` (misalnya `docs/English/`) dan digantikan oleh halaman arahan singkat yang menautkan setiap terjemahan yang tersedia.

## Setup

Semua hal (pembuatan venv, instalasi/sinkronisasi dependensi) ditangani oleh `run.sh` — tidak ada langkah instalasi terpisah. Skrip ini membaca paket dari `requirements.txt` dan menginstalnya kembali pada setiap kali dijalankan, jadi untuk memperbarui dependensi cukup dengan menjalankannya kembali.

Jika Anda ingin menggunakan model LM Studio lokal selain model bawaan, ubah nilai yang ada di `config.json`.

### Memilih bahasa sumber dan target

Dua kunci konfigurasi dalam `config.json` mengontrol arah penerjemahan:

- **`source_language`** — bahasa yang digunakan untuk menulis `README.md` kanonik Anda, sekaligus nama folder `docs/<source_language>/`. Defaultnya adalah `English`. Atur menjadi `中文`, `Indonesia`, atau bahasa lainnya untuk menerjemahkan *dari* bahasa tersebut.
- **`target_languages`** — daftar bahasa tujuan terjemahan pipeline. Entri apa pun yang sama dengan `source_language` akan dilewati secara otomatis, jadi membiarkan bahasa sumber tetap ada di dalam daftar tidak akan menimbulkan masalah.

Sebagai contoh, untuk menerjemahkan README bahasa Mandarin ke dalam bahasa Inggris dan Spanyol:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Jika `target_languages` dikosongkan, pipeline akan menggunakan daftar bawaan yang terdiri dari 18 bahasa.

`api_key` hanya berpengaruh jika Anda mengaktifkan "Require API Key" pada pengaturan server Developer di LM Studio — jika tidak, biarkan tetap `"lm-studio"`, karena LM Studio akan mengabaikannya. Perlu dicatat bahwa ini hanya berlaku untuk mode `pipeline`, satu-satunya bagian yang memanggil endpoint kompatibel OpenAI milik LM Studio secara langsung; mode `serve` tidak pernah berkomunikasi dengan API LM Studio itu sendiri karena LM Studio *adalah* klien MCP yang memanggilnya.

`max_tokens` dapat diatur di sini, namun saya tidak yakin apakah LM Studio benar-benar mematuhinya atau tidak. Pastikan untuk mengatur nilai ini setidaknya sekitar 24576 pada model itu sendiri sebelum menjalankan skrip ini.

## Penggunaan

```bash
./run.sh serve    /jalur/absolut/ke/proyek   # server MCP stdio
./run.sh pipeline /jalur/absolut/ke/proyek   # menjalankan main.py secara end-to-end
```

Kedua mode tersebut memerlukan jalur **absolut** ke folder proyek yang berisi `README.md` yang akan diterjemahkan. Dalam mode `pipeline`, Anda dapat mengosongkannya dan akan diminta memasukkannya kemudian, asalkan Anda menjalankannya secara interaktif di terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /jalur/absolut/ke/proyek
```

(Mode `serve` tidak pernah meminta input — setelah dimulai, stdin/stdout menjadi saluran JSON-RPC MCP itu sendiri, dan host MCP meluncurkannya secara non-interaktif.)

### `serve` — sebagai alat host MCP

Inilah yang harus dituju oleh `command` server pada host MCP (misalnya LM Studio), dengan jalur absolut proyek target sebagai argumen tetap. Server ini menyediakan:

- **tool** `write_readme(language, content)` (menulis file `docs/<language>/README.md`)
- **tool** `write_directory_readme(content)` (menulis file `README.md` di akar/halaman pemilih bahasa)
- **resource** `docs://readme` (sumber utama: `docs/<source_language>/README.md`, atau fallback ke `README.md` di akar)
- **resource** `docs://readme/{language}` (terjemahan yang sudah ada, jika tersedia)
- **resource** `docs://dir_readme` (file `README.md` di akar)
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` (loop penerjemahan baru)
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` (alur pembaruan: membandingkan terjemahan yang ada dengan sumber terbaru dan memperbaikinya dengan perubahan minimal)
- **prompt** `create_docs_language_directory` (membangun halaman pemilih bahasa di akar dari daftar terjemahan yang tersedia)

Model milik host-lah yang menggerakkan panggilan tool; server ini hanya menyediakan I/O file dan templat prompt.

#### Menambahkannya ke LM Studio

Konfigurasi MCP LM Studio berada di `~/.lmstudio/mcp.json`. Tambahkan entri seperti berikut:

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/jalur/absolut/ke/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/jalur/absolut/ke/proyek/yang/ingin/diterjemahkan"
      ]
    }
  }
}
```

Entri `args` kedua ditetapkan saat koneksi — konfigurasi LM Studio adalah JSON statis tanpa dukungan prompt interaktif, jadi itu harus berupa jalur aktual dari proyek yang ingin Anda terjemahkan, bukan jalur repositori ini (kecuali jika repositori inilah proyek yang ingin Anda terjemahkan).