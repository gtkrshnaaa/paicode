Written in Indonesian

---

### **Panduan Setup Proyek: Pai Code**

Dokumen ini menjelaskan langkah-langkah yang diperlukan untuk melakukan persiapan dan instalasi lingkungan pengembangan proyek Pai Code.

#### **1. Struktur Direktori Proyek**

Proyek ini menggunakan struktur direktori sr untuk aplikasi Python guna memisahkan kode sumber dari file konfigurasi dan skrip eksekusi.

```
pai-code/
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── pai.py
│
└── pai_code/
    ├── __init__.py
    ├── agent.py
    ├── fs.py
    └── llm.py
```

**Deskripsi Komponen:**

*   `pai.py`: Titik masuk (entry point) aplikasi yang dieksekusi dari command line. Berfungsi untuk mem-parsing argumen dan memanggil logika dari paket `pai_code`.
*   `pai_code/`: Paket utama yang berisi seluruh logika inti aplikasi.
    *   `agent.py`: Modul yang berisi logika agent, termasuk pemrosesan tugas dan konstruksi prompt.
    *   `fs.py`: Modul yang berisi fungsi-fungsi untuk berinteraksi dengan file system (misalnya, membuat file, membaca file, membuat direktori).
    *   `llm.py`: Modul yang bertanggung jawab untuk komunikasi dengan Gemini API.
*   `requirements.txt`: File yang mendefinisikan semua dependensi (library) Python yang dibutuhkan oleh proyek.
*   `.env`: File untuk menyimpan variabel lingkungan, seperti kunci API. File ini tidak untuk dilacak oleh sistem kontrol versi.
*   `.gitignore`: File konfigurasi untuk Git yang menentukan file atau direktori mana yang harus diabaikan.

---

#### **2. Langkah-Langkah Instalasi**

Ikuti prosedur berikut untuk menyiapkan lingkungan pengembangan.

**Langkah 1: Inisialisasi Struktur Direktori**

Jalankan perintah berikut di terminal untuk membuat struktur direktori dan file yang diperlukan.

```bash
# Membuat direktori root dan masuk ke dalamnya
mkdir pai-code
cd pai-code

# Membuat direktori source code
mkdir pai_code

# Membuat file-file yang diperlukan
touch pai.py README.md requirements.txt .gitignore .env
touch pai_code/__init__.py pai_code/agent.py pai_code/fs.py pai_code/llm.py
```

**Langkah 2: Konfigurasi Virtual Environment**

Penggunaan virtual environment direkomendasikan untuk mengisolasi dependensi proyek dan menghindari konflik dengan paket Python sistem.

1.  **Buat virtual environment:**
    ```bash
    python3 -m venv venv
    ```
Bisa di jalankan di route project

2.  **Aktifkan virtual environment:**
    *   **Untuk macOS/Linux:**
        ```bash
        source pyvenv/bin/activate
        ```
    *   **Untuk Windows (Command Prompt/PowerShell):**
        ```bash
        .\venv\Scripts\activate
        ```
    Setelah aktif, nama environment (`venv`) akan muncul di awal baris prompt terminal.

**Langkah 3: Mendefinisikan Dependensi**

Buka file `requirements.txt` dan tambahkan konten berikut untuk mendaftarkan library yang akan digunakan.

```txt
# requirements.txt
google-generativeai
python-dotenv
```

**Langkah 4: Instalasi Dependensi**

Dengan virtual environment yang sudah aktif, eksekusi perintah di bawah ini untuk menginstal semua library yang terdaftar di `requirements.txt`.

```bash
pip install -r requirements.txt
```

**Langkah 5: Konfigurasi Kunci API**

Kunci API untuk layanan LLM disimpan dalam file `.env` agar tidak terekspos dalam kode sumber.

1.  Dapatkan kunci API dari Google AI Studio.
2.  Buka file `.env` dan tambahkan baris berikut, ganti nilai `YOUR_API_KEY_HERE` dengan kunci API.
    ```env
    # .env
    GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```

**Langkah 6: Konfigurasi Git Ignore**

Isi file `.gitignore` dengan konten berikut untuk memastikan file-file yang tidak relevan atau sensitif (seperti `.env` dan direktori `venv`) tidak termasuk dalam riwayat kontrol versi.

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

Setelah menyelesaikan semua langkah di atas, lingkungan pengembangan untuk proyek Pai Code telah siap. Kode program utama dapat mulai diimplementasikan pada file-file di dalam direktori `pai_code/`.