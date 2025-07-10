# pai_code/agent.py

from . import llm
from . import fs

def handle_write(file_path: str, task: str):
    """Menangani perintah 'write' dengan membuat prompt dan menulis hasilnya."""
    prompt = f"""
Anda adalah seorang asisten pemrograman ahli.
Tugas Anda adalah menulis kode untuk file bernama '{file_path}'.

Deskripsi tugas:
"{task}"

Tolong berikan HANYA kode program mentah (raw code) untuk file tersebut tanpa penjelasan tambahan, komentar pembuka/penutup, atau format markdown.
"""
    code_content = llm.generate_text(prompt)
    if code_content:
        fs.write_to_file(file_path, code_content)
    else:
        print("Gagal menghasilkan konten, file tidak ditulis.")

def handle_auto(task: str):
    """Menangani mode otomatis untuk tugas kompleks."""
    print(f"Agent mengambil alih untuk tugas: '{task}'")
    
    prompt = f"""
Anda adalah sebuah AI agent otonom yang bertugas untuk menyelesaikan tugas pengembangan software.
Tugas utama Anda adalah: "{task}"

Anda dapat melakukan operasi pada file system dengan mengeluarkan perintah dalam format yang telah ditentukan.
Perintah yang tersedia:
1. `MKDIR::path/to/directory` - Membuat sebuah direktori.
2. `TOUCH::path/to/file.ext` - Membuat sebuah file kosong.
3. `WRITE::path/to/file.ext::Deskripsi singkat apa yang harus ditulis di file ini.` - Perintah untuk menulis kode ke file.
4. `FINISH::` - Perintah untuk menandakan bahwa semua tugas telah selesai.

Analisis tugas yang diberikan, pecah menjadi langkah-langkah kecil, dan hasilkan daftar perintah yang diperlukan, satu perintah per baris.

Contoh:
Tugas: "Buat aplikasi web Flask sederhana yang menampilkan 'Hello World'."
Output yang diharapkan:
MKDIR::my_flask_app
WRITE::my_flask_app/app.py::Buat server Flask dasar yang memiliki satu route '/' yang mengembalikan 'Hello, World!'.
WRITE::my_flask_app/requirements.txt::Tulis 'Flask' di dalam file ini.
FINISH::
"""
    
    plan = llm.generate_text(prompt)
    
    if not plan:
        print("Agent gagal membuat rencana.")
        return
        
    print("Agent telah membuat rencana berikut:")
    print(plan)
    print("---------------------------------------")
    input("Tekan Enter untuk melanjutkan eksekusi...")

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
                print(f"Mengeksekusi WRITE untuk {file_path} dengan tugas: '{write_task}'")
                handle_write(file_path, write_task) # Menggunakan kembali logika handle_write
            elif command == "FINISH":
                print("Agent telah menyelesaikan semua tugas.")
                break
            else:
                print(f"Perintah tidak dikenal: {command}")
        except IndexError:
            print(f"Format perintah salah: {action}")
        except Exception as e:
            print(f"Terjadi kesalahan saat eksekusi '{action}': {e}")