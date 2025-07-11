Written in Indonesian

-----

# **Pai Code: Agentic AI CLI Coder**

-----

## **1. Pendahuluan Pai Code**

> *A command-line based agentic AI designed to assist in software development through direct file system interaction.*

**Pai Code** adalah sebuah **AI agent lokal** yang beroperasi melalui **Command Line Interface (CLI)**, berfungsi untuk memfasilitasi operasi pengembangan perangkat lunak secara langsung pada struktur file dalam suatu proyek. Agent ini tidak memiliki koneksi langsung dengan *text/code editor*, namun berinteraksi langsung dengan *file system*, sehingga perubahan yang dilakukan oleh agent akan segera terefleksi pada *editor* yang sedang digunakan.

### Visi

Membangun sebuah **AI coding companion** yang beroperasi secara lokal, memiliki inisiatif, dan mampu mendukung proses pengembangan perangkat lunak secara *real-time*, mulai dari inisialisasi struktur proyek, penulisan kode program, hingga pengelolaan file dan direktori.

-----

## **2. Struktur Direktori Proyek**

Proyek ini mengadopsi struktur direktori standar untuk aplikasi Python guna memisahkan kode sumber dari file konfigurasi dan *script eksekusi*.

```
pai-code/
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── makefile
│
└── pai_code/
    ├── __init__.py
    ├── agent.py
    ├── cli.py
    ├── fs.py
    └── llm.py
```

**Deskripsi Komponen Utama:**

  * `pai_code/`: Paket utama yang memuat seluruh **logika inti aplikasi**.
      * `cli.py`: Merupakan **entry point CLI** untuk eksekusi perintah `pai`.
      * `agent.py`: Modul ini berisi **logika agent**, termasuk pemrosesan *task* dan konstruksi *prompt* untuk mode `auto`.
      * `fs.py`: Modul yang menyediakan **fungsi-fungsi untuk berinteraksi dengan *file system*** (misalnya, membuat file, membaca file, membuat direktori, menghapus, memindahkan).
      * `llm.py`: Modul yang bertanggung jawab untuk **komunikasi dengan Gemini API**.
  * `requirements.txt`: File ini mendefinisikan semua **dependensi (library) Python** yang dibutuhkan oleh proyek.
  * `.env`: File untuk menyimpan **variabel lingkungan**, seperti *API key*. **File ini tidak boleh dilacak oleh sistem *version control* dan harus ditambahkan ke `.gitignore`.**
  * `.gitignore`: File konfigurasi Git yang menentukan file atau direktori mana yang **harus diabaikan**.
  * `makefile`: Berisi **skrip untuk *development utility***, seperti pembuatan daftar file proyek yang aman.

-----

## **3. Panduan Instalasi dan Pengujian (Development Mode)**

Dokumen ini menjelaskan prosedur standar untuk menyiapkan lingkungan pengembangan proyek **Pai Code** serta metode pengujian fungsionalitas intinya. Pendekatan ini dirancang khusus untuk *developer* yang akan bekerja langsung pada *source code*.

### Prinsip Utama *Development Mode*:

  * **Isolated:** Semua dependensi dan *script* diinstal di dalam *virtual environment* proyek dan tidak akan memengaruhi sistem Python global.
  * **Live Reload:** Perubahan yang dilakukan pada *source code* akan langsung aktif tanpa memerlukan instalasi ulang, berkat penggunaan mode "editable".
  * **No System Modification:** Tidak memerlukan perubahan pada file konfigurasi *global shell* seperti `.bashrc` atau `.zshrc`.

### Prasyarat

Pastikan sistem Anda telah terinstal:

  * **Python 3.9+**
  * **Git**

### Langkah-Langkah Instalasi

1.  **Mendapatkan *Source Code***
    Buka terminal Anda dan *clone* repositori proyek, kemudian navigasikan ke direktori yang baru dibuat.

    ```bash
    # Ganti <URL_REPOSITORI> dengan URL Git proyek
    git clone <URL_REPOSITORI> paicode
    cd paicode
    ```

2.  **Inisialisasi dan Aktivasi *Virtual Environment***
    Buatlah sebuah *virtual environment* bernama `venv` untuk mengisolasi dependensi proyek.

    ```bash
    # Membuat virtual environment
    python3 -m venv venv

    # Mengaktifkan virtual environment
    source venv/bin/activate
    ```

    Setelah aktivasi berhasil, Anda akan melihat `(venv)` di awal baris *terminal prompt* Anda.

3.  **Instalasi Proyek dalam Mode *Editable***
    Dengan *virtual environment* yang telah aktif, instal proyek menggunakan `pip`. Ini akan menginstal proyek dalam mode *editable* dan juga menginstal semua dependensi yang terdaftar di `pyproject.toml` atau `requirements.txt`.

    ```bash
    # Pastikan Anda berada di direktori root proyek (paicode/)
    pip install -e .
    ```

4.  **Konfigurasi *API Key***
    Aplikasi ini membutuhkan *API key* untuk berkomunikasi dengan layanan Gemini.

      * Buat file `.env` di direktori *root* proyek jika belum ada:
        ```bash
        touch .env
        ```
      * Buka file `.env` tersebut dan tambahkan *API key* Anda dengan format berikut (ganti `GANTI_DENGAN_KUNCI_API_ANDA` dengan *API key* Anda yang sebenarnya):
        ```env
        # .env
        GEMINI_API_KEY="GANTI_DENGAN_KUNCI_API_ANDA"
        ```
        Contoh isi `.env.example`:
        ```
        # .env
        GEMINI_API_KEY="YOUR_API_KEY_HERE"
        ```

5.  **Konfigurasi *Git Ignore***
    Isi file `.gitignore` dengan konten berikut untuk memastikan file-file yang tidak relevan atau sensitif (seperti `.env` dan direktori `venv`) tidak termasuk dalam riwayat *version control*.

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

    pai_code.egg-info

    z_project_list
    ```

### Verifikasi Instalasi

Untuk memastikan instalasi berhasil, ikuti langkah verifikasi berikut.

1.  **Aktifkan `venv`** di dalam direktori proyek jika belum aktif.
2.  Pindah ke direktori lain, misalnya ke *home directory* Anda (`cd ~`).
3.  Jalankan perintah `pai --help`. Jika menu bantuan muncul, instalasi dianggap berhasil.

-----

## **4. Skenario Pengujian Fungsionalitas**

Setelah instalasi diverifikasi, jalankan skenario berikut untuk menguji semua fitur utama Pai Code. Disarankan untuk menjalankan dari lokasi yang bersih, seperti *home directory* Anda (`~`).

### 1\. Membuat Direktori Proyek (`mkdir`)

Buatlah sebuah direktori kerja baru untuk menampung hasil pengujian.

```bash
(venv) user@localhost:~$ pai mkdir proyek-coba
```

  * **Hasil:** Pesan konfirmasi pembuatan direktori akan muncul. Anda dapat memverifikasinya dengan perintah `ls`.

### 2\. Masuk ke Direktori dan Membuat File (`touch`)

Navigasikan ke direktori yang baru dibuat dan gunakan `pai` untuk membuat sebuah file Python kosong.

```bash
(venv) user@localhost:~$ cd proyek-coba
(venv) user@localhost:~/proyek-coba$ pai touch kalkulator.py
```

  * **Hasil:** Sebuah file kosong bernama `kalkulator.py` akan dibuat di dalam direktori `proyek-coba`.

### 3\. Menulis Kode dengan AI (`write`)

Mintalah *agent* untuk menulis kode sederhana ke dalam file yang baru dibuat.

```bash
(venv) user@localhost:~/proyek-coba$ pai write kalkulator.py "Buat sebuah fungsi Python bernama 'tambah' yang menerima dua argumen (a dan b) dan mengembalikan hasil penjumlahannya."
```

  * **Hasil:** Setelah proses "berpikir", *agent* akan menuliskan kode fungsi tersebut ke dalam `kalkulator.py`.

### 4\. Membaca Hasil Kerja AI (`read`)

Verifikasi konten yang ditulis oleh *agent* tanpa perlu membuka *text editor*.

```bash
(venv) user@localhost:~/proyek-coba$ pai read kalkulator.py
```

  * **Hasil:** Isi dari file `kalkulator.py` akan ditampilkan langsung di terminal Anda.

### 5\. Menguji Mode Otonom (Auto Mode / Talk Mode)

Ujilah kemampuan *agentic AI* untuk bekerja secara kontekstual melalui sesi interaktif.

```bash
(venv) user@localhost:~/proyek-coba$ pai auto
```

  * **Hasil:**

    1.  Terminal akan masuk ke mode `auto` interaktif (*prompt* berubah menjadi `pai>`).
    2.  Anda dapat memberikan perintah secara bertahap, misalnya:
        ```bash
        pai> buat file kalkulator.py dan isi fungsi tambah
        pai> tambahkan fungsi kurang
        pai> tampilkan isi file
        pai> buat file README.md untuk dokumentasi
        ```
    3.  Setiap instruksi akan diproses dengan mempertimbangkan perintah sebelumnya dalam satu konteks terpadu.
    4.  Semua interaksi sesi akan disimpan dalam `.pai_history/session.log` di dalam direktori proyek untuk keperluan kontekstualisasi lanjutan.
    5.  Untuk keluar dari sesi, gunakan perintah `exit` atau `quit`.

  * **Verifikasi:**

      * Gunakan perintah `ls`, `ls -a`, dan `pai read` untuk melihat perubahan file.
      * Buka file `.pai_history/session.log` untuk meninjau riwayat percakapan.

-----

## **5. Mode Operasi**

Pai Code menyediakan dua mode operasi utama:

### 5.1. Manual Mode

Mode ini memungkinkan Anda untuk mengeksekusi perintah satu per satu secara langsung.

  * `pai touch <file.py>`
    → Membuat file kosong pada direktori aktif.
  * `pai mkdir <folder>`
    → Membuat subdirektori baru pada *root project*.
  * `pai read <file.py>`
    → Menampilkan isi file ke terminal.
  * `pai write <file.py> "<task>"`
    → Menuliskan kode ke dalam file berdasarkan *task* tertentu.
  * `pai rm <path>`
    → Menghapus file atau direktori.
  * `pai mv <source> <destination>`
    → Memindahkan atau mengganti nama file/direktori.
  * `pai tree [path]`
    → Melihat struktur direktori secara rekursif.

### 5.2. Auto Mode

  * `pai auto`
    → Agent akan memasuki **mode interaktif *stateful***, di mana pengguna dapat memberikan instruksi secara bertahap dalam satu sesi yang berkelanjutan.
    Dalam mode ini:
      * Setiap perintah pengguna dianggap sebagai lanjutan konteks dari instruksi sebelumnya.
      * Agent akan menyusun *prompt* berdasarkan histori percakapan selama sesi berjalan.
      * Seluruh riwayat perintah dan hasil eksekusi dicatat di dalam folder khusus `.pai_history/` pada direktori proyek.
      * Sesi dapat dihentikan dengan perintah `exit` atau `quit`.

#### Contoh Penggunaan `pai auto` dengan studi kasus

Berikut adalah skenario contoh untuk membuat sistem *login* sederhana menggunakan *agent*. Anda dapat memberikan instruksi secara bertahap seperti ini:

```bash
(venv) user@localhost:~/proyek-coba$ pai auto
Memasuki mode auto interaktif. Ketik 'exit' atau 'quit' untuk keluar.
pai> buat struktur folder dasar untuk proyek login, dengan folder 'app' dan file 'main.py' di dalamnya.
```

*Agent akan memproses dan melakukan aksi. Outputnya mungkin sebagai berikut:*

```
Agent telah membuat rencana berikut:
---------------------------------------
MKDIR::app
TOUCH::app/main.py
---------------------------------------
Success: Direktori berhasil dibuat: app
Success: File berhasil dibuat: app/main.py
```

Selanjutnya, instruksikan agent untuk menulis kode:

```bash
pai> di app/main.py, buat fungsi untuk login sederhana. Terima username dan password, jika 'admin' dan 'password123' maka berhasil.
```

*Agent akan memproses dan menuliskan kode. Outputnya:*

```
Agent telah membuat rencana berikut:
---------------------------------------
WRITE::app/main.py::Buat fungsi Python bernama 'login' yang menerima dua argumen (username dan password). Jika username adalah 'admin' dan password adalah 'password123', fungsi mengembalikan True, jika tidak, mengembalikan False.
---------------------------------------
Success: Konten berhasil ditulis ke: app/main.py
```

Untuk memverifikasi, Anda dapat menampilkan isi file tersebut:

```bash
pai> tampilkan isi file app/main.py
```

*Pai Code akan membaca dan menampilkan isi file:*

```
--- ISI FILE: app/main.py ---
def login(username, password):
    if username == "admin" and password == "password123":
        return True
    else:
        return False
-----------------------------
```

Terakhir, instruksikan agent untuk membuat file `README.md` singkat yang menjelaskan proyek ini:

```bash
pai> buat file README.md di root proyek, jelaskan ini adalah aplikasi login sederhana.
```

*Agent akan membuat dan menulis file:*

```
Agent telah membuat rencana berikut:
---------------------------------------
WRITE::README.md::Buat file README.md yang menjelaskan bahwa ini adalah aplikasi login sederhana yang dibuat menggunakan Pai Code.
---------------------------------------
Success: Konten berhasil ditulis ke: README.md
```

Setelah semua *task* selesai, Anda dapat keluar dari mode `auto`:

```bash
pai> exit
```

*Output:*

```
Sesi berakhir.
```

-----

## **6. *Use-case* Utama**

  * Melakukan *bootstrapping* proyek secara cepat melalui perintah tunggal.
  * Membantu *developer* menyusun struktur proyek, membuat file, dan menuliskan kode *boilerplate*.
  * Melakukan revisi kode melalui perintah terstruktur tanpa memerlukan *plugin* khusus.
  * Menjadi dasar pengembangan AI *assistant* berbasis terminal untuk pemrograman berbagai bahasa.

-----

## **7. Arsitektur Sistem**

```
CLI Entry (pai.py)
    ↓
argparse CLI parser
    ↓
agent.py → prompt construction & task logic
    ↓
llm.py → komunikasi dengan Gemini API
    ↓
fs.py → operasi terhadap filesystem (file & folder)
```

-----

## **8. Fitur v0.1 (Minimum Viable Features)**

| Perintah                      | Deskripsi                                                                    |
| :---------------------------- | :------------------------------------------------------------------------- |
| `pai touch <file>`            | Membuat file kosong.                                                       |
| `pai mkdir <folder>`          | Membuat folder baru di dalam *root project*. |
| `pai read <file>`             | Menampilkan isi file.                                                      |
| `pai write <file> "<task>"`   | Menuliskan kode ke dalam file berdasarkan *prompt*. |
| `pai auto`                    | Mode otomatis di mana agent bertindak secara bebas untuk menyelesaikan *task*. |
| `pai rm <path>`               | Menghapus file atau direktori.                                              |
| `pai mv <source> <destination>` | Memindahkan atau mengganti nama file/direktori.                             |
| `pai tree [path]`             | Melihat struktur direktori secara rekursif.                                 |

-----

## **9. *Prompt* Template (Contoh)**

Berikut adalah contoh struktur *prompt* yang digunakan oleh agent:

```
You are a self-driven coding assistant. Your task is:
"Create a simple login system in Python."

Feel free to create any files, write necessary code, and structure the project as needed.
```

-----

## **10. Teknologi yang Digunakan**

  * **Python 3.9+**
  * **Gemini API** (melalui library `google.generativeai`)
  * Modul standar Python: `argparse`, `os`, `pathlib`, `subprocess`

### Dependensi Python (`requirements.txt`)

```txt
google-generativeai
python-dotenv
```

### Konfigurasi Proyek (`pyproject.toml` snippet)

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pai-code"
version = "0.1.0"
authors = [
  { name="Nama Anda", email="email@anda.com" },
]
description = "A command-line based agentic AI for software development."
readme = "README.md"
requires-python = ">=3.9"
license = { text = "MIT License" }
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
dependencies = [
    "google-generativeai",
    "python-dotenv",
]

[project.scripts]
pai = "pai_code.cli:main"

[tool.setuptools]
packages = ["pai_code"]
```

-----

## **11. Karakteristik Utama**

  * Tidak memerlukan proses `init` — *agent* langsung beroperasi di dalam *root folder project* yang sudah ada.
  * Semua operasi dilakukan secara lokal tanpa bergantung pada *plugin*, GUI, atau integrasi eksternal.
  * Mampu bekerja dengan berbagai bahasa pemrograman (*language-agnostic*), namun untuk versi awal difokuskan pada Python.
  * Sifat *agent* adalah **stateless**, namun dapat dikembangkan menjadi **stateful** dengan fitur *memory* atau *task chaining*.

-----

## **12. *Roadmap* Pengembangan**

| Versi | Penambahan                                         |
| :---- | :------------------------------------------------- |
| v0.1  | Perintah dasar (touch, mkdir, read, write, auto).  |
| v0.2  | Pembacaan struktur folder project secara otomatis. |
| v0.3  | *Tracking* perubahan (*change history*) dan kemampuan *undo*. |
| v0.4  | *Multi-step execution: plan → act → reflect*.      |

-----

## **13. Alasan Proyek Layak untuk Studi Akademik**

  * Topik ini berkaitan langsung dengan pengembangan *agentic AI*, yang merupakan *frontier* riset AI terkini.
  * Implementasinya mencakup aspek interaksi AI–file system, *prompt engineering*, serta otomasi berbasis *Large Language Model*.
  * Sistem ini dapat dievaluasi berdasarkan keberhasilan *task*, akurasi *output* kode, serta efisiensi penggunaan *agent*.

-----

## **14. Penutup**

Pai Code diharapkan dapat menjadi fondasi pengembangan **agent coding system** yang ringan, fleksibel, dan praktis, terutama untuk digunakan dalam konteks pengembangan perangkat lunak berbasis terminal. Pendekatan ini membuka jalan bagi integrasi LLM ke dalam *developer workflow* secara alami, tanpa harus mengorbankan kontrol dan fleksibilitas.

-----

