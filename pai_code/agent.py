# pai_code/agent.py

import os
from datetime import datetime
from . import llm
from . import fs

HISTORY_DIR = ".pai_history"

VALID_COMMANDS = ["MKDIR", "TOUCH", "WRITE", "READ", "RM", "MV", "TREE", "FINISH"]

def _execute_plan(plan: str) -> str:
    if not plan:
        return "Agent tidak menghasilkan rencana aksi."

    all_lines = [line.strip() for line in plan.strip().split('\n') if line.strip()]
    
    has_actions = any(
        line.split('::', 1)[0].upper().strip() in VALID_COMMANDS 
        for line in all_lines
    )

    if has_actions:
        print("\nAgent akan menjalankan rencana berikut:")
        print("---------------------------------------")

    execution_results = []
    
    for action in all_lines:
        try:
            command_candidate = action.split('::', 1)[0].upper().strip()
            
            if command_candidate in VALID_COMMANDS:
                print(f"-> Melakukan: {action}") 
                
                action = action.strip("`")
                parts = action.split('::', 2)
                command = parts[0].upper()
                
                if command == "MKDIR": fs.create_directory(parts[1])
                elif command == "TOUCH": fs.create_file(parts[1])
                elif command == "WRITE": handle_write(parts[1], parts[2])
                elif command == "READ":
                    path_to_read = parts[1]
                    content = fs.read_file(path_to_read)
                    if content is not None:
                        execution_results.append(f"--- ISI FILE: {path_to_read} ---\n{content}\n-----------------------------")
                    else:
                        execution_results.append(f"Error: Gagal membaca file: {path_to_read}")
                elif command == "RM": fs.delete_item(parts[1])
                elif command == "MV": fs.move_item(parts[1], parts[2])
                
                # --- INI BAGIAN YANG DIPERBAIKI ---
                elif command == "TREE":
                    path_to_list = parts[1] if len(parts) > 1 else '.'
                    tree_output = fs.tree_directory(path_to_list)
                    if tree_output:
                        print(tree_output)
                        execution_results.append(tree_output)
                # --- AKHIR PERBAIKAN ---

                elif command == "FINISH":
                    if len(parts) > 1 and parts[1]:
                        print(parts[1])
                    execution_results.append("Tugas dianggap selesai.")
                    break
            else:
                print(action)
                
        except Exception as e:
            msg = f"Error: Terjadi kesalahan saat memproses '{action}': {e}"
            print(msg)
            execution_results.append(msg)
    
    if has_actions:
        print("---------------------------------------")

    return "\n".join(execution_results) if execution_results else "Eksekusi selesai."

def handle_write(file_path: str, task: str):
    prompt = f"Anda adalah asisten pemrograman ahli. Tulis kode lengkap untuk file '{file_path}' berdasarkan deskripsi berikut: \"{task}\". Berikan HANYA kode mentah tanpa penjelasan atau markdown."
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

        prompt = f"""
Anda adalah sebuah AI agent otonom yang sangat teliti. Tugas Anda adalah membantu pengguna dengan file system.

Perintah yang tersedia:
1. `MKDIR::path`
2. `TOUCH::path`
3. `WRITE::path::deskripsi`
4. `READ::path`
5. `RM::path`
6. `MV::sumber::tujuan`
7. `TREE::path`
8. `FINISH::pesan penutup opsional`

PENTING: 
- Anda bisa berbicara dengan pengguna. Untuk berkomentar, tulis saja teks biasa tanpa format perintah.
- Ketika merencanakan, berikan hanya perintah atau komentar. Jangan menulis blok kode dalam rencana Anda. Penulisan kode hanya terjadi saat perintah `WRITE` dieksekusi.

Contoh respons Anda:
Tentu, saya buatkan struktur proyeknya.
MKDIR::src
TOUCH::src/main.py
Struktur sudah siap. Selanjutnya apa?

--- RIWAYAT SEBELUMNYA ---
{context_str}
--- AKHIR RIWAYAT ---

Permintaan terbaru dari pengguna:
"{user_input}"

Berdasarkan SELURUH riwayat, buat rencana aksi yang paling akurat dan komunikatif.
"""
        
        plan = llm.generate_text(prompt)
        system_response = _execute_plan(plan)
        
        interaction_log = f"User: {user_input}\nAI Plan:\n{plan}\nSystem Response:\n{system_response}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")