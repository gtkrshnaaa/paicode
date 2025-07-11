# pai_code/cli.py
#!/usr/bin/env python

import argparse
import sys
from . import agent, fs  

def main():
    parser = argparse.ArgumentParser(
        description="Pai Code: Agentic AI CLI Coder.",
        epilog="Jalankan 'pai <perintah> --help' untuk detail lebih lanjut."
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Perintah yang tersedia')

    # Setiap subparser dibuat dalam beberapa baris agar lebih jelas dan aman

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
    parser_write = subparsers.add_parser('write', help='Menulis kode ke file')
    parser_write.add_argument('file', type=str, help='File target')
    parser_write.add_argument('task', type=str, help='Deskripsi tugas')

    # Perintah: rm
    parser_rm = subparsers.add_parser('rm', help='Menghapus file atau direktori')
    parser_rm.add_argument('path', type=str, help='Path yang akan dihapus')

    # Perintah: mv
    parser_mv = subparsers.add_parser('mv', help='Memindahkan atau mengganti nama')
    parser_mv.add_argument('source', type=str, help='Path sumber')
    parser_mv.add_argument('destination', type=str, help='Path tujuan')
    
    # Perintah: tree
    parser_tree = subparsers.add_parser('tree', help='Melihat struktur direktori secara rekursif')
    parser_tree.add_argument('path', type=str, nargs='?', default='.', help='Path direktori (opsional)')
    
    # Perintah: auto
    subparsers.add_parser('auto', help='Memasuki mode interaktif dengan agent')

    args = parser.parse_args()

    if args.command == 'touch': fs.create_file(args.filename)
    elif args.command == 'mkdir': fs.create_directory(args.dirname)
    elif args.command == 'read': fs.read_file(args.filename)
    elif args.command == 'write': agent.handle_write(args.file, args.task)
    elif args.command == 'rm': fs.delete_item(args.path)
    elif args.command == 'mv': fs.move_item(args.source, args.destination)
    elif args.command == 'tree':
        tree_output = fs.tree_directory(args.path)
        if tree_output: print(tree_output)
    elif args.command == 'auto': agent.start_interactive_session()

if __name__ == "__main__":
    # Menggunakan sys.exit(main()) adalah praktik yang baik untuk CLI tools
    # Namun, karena main() tidak mengembalikan nilai, kita bisa memanggilnya langsung
    main()