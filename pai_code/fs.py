# pai_code/fs.py

import os
import shutil

PROJECT_ROOT = os.path.abspath(os.getcwd())

def _is_path_safe(path: str) -> bool:
    """Memastikan path target berada di dalam direktori proyek."""
    try:
        resolved_path = os.path.realpath(os.path.join(PROJECT_ROOT, path))
        is_safe = resolved_path.startswith(PROJECT_ROOT)
        if not is_safe:
            print(f"Error: Operasi dibatalkan. Path '{path}' berada di luar direktori proyek.")
        return is_safe
    except Exception as e:
        print(f"Error saat validasi path: {e}")
        return False

def tree_directory(path: str = '.') -> str:
    """Membuat representasi string dari struktur direktori secara rekursif."""
    if not _is_path_safe(path):
        return f"Error: Tidak dapat mengakses path '{path}'."

    full_path = os.path.join(PROJECT_ROOT, path)
    if not os.path.isdir(full_path):
        return f"Error: '{path}' bukan direktori yang valid."

    # Header
    tree_lines = [f"Struktur direktori untuk: {os.path.abspath(full_path)}", f"{os.path.basename(full_path)}/"]

    # Fungsi rekursif untuk membangun pohon
    def build_tree(directory, prefix=""):
        # Filter item yang tidak diinginkan
        items_to_ignore = ['.git', 'venv', '__pycache__', '.pai_history']
        try:
            items = sorted([item for item in os.listdir(directory) if item not in items_to_ignore])
        except FileNotFoundError:
            return

        pointers = ['├── '] * (len(items) - 1) + ['└── ']
        
        for pointer, item in zip(pointers, items):
            tree_lines.append(f"{prefix}{pointer}{item}")
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                # Tentukan prefix untuk level selanjutnya
                extension = '│   ' if pointer == '├── ' else '    '
                build_tree(item_path, prefix=prefix + extension)

    build_tree(full_path)
    return "\n".join(tree_lines)

def delete_item(path: str) -> str:
    """Menghapus file atau direktori dan mengembalikan pesan status."""
    if not _is_path_safe(path): return f"Error: Path '{path}' tidak aman."
    try:
        full_path = os.path.join(PROJECT_ROOT, path)
        if os.path.isfile(full_path):
            os.remove(full_path)
            return f"Success: File berhasil dihapus: {path}"
        elif os.path.isdir(full_path):
            shutil.rmtree(full_path)
            return f"Success: Direktori berhasil dihapus: {path}"
        else:
            return f"Warning: Item tidak ditemukan, tidak ada yang dihapus: {path}"
    except OSError as e:
        return f"Error: Gagal menghapus '{path}': {e}"

def move_item(source: str, destination: str) -> str:
    """Memindahkan item dan mengembalikan pesan status."""
    if not _is_path_safe(source) or not _is_path_safe(destination):
        return "Error: Path sumber atau tujuan tidak aman."
    try:
        full_source = os.path.join(PROJECT_ROOT, source)
        full_destination = os.path.join(PROJECT_ROOT, destination)
        shutil.move(full_source, full_destination)
        return f"Success: Item berhasil dipindahkan dari '{source}' ke '{destination}'"
    except (FileNotFoundError, shutil.Error) as e:
        return f"Error: Gagal memindahkan '{source}': {e}"

def create_file(file_path: str) -> str:
    """Membuat file kosong dan mengembalikan pesan status."""
    if not _is_path_safe(file_path): return f"Error: Path '{file_path}' tidak aman."
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        dir_name = os.path.dirname(full_path)
        if dir_name: os.makedirs(dir_name, exist_ok=True)
        with open(full_path, 'w') as f: pass
        return f"Success: File berhasil dibuat: {file_path}"
    except IOError as e:
        return f"Error: Gagal membuat file: {e}"

def create_directory(dir_path: str) -> str:
    """Membuat direktori dan mengembalikan pesan status."""
    if not _is_path_safe(dir_path): return f"Error: Path '{dir_path}' tidak aman."
    try:
        full_path = os.path.join(PROJECT_ROOT, dir_path)
        os.makedirs(full_path, exist_ok=True)
        return f"Success: Direktori berhasil dibuat: {dir_path}"
    except OSError as e:
        return f"Error: Gagal membuat direktori: {e}"

def read_file(file_path: str) -> str | None:
    """Membaca file dan mengembalikan isinya atau None jika gagal."""
    if not _is_path_safe(file_path): return None
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        with open(full_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File tidak ditemukan: {file_path}")
        return None
    except IOError as e:
        print(f"Error: Gagal membaca file: {e}")
        return None

def write_to_file(file_path: str, content: str) -> str:
    """Menulis ke file dan mengembalikan pesan status."""
    if not _is_path_safe(file_path): return f"Error: Path '{file_path}' tidak aman."
    try:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        dir_name = os.path.dirname(full_path)
        if dir_name: os.makedirs(dir_name, exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return f"Success: Konten berhasil ditulis ke: {file_path}"
    except IOError as e:
        return f"Error: Gagal menulis ke file: {e}"