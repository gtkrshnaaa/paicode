# pai_code/agent.py

import os
from datetime import datetime
from . import llm
from . import fs

HISTORY_DIR = ".pai_history"

def _execute_plan(plan: str) -> str:
    """
    Fungsi helper untuk mengeksekusi rencana dari LLM dan MENGEMBALIKAN outputnya.
    """
    if not plan:
        return "Agent tidak menghasilkan rencana aksi."

    print("Agent telah membuat rencana berikut:")
    print(f"---------------------------------------\n{plan}\n---------------------------------------")
    
    execution_results = []
    actions = plan.strip().split('\n')
    
    for action in actions:
        # Membersihkan setiap baris dari spasi dan karakter backtick (`)
        action = action.strip().strip("`")
        # -------------------------

        if not action: continue
        parts = action.split('::', 2)
        command = parts[0].upper()
        
        try:
            if command == "MKDIR": fs.create_directory(parts[1])
            elif command == "TOUCH": fs.create_file(parts[1])
            elif command == "WRITE": handle_write(parts[1], parts[2])
            elif command == "READ":
                path_to_read = parts[1]
                content = fs.read_file(path_to_read)
                if content is not None:
                    # Menambahkan output ke log untuk konteks AI berikutnya
                    execution_results.append(f"--- ISI FILE: {path_to_read} ---\n{content}\n-----------------------------")
                else:
                    execution_results.append(f"Error: Gagal membaca file atau file tidak ditemukan: {path_to_read}")
            elif command == "RM": fs.delete_item(parts[1])
            elif command == "MV": fs.move_item(parts[1], parts[2])
            elif command == "TREE":
                path_to_list = parts[1] if len(parts) > 1 else '.'
                tree_output = fs.tree_directory(path_to_list)
                if tree_output:
                    print(tree_output)
                    execution_results.append(tree_output)
            elif command == "FINISH":
                execution_results.append("Tugas dianggap selesai.")
                break
            else:
                msg = f"Warning: Perintah tidak dikenal dari AI: {command}"
                print(msg)
                execution_results.append(msg)
        except Exception as e:
            msg = f"Error: Terjadi kesalahan saat eksekusi '{action}': {e}"
            print(msg)
            execution_results.append(msg)
    
    return "\n".join(execution_results) if execution_results else "Tidak ada output dari eksekusi."

def handle_write(file_path: str, task: str):
    prompt = f"Anda adalah asisten pemrograman. Tulis kode untuk file '{file_path}' berdasarkan deskripsi: \"{task}\". Berikan HANYA kode mentah."
    code_content = llm.generate_text(prompt)
    if code_content: fs.write_to_file(file_path, code_content)
    else: print("Error: Gagal menghasilkan konten, file tidak ditulis.")

def start_interactive_session():
    if not os.path.exists(HISTORY_DIR): os.makedirs(HISTORY_DIR)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(HISTORY_DIR, f"session_{session_id}.log")

    session_context = []
    print("Memasuki mode auto interaktif. Ketik 'exit' atau 'quit' untuk keluar.")
    
    while True:
        try:
            user_input = input("pai> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSesi dihentikan."); break
        if user_input.lower() in ['exit', 'quit']:
            print("Sesi berakhir."); break
        if not user_input: continue

        context_str = "\n".join(session_context)

        # --- PROMPT DIMULAI ---
        prompt = f"""
Anda adalah sebuah AI agent otonom yang sangat teliti. Tugas Anda adalah membantu pengguna dengan file system.

Perintah yang tersedia:
1. `MKDIR::path` - Membuat direktori.
2. `TOUCH::path` - Membuat file kosong.
3. `WRITE::path::deskripsi` - Menulis kode ke file.
4. `READ::path` - Membaca isi sebuah file untuk observasi.
5. `RM::path` - Menghapus file atau direktori.
6. `MV::sumber::tujuan` - Memindahkan atau mengganti nama.
7. `TREE::path` - Menampilkan struktur direktori. Ini adalah alat observasi UTAMA Anda.
8. `FINISH::` - Menandakan tugas selesai.

PENTING: Gunakan output dari perintah `TREE` dan `READ` untuk memahami kondisi proyek saat ini sebelum membuat rencana aksi.

--- RIWAYAT SEBELUMNYA ---
{context_str}
--- AKHIR RIWAYAT ---

Permintaan terbaru dari pengguna:
"{user_input}"

Berdasarkan SELURUH riwayat dan hasil observasi dari `TREE` dan `READ`, buat rencana aksi yang paling akurat.
"""
        # --- AKHIR PROMPT ---
        
        plan = llm.generate_text(prompt)
        system_response = _execute_plan(plan)
        
        interaction_log = f"User: {user_input}\nAI Plan:\n{plan}\nSystem Response:\n{system_response}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")