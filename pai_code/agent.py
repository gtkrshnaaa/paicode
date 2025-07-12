# pai_code/agent.py

import os
from datetime import datetime
from . import llm
from . import fs

HISTORY_DIR = ".pai_history"
VALID_COMMANDS = ["MKDIR", "TOUCH", "WRITE", "READ", "RM", "MV", "TREE", "FINISH"]

def _execute_plan(plan: str) -> str:
    """
    Mengeksekusi rencana aksi yang dibuat oleh LLM.
    Fungsi ini dimodifikasi untuk memastikan SEMUA output (komentar AI dan hasil perintah)
    tercatat dalam log dengan benar.
    """
    if not plan:
        return "Agent tidak menghasilkan rencana aksi."

    all_lines = [line.strip() for line in plan.strip().split('\n') if line.strip()]
    execution_results = []
    
    print("\n--- Hasil Eksekusi Rencana ---")
    
    for action in all_lines:
        try:
            command_candidate, _, params = action.partition('::')
            command_candidate = command_candidate.upper().strip()
            
            # Cek apakah baris ini adalah perintah yang valid atau hanya komentar
            if command_candidate in VALID_COMMANDS:
                result = ""
                
                # Menampilkan aksi yang akan dijalankan, kecuali untuk perintah yang outputnya besar
                if command_candidate not in ["WRITE", "READ", "TREE"]:
                    print(f"-> Aksi: {action}")

                if command_candidate == "WRITE":
                    file_path, _, _ = params.partition('::')
                    print(f"-> Aksi: Menulis konten ke file '{file_path}'...")
                    result = handle_write(file_path, params)
                
                elif command_candidate == "READ":
                    path_to_read = params
                    print(f"-> Aksi: Membaca file '{path_to_read}'...")
                    content = fs.read_file(path_to_read)
                    if content is not None:
                        # Tampilkan konten ke konsol
                        print(f"--- ISI FILE: {path_to_read} ---\n{content}\n-----------------------------")
                        # Siapkan hasil LENGKAP untuk log
                        result = f"Success: Berhasil membaca {path_to_read}\n--- ISI FILE: {path_to_read} ---\n{content}\n-----------------------------"
                    else:
                        result = f"Error: Gagal membaca file: {path_to_read}"

                elif command_candidate == "TREE":
                    path_to_list = params if params else '.'
                    print(f"-> Aksi: Menampilkan struktur direktori dari '{path_to_list}'...")
                    tree_output = fs.tree_directory(path_to_list)
                    if tree_output:
                        print(tree_output)
                        # KUNCI PERBAIKAN: Hasilnya adalah output pohon itu sendiri
                        result = tree_output
                    else:
                        result = "Error: Gagal menampilkan struktur direktori."
                
                elif command_candidate == "FINISH":
                    result = params if params else "Tugas dianggap selesai."
                    print(f"Agent: {result}")
                    execution_results.append(result)
                    break 

                else: # Perintah lain: MKDIR, TOUCH, RM, MV
                    if command_candidate == "MKDIR": result = fs.create_directory(params)
                    elif command_candidate == "TOUCH": result = fs.create_file(params)
                    elif command_candidate == "RM": result = fs.delete_item(params)
                    elif command_candidate == "MV":
                        source, _, dest = params.partition('::')
                        result = fs.move_item(source, dest)
                
                # Cetak pesan status (Success/Error) jika ada dan belum dicetak
                if result and command_candidate not in ["READ", "TREE"]:
                     if "Success" in result or "Error" in result or "Warning" in result:
                           print(result)

                # Tambahkan semua hasil ke daftar untuk dicatat ke log
                if result:
                    execution_results.append(result)

            else:
                # KUNCI PERBAIKAN: Komentar dari AI juga dicatat ke log
                print(f"{action}")
                execution_results.append(action)

        except Exception as e:
            msg = f"Error: Terjadi kesalahan saat memproses '{action}': {e}"
            print(msg)
            execution_results.append(msg)

    print("---------------------------------")
    # Gabungkan semua output yang terkumpul menjadi satu string untuk log
    return "\n".join(execution_results) if execution_results else "Eksekusi selesai tanpa hasil."

def handle_write(file_path: str, params: str) -> str:
    """Menjalankan LLM untuk membuat konten dan menulisnya ke file."""
    _, _, description = params.partition('::')
    
    prompt = f"Anda adalah asisten pemrograman ahli. Tulis kode lengkap untuk file '{file_path}' berdasarkan deskripsi berikut: \"{description}\". Berikan HANYA kode mentah tanpa penjelasan atau markdown."
    
    code_content = llm.generate_text(prompt)
    
    if code_content:
        return fs.write_to_file(file_path, code_content)
    else:
        return f"Error: Gagal menghasilkan konten dari LLM untuk file: {file_path}"

def start_interactive_session():
    """Memulai sesi interaktif dengan agent."""
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
            print("\nSesi dihentikan."); break
        if user_input.lower() in ['exit', 'quit']:
            print("Sesi berakhir."); break
        if not user_input: continue

        context_str = "\n".join(session_context)

        prompt = f"""
Anda adalah Pai, sebuah AI agent otonom yang sangat teliti. Tugas Anda adalah membantu pengguna dengan file system.

Perintah yang tersedia:
1. `MKDIR::path`
2. `TOUCH::path`
3. `WRITE::path::deskripsi`
4. `READ::path`
5. `RM::path`
6. `MV::sumber::tujuan`
7. `TREE::path`
8. `FINISH::pesan penutup opsional`

ATURAN DAN CARA BERPIKIR PENTING:
- **Gunakan Hasil Perintah Sebelumnya:** Perhatikan baik-baik bagian `Aksi` dari riwayat. Gunakan output dari perintah sebelumnya (seperti `TREE`) untuk membuat rencana selanjutnya. Jika `TREE` menampilkan daftar file, Anda HARUS menggunakan daftar itu untuk perintah `READ` jika diminta. Jangan meminta pengguna untuk informasi yang sudah tersedia di riwayat.
- **Satu Perintah per Baris:** Berikan satu perintah per baris dalam rencana Anda.
- **Komentar:** Anda bisa berbicara dengan pengguna. Untuk berkomentar, tulis saja teks biasa tanpa format perintah.
- **Perintah WRITE:** Untuk `WRITE`, bagian `deskripsi` HANYA berisi penjelasan singkat, BUKAN kode sebenarnya.

--- RIWAYAT SEBELUMNYA ---
{context_str}
--- AKHIR RIWAYAT ---

Permintaan terbaru dari pengguna:
"{user_input}"

Berdasarkan SELURUH riwayat dan aturan di atas, buat rencana aksi yang paling akurat, cerdas, dan komunikatif. Jangan terjebak dalam lingkaran meminta informasi yang sudah ada.
"""
        
        plan = llm.generate_text(prompt)
        system_response = _execute_plan(plan)
        
        interaction_log = f"User: {user_input}\nAI Plan:\n{plan}\nSystem Response:\n{system_response}"
        session_context.append(interaction_log)
        with open(log_file_path, 'a') as f:
            f.write(interaction_log + "\n-------------------\n")