Written in Indonesian

---

### 1. Struktur Folder (Tree)

Struktur ini memisahkan kode utama aplikasi (`pai_code/`) dari skrip eksekusi, file konfigurasi, dan file pendukung lainnya.

```
pai-code/
├── .env                  # (JANGAN di-commit ke Git) Menyimpan API Key
├── .gitignore            # Daftar file/folder yang diabaikan oleh Git
├── README.md             # Deskripsi proyek dan cara penggunaan
├── requirements.txt      # Daftar library Python yang dibutuhkan
├── pai.py                # <<< ENTRY POINT: Skrip utama yang dijalankan dari terminal
│
└── pai_code/             # <<< SOURCE CODE: Paket utama berisi logika aplikasi
    ├── __init__.py       # Menandakan bahwa ini adalah sebuah Python package
    ├── agent.py          # Logika agent, konstruksi prompt, dan alur kerja
    ├── fs.py             # Fungsi-fungsi untuk operasi file system (baca, tulis, buat folder)
    └── llm.py            # Modul untuk berkomunikasi dengan Gemini API
```

**Penjelasan Singkat Setiap File/Folder:**

*   `pai-code/`: Folder root dari proyek kita.
*   `pai.py`: Ini adalah "pintu gerbang" aplikasi. File inilah yang akan kita panggil dari terminal (`python pai.py ...`). Tugasnya hanya mem-parsing argumen CLI dan memanggil fungsi yang relevan dari dalam paket `pai_code`.
*   `pai_code/`: Ini adalah "jantung" aplikasi. Semua logika inti ada di sini.
    *   `__init__.py`: File kosong yang membuat Python mengenali `pai_code/` sebagai sebuah modul yang bisa di-import.
    *   `agent.py`: Otak dari si Pai. Dia yang akan memutuskan apa yang harus dilakukan berdasarkan perintah.
    *   `fs.py`: "Tangan" dari si Pai. Isinya fungsi-fungsi seperti `create_file()`, `read_file()`, `create_directory()` yang berinteraksi langsung dengan file system.
    *   `llm.py`: "Mulut dan Telinga" si Pai. Modul ini khusus untuk mengirim prompt ke Gemini dan menerima responsnya.
*   `requirements.txt`: "Daftar belanjaan" untuk `pip`. Semua library eksternal yang kita butuhkan dicatat di sini.
*   `.env`: File rahasia untuk menyimpan kunci API Gemini. File ini tidak boleh di-upload ke GitHub.
*   `.gitignore`: "Daftar hitam" untuk Git. Kita akan suruh Git untuk mengabaikan file seperti `.env` dan folder `__pycache__`.

---

### 2. Setup Instalasi Kebutuhan

Sekarang, ayo kita siapkan semuanya agar bisa langsung *ngoding*. Ikuti langkah-langkah ini di terminalmu.

**Langkah 1: Buat Struktur Folder di Komputermu**

Kamu bisa membuat folder dan file di atas secara manual, atau gunakan perintah ini di terminal:

```bash
# Buat folder utama
mkdir pai-code
cd pai-code

# Buat folder source code
mkdir pai_code

# Buat file-file kosong
touch pai.py README.md requirements.txt .gitignore .env
touch pai_code/__init__.py pai_code/agent.py pai_code/fs.py pai_code/llm.py
```

**Langkah 2: Setup Virtual Environment (Sangat Direkomendasikan!)**

Ini akan mengisolasi library project kita dari library Python di sistem global.

```bash
# Buat virtual environment bernama 'venv'
python -m venv venv

# Aktifkan virtual environment
# Untuk macOS/Linux:
source venv/bin/activate

# Untuk Windows (Command Prompt/PowerShell):
.\venv\Scripts\activate
```
*Setelah aktif, kamu akan melihat `(venv)` di awal baris terminalmu.*

**Langkah 3: Isi File `requirements.txt`**

Buka file `requirements.txt` dan isikan nama library yang kita butuhkan. Kita butuh library Gemini dan satu lagi untuk membaca file `.env` dengan mudah.

```txt
# requirements.txt

google-generativeai
python-dotenv
```

**Langkah 4: Install Semua Kebutuhan**

Dengan virtual environment yang masih aktif, jalankan perintah ini:

```bash
pip install -r requirements.txt
```
Pip akan membaca file `requirements.txt` dan menginstall semua library yang terdaftar di sana.

**Langkah 5: Siapkan API Key di File `.env`**

1.  Dapatkan API Key kamu dari [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Buka file `.env` dan tambahkan baris berikut. Ganti `xxxxxxxx` dengan API key kamu.

```env
# .env

GEMINI_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Langkah 6: Isi File `.gitignore`**

Buka file `.gitignore` dan tambahkan konten ini. Ini akan mencegah file-file yang tidak perlu dan sensitif terkirim ke repository Git.

```gitignore
# .gitignore

# Virtual Environment
venv/
*.venv

# Python cache
__pycache__/
*.pyc

# Environment variables
.env

# IDE/Editor specific
.idea/
.vscode/
```

---
