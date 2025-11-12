#!/usr/bin/env python

import argparse
from . import agent, config, llm, ui

def main():
    parser = argparse.ArgumentParser(
        description="Pai Code: Your Single-Shot Agentic AI Coding Companion.",
        epilog="Use 'pai config set <API_KEY>' to configure. Run 'pai' to start the intelligent agent."
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Main agent command (default)
    parser_auto = subparsers.add_parser('auto', help='Start the single-shot AI agent session.')
    parser_auto.add_argument('--model', type=str, help='LLM model name (e.g., gemini-2.5-flash-lite)')
    parser_auto.add_argument('--temperature', type=float, help='LLM sampling temperature (e.g., 0.2)')

    # Simplified config management
    parser_config = subparsers.add_parser('config', help='Manage API key configuration')
    config_subparsers = parser_config.add_subparsers(dest='config_cmd', help='Config commands')

    parser_config_set = config_subparsers.add_parser('set', help='Set API key')
    parser_config_set.add_argument('api_key', type=str, help='Google Gemini API key')

    parser_config_show = config_subparsers.add_parser('show', help='Show current API key (masked)')

    parser_config_remove = config_subparsers.add_parser('remove', help='Remove stored API key')

    parser_config_validate = config_subparsers.add_parser('validate', help='Validate current API key')

    config_group = parser_config.add_mutually_exclusive_group(required=False)
    config_group.add_argument('--set', type=str, metavar='API_KEY', help='Set or update the API key (DEPRECATED)')
    config_group.add_argument('--show', action='store_true', help='Show the currently configured API key (DEPRECATED)')
    config_group.add_argument('--remove', action='store_true', help='Remove the stored API key (DEPRECATED)')

    args = parser.parse_args()

    # Handle config commands
    if args.command == 'config':
        if args.config_cmd == 'set':
            config.set_api_key(args.api_key)
            return
        elif args.config_cmd == 'show':
            config.show_api_key()
            return
        elif args.config_cmd == 'remove':
            config.remove_api_key()
            return
        elif args.config_cmd == 'validate':
            is_valid, message = config.validate_api_key()
            if is_valid:
                ui.print_success(f"✓ {message}")
            else:
                ui.print_error(f"✗ {message}")
            return
        else:
            parser_config.print_help()
            return

        # Legacy flags (kept for compatibility)
        if getattr(args, 'set', None):
            config.set_api_key(args.set)
            return
        if getattr(args, 'show', False):
            config.show_api_key()
            return
        if getattr(args, 'remove', False):
            config.remove_api_key()
            return
    # Default: start agent
    # Check API key before starting
    if not config.is_configured():
        ui.print_error("✗ No API key configured.")
        ui.print_info("Use 'pai config set <API_KEY>' to set your Google Gemini API key.")
        return 1

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