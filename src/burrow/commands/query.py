"""burrow query - run a one-shot SQL statement and print results."""

import argparse
import re
import sys

from burrow.config import AccessMode, load_config
from burrow.drivers import get_driver
from burrow.output import format_csv, format_json, format_table
from burrow.tunnel import SSHTunnel

# Data-modification (DML) and schema-modification (DDL) keywords for both
# PostgreSQL and MySQL. REPLACE and LOAD cover MySQL-specific write ops;
# COPY covers PostgreSQL COPY ... FROM (data import).
_WRITE_KEYWORDS = frozenset({
    # DML
    "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REPLACE", "MERGE",
    # DDL
    "CREATE", "DROP", "ALTER", "RENAME",
    # data import
    "COPY", "LOAD",
})


def _strip_comments(sql: str) -> str:
    sql = re.sub(r'--[^\n]*', ' ', sql)
    sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.DOTALL)
    return sql.strip()


def statement_keyword(sql: str) -> str | None:
    """Return the primary SQL keyword (uppercase) of the statement.

    Handles leading comments and CTEs (WITH ... AS (...) VERB ...).
    """
    sql = _strip_comments(sql)
    if not sql:
        return None

    m = re.match(r'\b(\w+)\b', sql)
    if not m:
        return None

    first = m.group(1).upper()
    if first != 'WITH':
        return first

    # CTE: WITH name AS (...) [, name AS (...)]* VERB ...
    # State machine: skip each "name AS (...)" block, return the first
    # depth-0 token that follows — that's the main statement keyword.
    # Using a state machine (not just last-close scan) so that subqueries
    # inside the main statement (e.g. WHERE id IN (...)) don't mislead us.
    _WANT_NAME, _WANT_AS, _WANT_OPEN, _IN_BODY, _AFTER_BODY = range(5)
    state = _WANT_NAME
    depth = 0

    for tok in re.finditer(r'[(),]|\b\w+\b', sql):
        t = tok.group()
        upper = t.upper() if t not in ('(', ')', ',') else t

        if state == _WANT_NAME:
            if upper != 'WITH':
                state = _WANT_AS
        elif state == _WANT_AS:
            if upper == 'AS':
                state = _WANT_OPEN
        elif state == _WANT_OPEN:
            if t == '(':
                depth = 1
                state = _IN_BODY
        elif state == _IN_BODY:
            if t == '(':
                depth += 1
            elif t == ')':
                depth -= 1
                if depth == 0:
                    state = _AFTER_BODY
        elif state == _AFTER_BODY:
            if t == ',':
                state = _WANT_NAME
            elif t not in ('(', ')'):
                return upper

    return first


def check_access(sql: str, access_mode: AccessMode) -> None:
    """Raise SystemExit if the statement is not allowed under access_mode."""
    if access_mode != AccessMode.READ:
        return

    kw = statement_keyword(sql)
    if kw in _WRITE_KEYWORDS:
        raise SystemExit(
            f"error: profile is configured for read-only access (access_mode = read)\n"
            f"statement type '{kw}' is not allowed\n"
            f"\nto allow writes, set access_mode = readwrite in your profile"
        )


def cmd_query(args: argparse.Namespace) -> None:
    config = load_config(args.profile)
    check_access(args.sql, config.access_mode)

    with SSHTunnel(config) as tunnel:
        conn = get_driver(config.db_type).connect(config, tunnel.local_port)
        with conn.cursor() as cur:
            cur.execute(args.sql)

            if cur.description is None:
                # DML statement - print affected row count
                print(f"{cur.rowcount} row(s) affected")
                conn.commit()
                return

            columns = [d[0] for d in cur.description]
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
