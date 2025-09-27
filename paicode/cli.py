#!/usr/bin/env python

import argparse
from rich.table import Table
from . import agent, config, llm, ui

def main():
    parser = argparse.ArgumentParser(
        description="Pai Code: Your Agentic AI Coding Companion.",
        epilog="Run 'pai config --help' for API key management. Run 'pai' or 'pai auto' to start the agent."
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    parser_auto = subparsers.add_parser('auto', help='Start the interactive AI agent session.')
    parser_auto.add_argument('--model', type=str, help='LLM model name (e.g., gemini-2.5-flash)')
    parser_auto.add_argument('--temperature', type=float, help='LLM sampling temperature (e.g., 0.2)')

    parser_config = subparsers.add_parser('config', help='Manage the API key configuration')
    # Backward-compatible flags
    parser_config.add_argument('--set', type=str, metavar='API_KEY', help='Set or update the default API key (compat)')
    parser_config.add_argument('--show', action='store_true', help='Show the currently configured API key (first enabled)')
    parser_config.add_argument('--remove', action='store_true', help='Remove the legacy single-key file (compat)')

    # Subcommands for multi-key management
    cfg_sub = parser_config.add_subparsers(dest='config_cmd', help='Multi-key management')

    cfg_list = cfg_sub.add_parser('list', help='List all API keys')

    cfg_add = cfg_sub.add_parser('add', help='Add a new API key')
    cfg_add.add_argument('--key', required=True, help='API key value')
    cfg_add.add_argument('--label', required=False, help='Optional label for the key')

    cfg_edit = cfg_sub.add_parser('edit', help='Edit/replace an existing API key by id')
    cfg_edit.add_argument('--id', type=int, required=True, help='Key ID')
    cfg_edit.add_argument('--key', required=True, help='New API key value')

    cfg_rename = cfg_sub.add_parser('rename', help='Rename a key label by id')
    cfg_rename.add_argument('--id', type=int, required=True, help='Key ID')
    cfg_rename.add_argument('--label', required=True, help='New label')

    cfg_remove = cfg_sub.add_parser('remove', help='Remove a key by id')
    cfg_remove.add_argument('--id', type=int, required=True, help='Key ID')

    cfg_enable = cfg_sub.add_parser('enable', help='Enable a key by id')
    cfg_enable.add_argument('--id', type=int, required=True, help='Key ID')

    cfg_disable = cfg_sub.add_parser('disable', help='Disable a key by id')
    cfg_disable.add_argument('--id', type=int, required=True, help='Key ID')

    args = parser.parse_args()

    if args.command == 'config':
        # Multi-key subcommands first
        if getattr(args, 'config_cmd', None) == 'list':
            keys = config.list_api_keys()
            table = Table(show_header=True, header_style='bold')
            table.add_column('ID', justify='right', width=4)
            table.add_column('Label')
            table.add_column('Enabled', justify='center', width=8)
            table.add_column('Created At')
            table.add_column('Masked Key')
            for k in keys:
                keyval = k.get('key', '')
                masked = f"{keyval[:5]}...{keyval[-4:]}" if keyval else ''
                table.add_row(
                    str(k.get('id', '')),
                    str(k.get('label', '')),
                    'Yes' if k.get('enabled', True) else 'No',
                    str(k.get('created_at', '')),
                    masked,
                )
            ui.console.print(table)
        elif getattr(args, 'config_cmd', None) == 'add':
            config.add_api_key(args.key, args.label)
        elif getattr(args, 'config_cmd', None) == 'edit':
            config.edit_api_key(args.id, args.key)
        elif getattr(args, 'config_cmd', None) == 'rename':
            config.rename_api_key(args.id, args.label)
        elif getattr(args, 'config_cmd', None) == 'remove':
            config.remove_api_key_by_id(args.id)
        elif getattr(args, 'config_cmd', None) == 'enable':
            config.enable_api_key(args.id, True)
        elif getattr(args, 'config_cmd', None) == 'disable':
            config.enable_api_key(args.id, False)
        else:
            # Backward-compatible flags
            if args.set:
                config.save_api_key(args.set)
            elif args.show:
                config.show_api_key()
            elif args.remove:
                config.remove_api_key()
            else:
                ui.print_info("Use 'pai config --help' to see subcommands for multi-key management.")
    else:
        # Configure LLM runtime if flags provided
        model = getattr(args, 'model', None)
        temperature = getattr(args, 'temperature', None)
        if model is not None or temperature is not None:
            llm.set_runtime_model(model, temperature)
        agent.start_interactive_session()

if __name__ == "__main__":
    main()