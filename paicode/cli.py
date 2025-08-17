#!/usr/bin/env python

import argparse
from . import agent, config

def main():
    parser = argparse.ArgumentParser(
        description="Pai Code: Your Agentic AI Coding Companion.",
        epilog="Run 'pai config --help' for API key management. Run 'pai' or 'pai auto' to start the agent."
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    subparsers.add_parser('auto', help='Start the interactive AI agent session.')

    parser_config = subparsers.add_parser('config', help='Manage the API key configuration')
    config_group = parser_config.add_mutually_exclusive_group(required=True)
    config_group.add_argument('--set', type=str, metavar='API_KEY', help='Set or update the API key')
    config_group.add_argument('--show', action='store_true', help='Show the currently configured API key')
    config_group.add_argument('--remove', action='store_true', help='Remove the stored API key')

    args = parser.parse_args()

    if args.command == 'config':
        if args.set: config.save_api_key(args.set)
        elif args.show: config.show_api_key()
        elif args.remove: config.remove_api_key()
    else:
        agent.start_interactive_session()

if __name__ == "__main__":
    main()