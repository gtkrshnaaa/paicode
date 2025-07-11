# pai_code/fs.py

import os
import shutil

PROJECT_ROOT = os.path.abspath(os.getcwd())

def _is_path_safe(path: str) -> bool:
    resolved_path = os.path.realpath(os.path.join(PROJECT_ROOT, path))
    is_safe = resolved_path.startswith(PROJECT_ROOT)
    if not is_safe:
        print(f"Error: Operasi dibatalkan. Path '{path}' berada di luar direktori proyek yang diizinkan.")
    return is_safe

def tree_directory(path: str = '.') -> str:
    """Membuat representasi string dari struktur direktori secara rekursif."""
    if not _is_path_safe(path):
        return f"Error: Tidak dapat mengakses path '{path}'."

    full_path = os.path.join(PROJECT_ROOT, path)
    if not os.path.isdir(full_path):
        return f"Error: '{path}' bukan direktori yang valid."

    output_lines = [f"Struktur direktori untuk: {os.path.abspath(full_path)}\n"]
    
    for root, dirs, files in os.walk(full_path):
        # Abaikan direktori .pai_history dan __pycache__ dari tampilan
        dirs[:] = [d for d in dirs if d not in ['.pai_history', '__pycache__', '.git', 'venv']]
        
        level = root.replace(full_path, '').count(os.sep)
        indent = ' ' * 4 * level
        output_lines.append(f"{indent}{os.path.basename(root)}/")
        
        sub_indent = ' ' * 4 * (level + 1)
        for f in sorted(files):
            output_lines.append(f"{sub_indent}{f}")

    return "\n".join(output_lines)

def delete_item(path: str):
    # (Fungsi ini dan yang lainnya tetap sama, tidak perlu diubah)
    if not _is_path_safe(path): return
    try:
        full_path = os.path.join(PROJECT_ROOT, path)
        if os.path.isfile(full_path):
            os.remove(full_path)
            print(f"Success: File berhasil dihapus: {path}")
        elif os.path.isdir(full_path):
            shutil.rmtree(full_path)
            print(f"Success: Direktori berhasil dihapus: {path}")
        else:
            print(f"Warning: Item tidak ditemukan, tidak ada yang dihapus: {path}")
    except OSError as e: print(f"Error: Gagal menghapus '{path}': {e}")

def move_item(source: str, destination: str):
    if not _is_path_safe(source) or not _is_path_safe(destination): return
    try:
        full_source = os.path.join(PROJECT_ROOT, source)
        full_destination = os.path.join(PROJECT_ROOT, destination)
        shutil.move(full_source, full_destination)
        print(f"Success: Item berhasil dipindahkan/diganti nama dari '{source}' ke '{destination}'")
    except (FileNotFoundError, shutil.Error) as e: print(f"Error: Gagal memindahkan '{source}': {e}")

def create_file(file_path: str):
    if not _is_path_safe(file_path): return
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        dir_name = os.path.dirname(full_path)
        if dir_name: os.makedirs(dir_name, exist_ok=True)
        with open(full_path, 'w') as f: pass
        print(f"Success: File berhasil dibuat: {file_path}")
    except IOError as e: print(f"Error: Gagal membuat file: {e}")

def create_directory(dir_path: str):
    if not _is_path_safe(dir_path): return
    try:
        full_path = os.path.join(PROJECT_ROOT, dir_path)
        os.makedirs(full_path, exist_ok=True)
        print(f"Success: Direktori berhasil dibuat: {dir_path}")
    except OSError as e: print(f"Error: Gagal membuat direktori: {e}")

def read_file(file_path: str) -> str | None:
    if not _is_path_safe(file_path): return None
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        with open(full_path, 'r') as f: content = f.read()
        print(f"--- ISI FILE: {file_path} ---\n{content}\n-----------------------------")
        return content
    except FileNotFoundError: print(f"Error: File tidak ditemukan: {file_path}"); return None
    except IOError as e: print(f"Error: Gagal membaca file: {e}"); return None

def write_to_file(file_path: str, content: str):
    if not _is_path_safe(file_path): return
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        dir_name = os.path.dirname(full_path)
        if dir_name: os.makedirs(dir_name, exist_ok=True)
        with open(full_path, 'w') as f: f.write(content)
        print(f"Success: Konten berhasil ditulis ke: {file_path}")
    except IOError as e: print(f"Error: Gagal menulis ke file: {e}")