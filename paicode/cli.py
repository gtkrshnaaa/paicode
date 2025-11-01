#!/usr/bin/env python

import argparse
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
    config_subparsers = parser_config.add_subparsers(dest='config_cmd', help='Available config subcommands')

    parser_config_add = config_subparsers.add_parser('add', help='Add a new API key')
    parser_config_add.add_argument('id', type=str, help='API key ID')
    parser_config_add.add_argument('key', type=str, help='API key')

    parser_config_list = config_subparsers.add_parser('list', help='List all API keys')

    parser_config_show = config_subparsers.add_parser('show', help='Show an API key')
    parser_config_show.add_argument('id', type=str, help='API key ID')

    parser_config_remove = config_subparsers.add_parser('remove', help='Remove an API key')
    parser_config_remove.add_argument('id', type=str, help='API key ID')

    parser_config_set_default = config_subparsers.add_parser('set-default', help='Set an API key as default')
    parser_config_set_default.add_argument('id', type=str, help='API key ID')

    config_group = parser_config.add_mutually_exclusive_group(required=False)
    config_group.add_argument('--set', type=str, metavar='API_KEY', help='Set or update the API key (DEPRECATED)')
    config_group.add_argument('--show', action='store_true', help='Show the currently configured API key (DEPRECATED)')
    config_group.add_argument('--remove', action='store_true', help='Remove the stored API key (DEPRECATED)')

    args = parser.parse_args()

    if args.command == 'config':
        # Handle new subcommands first
        if args.config_cmd == 'add':
            config.add_api_key(args.id, args.key)
            return
        elif args.config_cmd == 'list':
            rows = config.list_api_keys()
            # Pretty table
            from rich.table import Table
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="bold")
            table.add_column("Masked Key")
            table.add_column("Default", justify="center")
            for r in rows:
                table.add_row(r.get('id',''), r.get('masked',''), r.get('is_default',''))
            ui.console.print(table)
            return
        elif args.config_cmd == 'show':
            config.show_api_key(args.id)
            return
        elif args.config_cmd == 'remove':
            config.remove_api_key(args.id)
            return
        elif args.config_cmd == 'set-default':
            config.set_default_api_key(args.id)
            return

        # Legacy flags (kept for compatibility)
        if getattr(args, 'set', None):
            config.save_api_key(args.set)
            return
        if getattr(args, 'show', False):
            config.show_api_key(None)
            return
        if getattr(args, 'remove', False):
            # In multi-key mode, removing legacy means wiping file; but safer to instruct user
            ui.print_warning("Legacy --remove is deprecated. Use: pai config remove <ID>")
            return
    else:
        # Configure LLM runtime if flags provided
        model = getattr(args, 'model', None)
        temperature = getattr(args, 'temperature', None)
        if model is not None or temperature is not None:
            llm.set_runtime_model(model, temperature)
        try:
            agent.start_interactive_session()
        except KeyboardInterrupt:
            ui.print_info("\nSession terminated by user.")
        except Exception as e:
            ui.print_error(f"An error occurred during the session: {e}")
            return 1

if __name__ == "__main__":
    main()