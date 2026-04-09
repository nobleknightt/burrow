"""burrow query - run a one-shot SQL statement and print results."""

import argparse
import sys

from burrow.config import load_config
from burrow.output import format_csv, format_json, format_table
from burrow.tunnel import PostgresSSHTunnel


def cmd_query(args: argparse.Namespace) -> None:
    config = load_config(args.profile)

    with PostgresSSHTunnel(config) as tunnel:
        conn = tunnel.get_connection()
        with conn.cursor() as cur:
            cur.execute(args.sql)

            if cur.description is None:
                # DML statement - print affected row count
                print(f"{cur.rowcount} row(s) affected")
                conn.commit()
                return

            columns = [d.name for d in cur.description]
            rows = cur.fetchall()

    if not rows:
        print("(no rows)", file=sys.stderr)
        return

    match args.output:
        case "json":
            print(format_json(rows, columns))
        case "csv":
            print(format_csv(rows, columns, no_header=args.no_header))
        case _:
            print(format_table(rows, columns, no_header=args.no_header))
