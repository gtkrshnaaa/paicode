# pai_code/cli.py
#!/usr/bin/env python

import argparse
from . import agent, fs  

def main():
    parser = argparse.ArgumentParser(
        description="Pai Code: Agentic AI CLI Coder.",
        epilog="Jalankan 'pai <perintah> --help' untuk detail lebih lanjut."
    )
    
    subparsers = parser.add_subparsers(dest='command', required=True, help='Perintah yang tersedia')

    # Perintah: touch
    parser_touch = subparsers.add_parser('touch', help='Membuat file kosong')
    parser_touch.add_argument('filename', type=str, help='Nama file yang akan dibuat')

    # Perintah: mkdir
    parser_mkdir = subparsers.add_parser('mkdir', help='Membuat direktori baru')
    parser_mkdir.add_argument('dirname', type=str, help='Nama direktori yang akan dibuat')

    # Perintah: read
    parser_read = subparsers.add_parser('read', help='Membaca dan menampilkan isi file')
    parser_read.add_argument('filename', type=str, help='Nama file yang akan dibaca')
    
    # Perintah: write
    parser_write = subparsers.add_parser('write', help='Menulis kode ke file berdasarkan deskripsi tugas')
    parser_write.add_argument('file', type=str, help='File target untuk ditulis')
    parser_write.add_argument('task', type=str, help='Deskripsi tugas untuk kode yang akan ditulis')

    # Perintah: auto
    # Tidak lagi memerlukan argumen 'task'.
    parser_auto = subparsers.add_parser('auto', help='Memasuki mode interaktif (chat mode) dengan agent')
    # -------------------------

    args = parser.parse_args()

    if args.command == 'touch':
        fs.create_file(args.filename)
    elif args.command == 'mkdir':
        fs.create_directory(args.dirname)
    elif args.command == 'read':
        fs.read_file(args.filename)
    elif args.command == 'write':
        agent.handle_write(args.file, args.task)
    elif args.command == 'auto':
        # Memanggil fungsi baru untuk sesi interaktif
        agent.start_interactive_session()
    # -------------------------


if __name__ == "__main__":
    main()