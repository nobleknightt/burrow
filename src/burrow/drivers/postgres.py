"""PostgreSQL driver — wraps psycopg."""

import psycopg

from burrow.config import DatabaseConfig


def connect(config: DatabaseConfig, local_port: int | None) -> psycopg.Connection:
    if local_port is not None:
        host, port = "127.0.0.1", local_port
    else:
        host, port = config.db_host, config.db_port
    return psycopg.connect(
        host=host,
        port=port,
        user=config.db_user,
        password=config.db_password,
        dbname=config.db_name,
        options=f"-c search_path={config.db_schema}",
    )
