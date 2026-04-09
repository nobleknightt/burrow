"""CLI entrypoint - registered as `burrow` via pyproject.toml [project.scripts]."""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="burrow",
        description="Query infrastructure databases through SSH tunnels",
    )
    parser.add_argument(
        "--profile",
        "-p",
        default="default",
        metavar="PROFILE",
        help="Config profile to use (default: 'default')",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # query
    p_query = sub.add_parser("query", help="Run a SQL query and print results")
    p_query.add_argument("sql", help="SQL statement to execute")
    p_query.add_argument(
        "--output",
        "-o",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )
    p_query.add_argument(
        "--no-header",
        action="store_true",
        help="Suppress column headers (table/csv only)",
    )

    # describe
    p_desc = sub.add_parser("describe", help="Inspect tables and columns")
    p_desc.add_argument(
        "--table",
        "-t",
        metavar="TABLE",
        help="Describe a specific table",
    )
    p_desc.add_argument(
        "--schema",
        "-s",
        metavar="SCHEMA",
        help="Override the schema from .env",
    )

    # shell
    sub.add_parser("shell", help="Interactive SQL REPL")

    # config
    p_cfg = sub.add_parser("config", help="Manage configuration and profiles")
    cfg_sub = p_cfg.add_subparsers(dest="config_command", required=True)

    cfg_sub.add_parser("set", help="Interactively configure a profile")
    cfg_sub.add_parser("list", help="List all profiles")

    p_cfg_get = cfg_sub.add_parser("get", help="Show resolved config for a profile")
    p_cfg_get.add_argument("key", nargs="?", help="Show a single key instead of all")

    p_cfg_unset = cfg_sub.add_parser(
        "unset", help="Remove a profile from the config file"
    )
    p_cfg_unset.add_argument(
        "profile_name", metavar="PROFILE", help="Profile to remove"
    )

    # easter egg - intentionally undocumented
    sub.add_parser("dig")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "query":
            from burrow.commands.query import cmd_query

            cmd_query(args)
        elif args.command == "describe":
            from burrow.commands.describe import cmd_describe

            cmd_describe(args)
        elif args.command == "shell":
            from burrow.commands.shell import cmd_shell

            cmd_shell(args)
        elif args.command == "config":
            from burrow.commands.config import cmd_config

            cmd_config(args)  # dispatches internally on args.config_command
        elif args.command == "dig":
            from burrow.commands.dig import cmd_dig

            cmd_dig(args)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
