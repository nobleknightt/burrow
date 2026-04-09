"""burrow describe - inspect tables and column definitions."""

import argparse

from burrow.config import load_config
from burrow.output import format_table
from burrow.tunnel import PostgresSSHTunnel

_LIST_TABLES = """
SELECT
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = %s
ORDER BY table_type, table_name;
"""

_DESCRIBE_TABLE = """
SELECT
    c.column_name,
    c.data_type,
    c.character_maximum_length,
    c.is_nullable,
    c.column_default,
    CASE WHEN pk.column_name IS NOT NULL THEN 'YES' ELSE '' END AS primary_key
FROM information_schema.columns c
LEFT JOIN (
    SELECT ku.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage ku
        ON tc.constraint_name = ku.constraint_name
       AND tc.table_schema    = ku.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_name      = %s
      AND tc.table_schema    = %s
) pk ON pk.column_name = c.column_name
WHERE c.table_name   = %s
  AND c.table_schema = %s
ORDER BY c.ordinal_position;
"""


def cmd_describe(args: argparse.Namespace) -> None:
    config = load_config(args.profile)
    schema = getattr(args, "schema", None) or config.db_schema

    with PostgresSSHTunnel(config) as tunnel:
        conn = tunnel.get_connection()
        with conn.cursor() as cur:
            if args.table:
                cur.execute(_DESCRIBE_TABLE, (args.table, schema, args.table, schema))
                columns = ["column", "type", "max_len", "nullable", "default", "pk"]
            else:
                cur.execute(_LIST_TABLES, (schema,))
                columns = ["table", "type"]

            rows = cur.fetchall()

    if not rows:
        label = f"table '{args.table}'" if args.table else f"schema '{schema}'"
        print(f"(nothing found in {label})")
        return

    print(format_table(rows, columns))
