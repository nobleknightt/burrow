"""burrow shell - interactive SQL REPL."""

import argparse
import readline  # noqa: F401 - side-effect: enables arrow keys / history
import sys

import psycopg

from burrow.config import load_config
from burrow.output import format_table
from burrow.tunnel import PostgresSSHTunnel

HELP = """\
commands:
  \\q, exit, quit  - close the shell
  \\d               - list tables
  \\d <table>       - describe table
  \\o json|csv|table - change output format
  <any SQL>        - execute and print results
"""


def cmd_shell(args: argparse.Namespace) -> None:
    config = load_config(args.profile)
    fmt = "table"

    print(
        f"connecting to {config.db_name} on {config.db_host} via {config.ssh_host}..."
    )

    with PostgresSSHTunnel(config) as tunnel:
        conn = tunnel.get_connection()
        conn.autocommit = True
        print(f"connected. schema: {config.db_schema}  (\\? for help)\n")

        while True:
            try:
                line = input("db> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue
            if line in ("\\q", "exit", "quit"):
                break
            if line == "\\?":
                print(HELP)
                continue
            if line.startswith("\\o "):
                new_fmt = line.split()[1]
                if new_fmt in ("json", "csv", "table"):
                    fmt = new_fmt
                    print(f"output format: {fmt}")
                else:
                    print("unknown format - choose json, csv, or table")
                continue
            if line.startswith("\\d"):
                parts = line.split()
                table = parts[1] if len(parts) > 1 else None
                _run_describe(conn, config.db_schema, table)
                continue

            _run_query(conn, line, fmt)


def _run_query(conn: psycopg.Connection, sql: str, fmt: str) -> None:
    from burrow.output import format_csv, format_json, format_table

    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description is None:
                print(f"{cur.rowcount} row(s) affected")
                return
            columns = [d.name for d in cur.description]
            rows = cur.fetchall()
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return

    if not rows:
        print("(no rows)")
        return

    match fmt:
        case "json":
            print(format_json(rows, columns))
        case "csv":
            print(format_csv(rows, columns))
        case _:
            print(format_table(rows, columns))


def _run_describe(conn: psycopg.Connection, schema: str, table: str | None) -> None:
    from burrow.commands.describe import _DESCRIBE_TABLE, _LIST_TABLES

    try:
        with conn.cursor() as cur:
            if table:
                cur.execute(_DESCRIBE_TABLE, (table, schema, table, schema))
                columns = ["column", "type", "max_len", "nullable", "default", "pk"]
            else:
                cur.execute(_LIST_TABLES, (schema,))
                columns = ["table", "type"]
            rows = cur.fetchall()
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return

    if not rows:
        print("(no rows)")
        return
    print(format_table(rows, columns))
