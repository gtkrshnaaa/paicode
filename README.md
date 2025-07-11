Written in Indonesian

-----

# **Pai Code: Agentic AI CLI Coder**

-----

## ✦ **Tentang Pai Code**

> *A command-line based agentic AI designed to assist in software development through direct file system interaction.*

**Pai Code** merupakan sebuah **AI agent lokal** yang dijalankan melalui **Command Line Interface (CLI)** dan berfungsi untuk melakukan operasi pengembangan perangkat lunak secara langsung terhadap struktur file dalam sebuah proyek. Agent ini tidak terhubung secara langsung dengan *text/code editor*, namun bekerja melalui interaksi langsung dengan *file system*, sehingga perubahan yang dilakukan oleh agent dapat segera terlihat di editor manapun yang digunakan.

### Visi

Membangun sebuah **AI coding companion** yang berjalan secara lokal, dapat berinisiatif, dan mampu mendukung proses pengembangan perangkat lunak secara *real-time*, mulai dari pembuatan struktur proyek, penulisan kode program, hingga pengelolaan file dan direktori.

-----

## ✦ **Struktur Direktori Proyek**

Proyek ini menggunakan struktur direktori `src` untuk aplikasi Python guna memisahkan kode sumber dari file konfigurasi dan skrip eksekusi.

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

  * `pai_code/`: Paket utama yang berisi seluruh logika inti aplikasi.
      * `cli.py`: *Entry point* CLI untuk menjalankan perintah `pai`.
      * `agent.py`: Modul yang berisi logika agent, termasuk pemrosesan tugas dan konstruksi *prompt* untuk mode `auto`.
      * `fs.py`: Modul yang berisi fungsi-fungsi untuk berinteraksi dengan *file system* (misalnya, membuat file, membaca file, membuat direktori, menghapus, memindahkan).
      * `llm.py`: Modul yang bertanggung jawab untuk komunikasi dengan Gemini API.
  * `requirements.txt`: File yang mendefinisikan semua dependensi (library) Python yang dibutuhkan oleh proyek.
  * `.env`: File untuk menyimpan variabel lingkungan, seperti kunci API. **File ini tidak untuk dilacak oleh sistem kontrol versi dan harus ditambahkan ke `.gitignore`.**
  * `.gitignore`: File konfigurasi untuk Git yang menentukan file atau direktori mana yang harus diabaikan.
  * `makefile`: Berisi skrip untuk *utility* pengembangan, seperti membuat daftar file proyek yang aman.

-----

## ✦ **Panduan Instalasi dan Pengujian (Mode Pengembangan)**

Dokumen ini menjelaskan prosedur standar untuk menyiapkan lingkungan pengembangan proyek **Pai Code** serta cara menguji fungsionalitas intinya. Metode ini dirancang untuk *developer* yang akan bekerja langsung pada kode sumber.

### Prinsip Utama Mode Pengembangan:

  * **Terisolasi:** Semua dependensi dan skrip terinstal di dalam *virtual environment* proyek dan tidak akan memengaruhi sistem Python global.
  * **Live Reload:** Perubahan yang dibuat pada kode sumber akan langsung aktif tanpa perlu instalasi ulang, berkat penggunaan mode "editable".
  * **Tanpa Modifikasi Sistem:** Tidak memerlukan perubahan pada file konfigurasi *shell* global seperti `.bashrc` atau `.zshrc`.

### Prasyarat

Pastikan sistemmu telah terpasang:

  * **Python 3.9+**
  * **Git**

### Langkah-Langkah Instalasi

1.  **Dapatkan Kode Sumber**
    Buka terminal dan kloning repositori proyek, lalu masuk ke direktori yang baru dibuat.

    ```bash
    # Ganti <URL_REPOSITORI> dengan URL Git proyek Anda
    git clone <URL_REPOSITORI> paicode
    cd paicode
    ```

2.  **Inisialisasi dan Aktivasi Lingkungan Virtual**
    Buat sebuah *virtual environment* bernama `venv` untuk mengisolasi dependensi proyek.

    ```bash
    # Membuat virtual environment
    python3 -m venv venv

    # Mengaktifkan virtual environment
    source venv/bin/activate
    ```

    Setelah aktivasi berhasil, kamu akan melihat `(venv)` di awal baris *prompt* terminalmu.

3.  **Instal Proyek dalam Mode Editable**
    Dengan *virtual environment* yang sudah aktif, instal proyek menggunakan `pip`. Ini akan menginstal proyek dalam mode *editable* dan juga menginstal semua dependensi yang terdaftar di `pyproject.toml` atau `requirements.txt`.

    ```bash
    # Pastikan kamu berada di direktori root proyek (paicode/)
    pip install -e .
    ```

4.  **Konfigurasi Kunci API**
    Aplikasi memerlukan kunci API untuk berkomunikasi dengan layanan Gemini.

      * Buat file `.env` di direktori *root* proyek jika belum ada:
        ```bash
        touch .env
        ```
      * Buka file `.env` tersebut dan tambahkan kunci API-mu dengan format berikut (ganti `GANTI_DENGAN_KUNCI_API_ANDA` dengan kunci API-mu yang sebenarnya):
        ```env
        # .env
        GEMINI_API_KEY="GANTI_DENGAN_KUNCI_API_ANDA"
        ```
        Contoh isi `.env.example`:
        ```
        # .env
        GEMINI_API_KEY="YOUR_API_KEY_HERE"
        ```

5.  **Konfigurasi Git Ignore**
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

    pai_code.egg-info

    z_project_list
    ```

### Verifikasi Instalasi

Untuk memastikan instalasi berhasil, ikuti langkah verifikasi berikut.

1.  **Aktifkan `venv`** di dalam direktori proyek jika belum aktif.
2.  Pindah ke direktori lain, misalnya ke *home directory* kamu (`cd ~`).
3.  Jalankan perintah `pai --help`. Jika menu bantuan muncul, instalasi berhasil.

-----

## ✦ **Skenario Pengujian Fungsionalitas**

Setelah instalasi diverifikasi, jalankan skenario berikut untuk mencoba semua fitur utama Pai Code. Sebaiknya jalankan dari lokasi yang bersih, seperti *home directory* kamu (`~`).

### 1\. Membuat Direktori Proyek (`mkdir`)

Buat sebuah direktori kerja baru untuk menampung hasil pengujian kita.

```bash
(venv) user@localhost:~$ pai mkdir proyek-coba
```

  * **Hasil:** Pesan konfirmasi pembuatan direktori akan muncul. Kamu dapat memverifikasinya dengan perintah `ls`.

### 2\. Masuk ke Direktori dan Membuat File (`touch`)

Pindah ke direktori yang baru dibuat dan gunakan `pai` untuk membuat sebuah file Python kosong.

```bash
(venv) user@localhost:~$ cd proyek-coba
(venv) user@localhost:~/proyek-coba$ pai touch kalkulator.py
```

  * **Hasil:** Sebuah file kosong bernama `kalkulator.py` akan dibuat di dalam direktori `proyek-coba`.

### 3\. Menulis Kode dengan AI (`write`)

Minta *agent* untuk menulis kode sederhana ke dalam file yang baru dibuat.

```bash
(venv) user@localhost:~/proyek-coba$ pai write kalkulator.py "Buat sebuah fungsi Python bernama 'tambah' yang menerima dua argumen (a dan b) dan mengembalikan hasil penjumlahannya."
```

  * **Hasil:** Setelah proses "berpikir", *agent* akan menuliskan kode fungsi tersebut ke dalam `kalkulator.py`.

### 4\. Membaca Hasil Kerja AI (`read`)

Verifikasi konten yang ditulis oleh *agent* tanpa perlu membuka editor teks.

```bash
(venv) user@localhost:~/proyek-coba$ pai read kalkulator.py
```

  * **Hasil:** Isi dari file `kalkulator.py` akan ditampilkan langsung di terminalmu.

### 5\. Menguji Mode Otonom (Auto Mode / Talk Mode)

Uji kemampuan *agentic AI* untuk bekerja secara kontekstual melalui sesi interaktif.

```bash
(venv) user@localhost:~/proyek-coba$ pai auto
```

  * **Hasil:**

    1.  Terminal akan masuk ke mode `auto` interaktif (*prompt* berubah menjadi `pai>`).
    2.  Kamu dapat memberikan perintah secara bertahap, misalnya:
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

## ✦ **Mode Operasi**

Pai Code memiliki dua mode operasi utama:

### 1\. Manual Mode

Mode ini memungkinkan kamu untuk menjalankan perintah satu per satu secara langsung.

  * `pai touch <file.py>`
    → Membuat file kosong pada direktori aktif
  * `pai mkdir <folder>`
    → Membuat subdirektori baru pada *root project*
  * `pai read <file.py>`
    → Menampilkan isi file ke terminal
  * `pai write <file.py> "<task>"`
    → Menuliskan kode ke dalam file berdasarkan *task* tertentu
  * `pai rm <path>`
    → Menghapus file atau direktori
  * `pai mv <source> <destination>`
    → Memindahkan atau mengganti nama file/direktori
  * `pai tree [path]`
    → Melihat struktur direktori secara rekursif

### 2\. Auto Mode

  * `pai auto`
    → Agent memasuki **mode interaktif *stateful***, di mana pengguna dapat memberikan instruksi secara bertahap dalam satu sesi yang berkelanjutan.
    Dalam mode ini:
      * Setiap perintah pengguna dianggap sebagai lanjutan konteks dari instruksi sebelumnya
      * Agent akan menyusun *prompt* berdasarkan histori percakapan selama sesi berjalan
      * Seluruh riwayat perintah dan hasil dieksekusi dicatat di dalam folder khusus `.pai_history/` pada direktori proyek
      * Sesi dapat dihentikan dengan perintah `exit` atau `quit`



#### Contoh Penggunaan `pai auto`

Untuk memulai sesi interaktif dengan Pai Code dalam mode otonom, cukup jalankan perintah `pai auto` di terminalmu dari *root* direktori proyek:

```bash
(venv) user@localhost:~/proyek-coba$ pai auto
Memasuki mode auto interaktif. Ketik 'exit' atau 'quit' untuk keluar.
pai>
```

Setelah `pai>` muncul, kamu bisa mulai memberikan instruksi. Agent akan memprosesnya secara berurutan dan mengingat konteks dari perintah sebelumnya.

-----

##### Skenario: Membuat Sistem Login Sederhana

Mari kita coba membuat sistem login sederhana dengan *agent*. Kamu bisa berikan instruksi bertahap seperti ini:

```bash
pai> buat struktur folder dasar untuk proyek login, dengan folder 'app' dan file 'main.py' di dalamnya.
```

*Agent akan berpikir dan melakukan aksi. Outputnya mungkin seperti ini:*

```
Agent telah membuat rencana berikut:
---------------------------------------
MKDIR::app
TOUCH::app/main.py
---------------------------------------
Success: Direktori berhasil dibuat: app
Success: File berhasil dibuat: app/main.py
```

Lanjut, kita minta dia menulis kode:

```bash
pai> di app/main.py, buat fungsi untuk login sederhana. Terima username dan password, jika 'admin' dan 'password123' maka berhasil.
```

*Agent akan memproses dan menulis kode. Outputnya:*

```
Agent telah membuat rencana berikut:
---------------------------------------
WRITE::app/main.py::Buat fungsi Python bernama 'login' yang menerima dua argumen (username dan password). Jika username adalah 'admin' dan password adalah 'password123', fungsi mengembalikan True, jika tidak, mengembalikan False.
---------------------------------------
Success: Konten berhasil ditulis ke: app/main.py
```

Sekarang, kita bisa cek isi file tersebut:

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

Terakhir, kita minta dia membuat file `README.md` singkat untuk menjelaskan proyek ini:

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

Setelah selesai, kamu bisa keluar dari mode `auto`:

```bash
pai> exit
```

*Output:*

```
Sesi berakhir.
```

-----

##### Verifikasi Setelah Sesi `auto`

Setelah keluar dari sesi `pai auto`, kamu bisa verifikasi perubahan yang sudah dilakukan:

1.  **Cek struktur direktori:**

    ```bash
    (venv) user@localhost:~/proyek-coba$ ls -F
    app/  README.md
    ```

2.  **Cek isi file `README.md`:**

    ```bash
    (venv) user@localhost:~/proyek-coba$ cat README.md
    ```

    *Outputnya akan berisi deskripsi yang dibuat oleh agent.*

3.  **Cek riwayat sesi:**
    Agent akan menyimpan log interaksi di direktori `.pai_history/` di dalam proyekmu.

    ```bash
    (venv) user@localhost:~/proyek-coba$ ls -a .pai_history/
    session_YYYYMMDD_HHMMSS.log
    ```

    Kamu bisa melihat isi lognya dengan `cat .pai_history/session_YYYYMMDD_HHMMSS.log`.

-----

## ✦ ***Use-case* Utama**

  * Melakukan *bootstrapping* terhadap sebuah proyek secara cepat melalui perintah tunggal.
  * Membantu *developer* menyusun struktur proyek, membuat file, dan menuliskan kode *boilerplate*.
  * Melakukan revisi kode melalui perintah terstruktur tanpa memerlukan *plugin* khusus.
  * Menjadi dasar pengembangan AI *assistant* berbasis terminal untuk pemrograman berbagai bahasa.

-----

## ✦ **Arsitektur Sistem**

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

## ✦ **Fitur v0.1 (Minimum Viable Features)**

| Perintah                      | Deskripsi                                                                    |
| :---------------------------- | :------------------------------------------------------------------------- |
| `pai touch <file>`            | Membuat file kosong                                                        |
| `pai mkdir <folder>`          | Membuat folder baru di dalam *root project* |
| `pai read <file>`             | Menampilkan isi file                                                       |
| `pai write <file> "<task>"`   | Menuliskan kode ke dalam file berdasarkan *prompt* |
| `pai auto`                    | Mode otomatis di mana agent bertindak secara bebas untuk menyelesaikan *task* |
| `pai rm <path>`               | Menghapus file atau direktori                                              |
| `pai mv <source> <destination>` | Memindahkan atau mengganti nama file/direktori                             |
| `pai tree [path]`             | Melihat struktur direktori secara rekursif                                 |

-----

## ✦ ***Prompt* Template (Contoh)**

Berikut adalah contoh struktur *prompt* yang digunakan oleh agent:

```
You are a self-driven coding assistant. Your task is:
"Create a simple login system in Python."

Feel free to create any files, write necessary code, and structure the project as needed.
```

-----

## ✦ **Teknologi yang Digunakan**

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
```

-----

## ✦ **Karakteristik Utama**

  * Tidak memerlukan proses `init` — *agent* langsung dijalankan di dalam *root folder project* yang sudah ada.
  * Semua operasi dilakukan secara lokal tanpa tergantung pada *plugin*, GUI, atau integrasi eksternal.
  * Dapat bekerja dengan berbagai bahasa pemrograman (*language-agnostic*), namun untuk versi awal difokuskan pada Python.
  * Sifat *agent* adalah **stateless**, namun dapat dikembangkan menjadi **stateful** dengan fitur *memory* atau *task chaining*.

-----

## ✦ ***Roadmap* Pengembangan**

| Versi | Penambahan                                         |
| :---- | :------------------------------------------------- |
| v0.1  | Perintah dasar (touch, mkdir, read, write, auto)   |
| v0.2  | Pembacaan struktur folder project secara otomatis  |
| v0.3  | *Tracking* perubahan (*change history*) dan kemampuan *undo* |
| v0.4  | *Multi-step execution: plan → act → reflect* |

-----

## ✦ **Alasan Proyek Layak untuk Studi Akademik**

  * Topik berkaitan langsung dengan pengembangan *agentic AI*, yang merupakan *frontier* riset AI terkini.
  * Implementasi mencakup aspek interaksi AI–file system, *prompt engineering*, serta otomasi berbasis *Large Language Model*.
  * Sistem dapat dievaluasi berdasarkan keberhasilan *task*, keakuratan *output* kode, serta efisiensi penggunaan *agent*.

-----

## ✦ **Penutup**

Pai Code diharapkan dapat menjadi fondasi pengembangan **agent coding system** yang ringan, fleksibel, dan praktis, terutama untuk digunakan dalam konteks pengembangan perangkat lunak berbasis terminal. Pendekatan ini membuka jalan bagi integrasi LLM ke dalam *developer workflow* secara alami, tanpa harus mengorbankan kontrol dan fleksibilitas.

-----

