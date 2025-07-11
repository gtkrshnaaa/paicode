Written in Indonesian

---

# **Concept Book – Pai Code: Agentic AI CLI Coder**

---

## ✦ **Pai Code**

> *A command-line based agentic AI designed to assist in software development through direct file system interaction.*

---

## ✦ Deskripsi Singkat

**Pai Code** merupakan sebuah **AI agent lokal** yang dijalankan melalui **Command Line Interface (CLI)** dan berfungsi untuk melakukan operasi pengembangan perangkat lunak secara langsung terhadap struktur file dalam sebuah project. Agent ini tidak terhubung secara langsung dengan text/code editor, namun bekerja melalui interaksi langsung dengan file system, sehingga perubahan yang dilakukan oleh agent dapat segera terlihat di editor manapun yang digunakan.

---

## ✦ Visi

Membangun sebuah **AI coding companion** yang berjalan secara lokal, dapat berinisiatif, dan mampu mendukung proses pengembangan perangkat lunak secara real-time, mulai dari pembuatan struktur proyek, penulisan kode program, hingga pengelolaan file dan direktori.

---

## ✦ Mode Operasi

1. **Manual Mode**

   * `pai touch <file.py>`
     → Membuat file kosong pada direktori aktif
   * `pai mkdir <folder>`
     → Membuat subdirektori baru pada root project
   * `pai read <file.py>`
     → Menampilkan isi file ke terminal
   * `pai write <file.py> "<task>"`
     → Menuliskan kode ke dalam file berdasarkan task tertentu

2. **Auto Mode**

   * `pai auto`
     → Agent memasuki **mode interaktif stateful**, di mana pengguna dapat memberikan instruksi secara bertahap dalam satu sesi yang berkelanjutan.
     Dalam mode ini:

     * Setiap perintah pengguna dianggap sebagai lanjutan konteks dari instruksi sebelumnya

     * Agent akan menyusun prompt berdasarkan histori percakapan selama sesi berjalan

     * Seluruh riwayat perintah dan hasil dieksekusi dicatat di dalam folder khusus `.pai_history/` pada direktori proyek

     * Sesi dapat dihentikan dengan perintah `exit` atau `quit`

   > Contoh interaksi:

   ```bash
   $ pai auto
   pai> buat file kalkulator.py dan isi fungsi tambah
   pai> tambahkan validasi input untuk angka negatif
   pai> tampilkan isi file tersebut
   ```

---

## ✦ Use-case Utama

* Melakukan *bootstrapping* terhadap sebuah proyek secara cepat melalui perintah tunggal
* Membantu developer menyusun struktur proyek, membuat file, dan menuliskan kode boilerplate
* Melakukan revisi kode melalui perintah terstruktur tanpa memerlukan plugin khusus
* Menjadi dasar pengembangan AI assistant berbasis terminal untuk pemrograman berbagai bahasa

---

## ✦ Arsitektur Sistem

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

---

## ✦ Fitur v0.1 (Minimum Viable Features)

| Perintah                    | Deskripsi                                                                   |
| --------------------------- | --------------------------------------------------------------------------- |
| `pai touch <file>`          | Membuat file kosong                                                         |
| `pai mkdir <folder>`        | Membuat folder baru di dalam root project                                   |
| `pai read <file>`           | Menampilkan isi file                                                        |
| `pai write <file> "<task>"` | Menuliskan kode ke dalam file berdasarkan prompt                            |
| `pai auto "<task>"`         | Mode otomatis di mana agent bertindak secara bebas untuk menyelesaikan task |

---

## ✦ Prompt Template (Contoh)

```
You are a self-driven coding assistant. Your task is:
"Create a simple login system in Python."

Feel free to create any files, write necessary code, and structure the project as needed.
```

---

## ✦ Teknologi yang Digunakan

* **Python 3.9+**
* **Gemini API** (melalui library `google.generativeai`)
* Modul standar Python: `argparse`, `os`, `pathlib`, `subprocess`

---

## ✦ Karakteristik Utama

* Tidak memerlukan proses `init` — agent langsung dijalankan di dalam root folder project yang sudah ada
* Semua operasi dilakukan secara lokal tanpa tergantung pada plugin, GUI, atau integrasi eksternal
* Dapat bekerja dengan berbagai bahasa pemrograman (language-agnostic), namun untuk versi awal difokuskan pada Python
* Sifat agent adalah **stateless**, namun dapat dikembangkan menjadi **stateful** dengan fitur memory atau task chaining

---

## ✦ Roadmap Pengembangan

| Versi | Penambahan                                             |
| ----- | ------------------------------------------------------ |
| v0.1  | Perintah dasar (touch, mkdir, read, write, auto)       |
| v0.2  | Pembacaan struktur folder project secara otomatis      |
| v0.3  | Tracking perubahan (change history) dan kemampuan undo |
| v0.4  | Multi-step execution: plan → act → reflect             |

---

## ✦ Alasan Proyek Layak untuk Studi Akademik

* Topik berkaitan langsung dengan pengembangan *agentic AI*, yang merupakan frontier riset AI terkini
* Implementasi mencakup aspek interaksi AI–file system, prompt engineering, serta otomasi berbasis Large Language Model
* Sistem dapat dievaluasi berdasarkan keberhasilan task, keakuratan output kode, serta efisiensi penggunaan agent

---

## ✦ Penutup

Pai Code diharapkan dapat menjadi fondasi pengembangan **agent coding system** yang ringan, fleksibel, dan praktis, terutama untuk digunakan dalam konteks pengembangan perangkat lunak berbasis terminal. Pendekatan ini membuka jalan bagi integrasi LLM ke dalam *developer workflow* secara alami, tanpa harus mengorbankan kontrol dan fleksibilitas.

---


