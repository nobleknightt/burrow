"""Result formatting for query output."""

import csv
import io
import json
from typing import Any


def format_table(rows: list[tuple], columns: list[str], no_header: bool = False) -> str:
    from tabulate import tabulate

    if no_header:
        return tabulate(rows, tablefmt="simple")
    return tabulate(rows, headers=columns, tablefmt="simple")


def format_json(rows: list[tuple], columns: list[str]) -> str:
    data = [dict(zip(columns, row)) for row in rows]
    return json.dumps(data, indent=2, default=_json_default)


def format_csv(rows: list[tuple], columns: list[str], no_header: bool = False) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    if not no_header:
        writer.writerow(columns)
    writer.writerows(rows)
    return buf.getvalue().rstrip()


def _json_default(obj: Any) -> Any:
    """Fallback serialiser for types psycopg returns that json can't handle."""
    import datetime
    import decimal

    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    return str(obj)
