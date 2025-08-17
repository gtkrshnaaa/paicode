#!/usr/bin/env python

import argparse
from . import agent, fs, config, ui

def main():
    parser = argparse.ArgumentParser(
        description="Pai Code: Agentic AI CLI Coder.",
        epilog="Run 'pai <command> --help' for more details on a specific command."
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # Command: touch
    parser_touch = subparsers.add_parser('touch', help='Create an empty file')
    parser_touch.add_argument('filename', type=str, help='The name of the file to create')

    # Command: mkdir
    parser_mkdir = subparsers.add_parser('mkdir', help='Create a new directory')
    parser_mkdir.add_argument('dirname', type=str, help='The name of the directory to create')

    # Command: read
    parser_read = subparsers.add_parser('read', help='Read and display the content of a file')
    parser_read.add_argument('filename', type=str, help='The name of the file to read')
    
    # Command: write
    parser_write = subparsers.add_parser('write', help='Write code to a file using AI')
    parser_write.add_argument('file', type=str, help='The target file')
    parser_write.add_argument('task', type=str, help='The description of the task')

    # Command: rm
    parser_rm = subparsers.add_parser('rm', help='Remove a file or directory')
    parser_rm.add_argument('path', type=str, help='The path to the item to be removed')

    # Command: mv
    parser_mv = subparsers.add_parser('mv', help='Move or rename a file or directory')
    parser_mv.add_argument('source', type=str, help='The source path')
    parser_mv.add_argument('destination', type=str, help='The destination path')
    
    # Command: tree
    parser_tree = subparsers.add_parser('tree', help='Display the directory structure recursively')
    parser_tree.add_argument('path', type=str, nargs='?', default='.', help='The directory path (optional, defaults to current directory)')
    
    # Command: auto
    subparsers.add_parser('auto', help='Enter interactive agent mode')

    # Command: config
    parser_config = subparsers.add_parser('config', help='Manage the API key configuration')
    config_group = parser_config.add_mutually_exclusive_group(required=True)
    config_group.add_argument('--set', type=str, metavar='API_KEY', help='Set or update the API key')
    config_group.add_argument('--show', action='store_true', help='Show the currently configured API key')
    config_group.add_argument('--remove', action='store_true', help='Remove the stored API key')

    args = parser.parse_args()

    # Dispatch commands
    result = None
    if args.command == 'touch': result = fs.create_file(args.filename)
    elif args.command == 'mkdir': result = fs.create_directory(args.dirname)
    elif args.command == 'read': 
        content = fs.read_file(args.filename)
        if content is not None:
            # Determine language for syntax highlighting, default to text
            language = "python" if args.filename.endswith(".py") else "text"
            ui.display_panel(content, f"Content of {args.filename}", language=language)
    elif args.command == 'write': result = agent.handle_write(args.file, f"::{args.task}")
    elif args.command == 'rm': result = fs.delete_item(args.path)
    elif args.command == 'mv': result = fs.move_item(args.source, args.destination)
    elif args.command == 'tree':
        tree_output = fs.tree_directory(args.path)
        if tree_output: ui.console.print(f"[cyan]{tree_output}[/cyan]")
    elif args.command == 'auto': agent.start_interactive_session()
    elif args.command == 'config':
        if args.set: config.save_api_key(args.set)
        elif args.show: config.show_api_key()
        elif args.remove: config.remove_api_key()
    
    if result:
        if "Success" in result: ui.print_success(result)
        elif "Error" in result: ui.print_error(result)
        elif "Warning" in result: ui.print_warning(result)
        else: ui.print_info(result)

if __name__ == "__main__":
    main()