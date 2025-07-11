# pai_code/fs.py

import os
import shutil

# --- SANDBOXING: ---
# Menetapkan direktori root proyek saat aplikasi pertama kali dijalankan.
# Ini adalah "kotak" kita.
PROJECT_ROOT = os.path.abspath(os.getcwd())

def _is_path_safe(path: str) -> bool:
    """
    Memeriksa apakah sebuah path berada di dalam PROJECT_ROOT.
    Ini adalah fungsi keamanan utama kita (sandbox).
    """
    # Mengubah path menjadi path absolut yang sebenarnya, mengikuti symlink.
    # Ini mencegah trik seperti `../../`
    resolved_path = os.path.realpath(os.path.join(PROJECT_ROOT, path))
    
    # Memastikan path yang sudah diselesaikan berada di dalam atau sama dengan PROJECT_ROOT.
    is_safe = resolved_path.startswith(PROJECT_ROOT)
    
    if not is_safe:
        print(f"Error: Operasi dibatalkan. Path '{path}' berada di luar direktori proyek yang diizinkan.")
    
    return is_safe
# -----------------------------


def delete_item(path: str):
    """Menghapus file atau direktori secara rekursif (setelah pemeriksaan keamanan)."""
    if not _is_path_safe(path):
        return
        
    try:
        # Menggunakan os.path.join untuk keamanan tambahan
        full_path = os.path.join(PROJECT_ROOT, path)
        if os.path.isfile(full_path):
            os.remove(full_path)
            print(f"Success: File berhasil dihapus: {path}")
        elif os.path.isdir(full_path):
            shutil.rmtree(full_path)
            print(f"Success: Direktori berhasil dihapus: {path}")
        else:
            print(f"Warning: Item tidak ditemukan, tidak ada yang dihapus: {path}")
    except OSError as e:
        print(f"Error: Gagal menghapus '{path}': {e}")

def move_item(source: str, destination: str):
    """Memindahkan atau mengganti nama file/direktori (setelah pemeriksaan keamanan)."""
    if not _is_path_safe(source) or not _is_path_safe(destination):
        return
        
    try:
        full_source = os.path.join(PROJECT_ROOT, source)
        full_destination = os.path.join(PROJECT_ROOT, destination)
        shutil.move(full_source, full_destination)
        print(f"Success: Item berhasil dipindahkan/diganti nama dari '{source}' ke '{destination}'")
    except (FileNotFoundError, shutil.Error) as e:
        print(f"Error: Gagal memindahkan '{source}': {e}")

def list_directory(path: str = '.'):
    """Menampilkan daftar isi dari sebuah direktori (setelah pemeriksaan keamanan)."""
    if not _is_path_safe(path):
        return

    full_path = os.path.join(PROJECT_ROOT, path)
    abs_path = os.path.abspath(full_path)
    print(f"--- DAFTAR ISI: {abs_path} ---")
    try:
        if not os.path.isdir(full_path):
            print(f"Error: '{path}' bukan direktori yang valid.")
            return
        items = os.listdir(full_path)
        if not items:
            print("(Direktori ini kosong)")
        else:
            for item in sorted(items):
                print(item)
    except OSError as e:
        print(f"Error: Gagal membaca direktori '{path}': {e}")
    finally:
        print("---------------------------------")

def create_file(file_path: str):
    """Membuat sebuah file kosong (setelah pemeriksaan keamanan)."""
    if not _is_path_safe(file_path):
        return

    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        dir_name = os.path.dirname(full_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(full_path, 'w') as f:
            pass
        print(f"Success: File berhasil dibuat: {file_path}")
    except IOError as e:
        print(f"Error: Gagal membuat file: {e}")

def create_directory(dir_path: str):
    """Membuat sebuah direktori baru (setelah pemeriksaan keamanan)."""
    if not _is_path_safe(dir_path):
        return

    try:
        full_path = os.path.join(PROJECT_ROOT, dir_path)
        os.makedirs(full_path, exist_ok=True)
        print(f"Success: Direktori berhasil dibuat: {dir_path}")
    except OSError as e:
        print(f"Error: Gagal membuat direktori: {e}")

def read_file(file_path: str) -> str | None:
    """Membaca isi file (setelah pemeriksaan keamanan)."""
    if not _is_path_safe(file_path):
        return None

    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        with open(full_path, 'r') as f:
            content = f.read()
            print(f"--- ISI FILE: {file_path} ---")
            print(content)
            print("-----------------------------")
            return content
    except FileNotFoundError:
        print(f"Error: File tidak ditemukan: {file_path}")
        return None
    except IOError as e:
        print(f"Error: Gagal membaca file: {e}")
        return None

def write_to_file(file_path: str, content: str):
    """Menulis ke file (setelah pemeriksaan keamanan)."""
    if not _is_path_safe(file_path):
        return
        
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        dir_name = os.path.dirname(full_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        print(f"Success: Konten berhasil ditulis ke: {file_path}")
    except IOError as e:
        print(f"Error: Gagal menulis ke file: {e}")