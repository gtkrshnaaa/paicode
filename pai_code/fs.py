# pai_code/fs.py

import os

def create_file(file_path: str):
    """Membuat sebuah file kosong jika belum ada."""
    try:
        # Hanya buat direktori jika nama direktorinya ada (tidak kosong)
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        with open(file_path, 'w') as f:
            pass
        print(f"File berhasil dibuat: {file_path}")
    except IOError as e:
        print(f"Gagal membuat file: {e}")

def create_directory(dir_path: str):
    """Membuat sebuah direktori baru."""
    try:
        os.makedirs(dir_path, exist_ok=True)
        print(f"Direktori berhasil dibuat: {dir_path}")
    except OSError as e:
        print(f"Gagal membuat direktori: {e}")

def read_file(file_path: str) -> str | None:
    """Membaca dan menampilkan isi file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            print(f"--- ISI FILE: {file_path} ---")
            print(content)
            print("-----------------------------")
            return content
    except FileNotFoundError:
        print(f"File tidak ditemukan: {file_path}")
        return None
    except IOError as e:
        print(f"Gagal membaca file: {e}")
        return None

def write_to_file(file_path: str, content: str):
    """Menulis atau menimpa konten ke dalam sebuah file."""
    try:
        # Logika yang sama diterapkan di sini
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Konten berhasil ditulis ke: {file_path}")
    except IOError as e:
        print(f"Gagal menulis ke file: {e}")