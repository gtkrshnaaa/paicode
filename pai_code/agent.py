# pai_code/agent.py

import os
from datetime import datetime
from . import llm
from . import fs

# Direktori untuk menyimpan riwayat sesi
HISTORY_DIR = ".pai_history"

def _execute_plan(plan: str):
    """Fungsi helper untuk mengeksekusi rencana yang dihasilkan oleh LLM."""
    if not plan:
        print("Agent tidak menghasilkan rencana aksi.")
        return

    print("Agent telah membuat rencana berikut:")
    print(f"---------------------------------------\n{plan}\n---------------------------------------")
    
    actions = plan.strip().split('\n')
    
    for action in actions:
        action = action.strip()
        if not action:
            continue
            
        parts = action.split('::', 2)
        command = parts[0].upper()
        
        try:
            if command == "MKDIR":
                fs.create_directory(parts[1])
            elif command == "TOUCH":
                fs.create_file(parts[1])
            elif command == "WRITE":
                file_path = parts[1]
                write_task = parts[2]
                print(f"Mengeksekusi WRITE untuk {file_path}")
                handle_write(file_path, write_task) # Menggunakan kembali logika handle_write
            elif command == "FINISH":
                print("Agent menganggap tugas ini selesai.")
                break
            else:
                print(f"Perintah tidak dikenal dari AI: {command}")
        except IndexError:
            print(f"Format perintah dari AI salah: {action}")
        except Exception as e:
            print(f"Terjadi kesalahan saat eksekusi '{action}': {e}")


def handle_write(file_path: str, task: str):
    """Menangani perintah 'write' dengan membuat prompt dan menulis hasilnya."""
    prompt = f"""
Anda adalah seorang asisten pemrograman ahli.
Tugas Anda adalah menulis kode untuk file bernama '{file_path}'.
Deskripsi tugas: "{task}"
Tolong berikan HANYA kode program mentah (raw code) untuk file tersebut tanpa penjelasan tambahan atau format markdown.
"""
    code_content = llm.generate_text(prompt)
    if code_content:
        fs.write_to_file(file_path, code_content)
    else:
        print("Gagal menghasilkan konten, file tidak ditulis.")


def start_interactive_session():
    """Memulai sesi interaktif (chat mode) dengan agent."""
    # Setup riwayat
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(HISTORY_DIR, f"session_{session_id}.log")

    session_context = []
    print("Memasuki mode auto interaktif. Ketik 'exit' atau 'quit' untuk keluar.")
    
    while True:
        try:
            user_input = input("pai> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSesi dihentikan.")
            break

        if user_input.lower() in ['exit', 'quit']:
            print("👋 Sesi berakhir.")
            break
        
        if not user_input:
            continue

        # Gabungkan konteks sebelumnya
        context_str = "\n".join(session_context)

        prompt = f"""
Anda adalah sebuah AI agent otonom interaktif. Anda sedang berada dalam sesi chat dengan pengguna.
Tugas Anda adalah membantu pengguna menyelesaikan tugas pengembangan software langkah demi langkah.
Anda dapat melakukan operasi pada file system dengan mengeluarkan perintah dalam format yang telah ditentukan.

Perintah yang tersedia:
1. `MKDIR::path/to/directory` - Membuat sebuah direktori.
2. `TOUCH::path/to/file.ext` - Membuat sebuah file kosong.
3. `WRITE::path/to/file.ext::Deskripsi singkat apa yang harus ditulis di file ini.` - Menulis kode ke file.
4. `FINISH::` - Menandakan bahwa tugas dari pengguna telah selesai.

Berikut adalah riwayat percakapan sejauh ini:
---
{context_str}
---

Permintaan terbaru dari pengguna adalah:
"{user_input}"

Berdasarkan SELURUH riwayat dan permintaan terbaru, hasilkan daftar perintah yang diperlukan untuk memenuhi permintaan terbaru ini.
Hanya hasilkan perintahnya saja, satu per baris.
"""
        # Hasilkan rencana dari LLM
        plan = llm.generate_text(prompt)
        
        # Eksekusi rencana
        _execute_plan(plan)
        
        # Simpan interaksi ke riwayat untuk konteks berikutnya dan logging
        interaction_log = f"User: {user_input}\nAI Plan:\n{plan}\n"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "-------------------\n")