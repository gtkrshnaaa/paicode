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

    # Perintah yang sudah ada
    parser_touch = subparsers.add_parser('touch', help='Membuat file kosong')
    parser_touch.add_argument('filename', type=str, help='Nama file yang akan dibuat')

    parser_mkdir = subparsers.add_parser('mkdir', help='Membuat direktori baru')
    parser_mkdir.add_argument('dirname', type=str, help='Nama direktori yang akan dibuat')

    parser_read = subparsers.add_parser('read', help='Membaca dan menampilkan isi file')
    parser_read.add_argument('filename', type=str, help='Nama file yang akan dibaca')
    
    parser_write = subparsers.add_parser('write', help='Menulis kode ke file berdasarkan deskripsi tugas')
    parser_write.add_argument('file', type=str, help='File target untuk ditulis')
    parser_write.add_argument('task', type=str, help='Deskripsi tugas untuk kode yang akan ditulis')

    # Perintah baru
    parser_rm = subparsers.add_parser('rm', help='Menghapus file atau direktori')
    parser_rm.add_argument('path', type=str, help='Path file/direktori yang akan dihapus')

    parser_mv = subparsers.add_parser('mv', help='Memindahkan atau mengganti nama file/direktori')
    parser_mv.add_argument('source', type=str, help='Path sumber')
    parser_mv.add_argument('destination', type=str, help='Path tujuan')

    parser_ls = subparsers.add_parser('ls', help='Melihat daftar isi direktori')
    parser_ls.add_argument('path', type=str, nargs='?', default='.', help='Path direktori (opsional, default: direktori saat ini)')
    
    # Perintah auto mode
    parser_auto = subparsers.add_parser('auto', help='Memasuki mode interaktif (chat mode) dengan agent')

    args = parser.parse_args()

    # Logika penanganan perintah
    if args.command == 'touch':
        fs.create_file(args.filename)
    elif args.command == 'mkdir':
        fs.create_directory(args.dirname)
    elif args.command == 'read':
        fs.read_file(args.filename)
    elif args.command == 'write':
        agent.handle_write(args.file, args.task)
    elif args.command == 'rm':
        fs.delete_item(args.path)
    elif args.command == 'mv':
        fs.move_item(args.source, args.destination)
    elif args.command == 'ls':
        fs.list_directory(args.path)
    elif args.command == 'auto':
        agent.start_interactive_session()

if __name__ == "__main__":
    main()