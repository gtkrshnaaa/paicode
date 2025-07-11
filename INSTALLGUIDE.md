Written in Indonesian

---

### **Panduan Instalasi dan Pengujian (Mode Pengembangan)**

Dokumen ini menjelaskan prosedur standar untuk menyiapkan lingkungan pengembangan proyek **Pai Code** serta cara menguji fungsionalitas intinya. Metode ini dirancang untuk developer yang akan bekerja langsung pada kode sumber.

**Prinsip Utama Mode Pengembangan:**
*   **Terisolasi:** Semua dependensi dan skrip terinstal di dalam *virtual environment* proyek dan tidak akan memengaruhi sistem Python global.
*   **Live Reload:** Perubahan yang dibuat pada kode sumber akan langsung aktif tanpa perlu instalasi ulang, berkat penggunaan mode "editable".
*   **Tanpa Modifikasi Sistem:** Tidak memerlukan perubahan pada file konfigurasi *shell* global seperti `.bashrc` atau `.zshrc`.

---

#### **Prasyarat**
Pastikan sistem Anda telah terpasang:
*   Python 3.9+
*   Git

---

#### **Langkah-Langkah Instalasi**

**Langkah 1: Dapatkan Kode Sumber**
Buka terminal dan kloning repositori proyek, lalu masuk ke direktori yang baru dibuat.
```bash
# Ganti <URL_REPOSITORI> dengan URL Git proyek Anda
git clone <URL_REPOSITORI> paicode
cd paicode
```

**Langkah 2: Inisialisasi dan Aktivasi Lingkungan Virtual**
Buat sebuah *virtual environment* bernama `venv` untuk mengisolasi dependensi proyek.
```bash
# Membuat virtual environment
python3 -m venv venv

# Mengaktifkan virtual environment
source venv/bin/activate
```
Setelah aktivasi berhasil, Anda akan melihat `(venv)` di awal baris prompt terminal Anda.

**Langkah 3: Instal Proyek dalam Mode Editable**
Dengan *virtual environment* yang sudah aktif, instal proyek menggunakan `pip`.
```bash
# Pastikan Anda berada di direktori root proyek (paicode/)
pip install -e .
```

**Langkah 4: Konfigurasi Kunci API**
Aplikasi memerlukan kunci API untuk berkomunikasi dengan layanan Gemini.
1.  Buat file `.env` di direktori root proyek.
    ```bash
    touch .env
    ```
2.  Buka file `.env` tersebut dan tambahkan kunci API Anda dengan format berikut:
    ```env
    GEMINI_API_KEY="GANTI_DENGAN_KUNCI_API_ANDA"
    ```

---

#### **Verifikasi Instalasi**
Untuk memastikan instalasi berhasil, ikuti langkah verifikasi berikut.
1.  **Aktifkan `venv`** di dalam direktori proyek jika belum aktif.
2.  Pindah ke direktori lain, misalnya ke *home directory* Anda (`cd ~`).
3.  Jalankan perintah `pai --help`. Jika menu bantuan muncul, instalasi berhasil.

---

### **Skenario Pengujian Fungsionalitas**

Setelah instalasi diverifikasi, jalankan skenario berikut untuk mencoba semua fitur utama Pai Code. Sebaiknya jalankan dari lokasi yang bersih, seperti *home directory* Anda (`~`).

**1. Membuat Direktori Proyek (`mkdir`)**
Buat sebuah direktori kerja baru untuk menampung hasil pengujian kita.
```bash
(venv) user@localhost:~$ pai mkdir proyek-coba
```
*   **Hasil:** Pesan konfirmasi pembuatan direktori akan muncul. Anda dapat memverifikasinya dengan perintah `ls`.

**2. Masuk ke Direktori dan Membuat File (`touch`)**
Pindah ke direktori yang baru dibuat dan gunakan `pai` untuk membuat sebuah file Python kosong.
```bash
(venv) user@localhost:~$ cd proyek-coba
(venv) user@localhost:~/proyek-coba$ pai touch kalkulator.py
```
*   **Hasil:** Sebuah file kosong bernama `kalkulator.py` akan dibuat di dalam direktori `proyek-coba`.

**3. Menulis Kode dengan AI (`write`)**
Minta agent untuk menulis kode sederhana ke dalam file yang baru dibuat.
```bash
(venv) user@localhost:~/proyek-coba$ pai write kalkulator.py "Buat sebuah fungsi Python bernama 'tambah' yang menerima dua argumen (a dan b) dan mengembalikan hasil penjumlahannya."
```
*   **Hasil:** Setelah proses "berpikir", agent akan menuliskan kode fungsi tersebut ke dalam `kalkulator.py`.

**4. Membaca Hasil Kerja AI (`read`)**
Verifikasi konten yang ditulis oleh agent tanpa perlu membuka editor teks.
```bash
(venv) user@localhost:~/proyek-coba$ pai read kalkulator.py
```
*   **Hasil:** Isi dari file `kalkulator.py` akan ditampilkan langsung di terminal Anda.

**5. Menguji Mode Otonom (Auto Mode / Talk Mode)**
Uji kemampuan *agentic AI* untuk bekerja secara kontekstual melalui sesi interaktif.

```bash
(venv) user@localhost:~/proyek-coba$ pai auto
```

* **Hasil:**

  1. Terminal akan masuk ke mode `auto` interaktif (prompt berubah menjadi `pai>`).
  2. Anda dapat memberikan perintah secara bertahap, misalnya:

     ```bash
     pai> buat file kalkulator.py dan isi fungsi tambah
     pai> tambahkan fungsi kurang
     pai> tampilkan isi file
     pai> buat file README.md untuk dokumentasi
     ```
  3. Setiap instruksi akan diproses dengan mempertimbangkan perintah sebelumnya dalam satu konteks terpadu.
  4. Semua interaksi sesi akan disimpan dalam `.pai_history/session.log` di dalam direktori proyek untuk keperluan kontekstualisasi lanjutan.
  5. Untuk keluar dari sesi, gunakan perintah `exit` atau `quit`.

* **Verifikasi:**

  * Gunakan perintah `ls`, `ls -a`, dan `pai read` untuk melihat perubahan file.
  * Buka file `.pai_history/session.log` untuk meninjau riwayat percakapan.


---

