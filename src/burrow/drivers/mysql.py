"""MySQL driver — wraps pymysql."""

import pymysql
import pymysql.cursors

from burrow.config import DatabaseConfig


def connect(config: DatabaseConfig, local_port: int | None) -> pymysql.connections.Connection:
    if local_port is not None:
        host, port = "127.0.0.1", local_port
    else:
        host, port = config.db_host, config.db_port
    return pymysql.connect(
        host=host,
        port=port,
        user=config.db_user,
        password=config.db_password,
        database=config.db_name,
        connect_timeout=config.connection_timeout,
        cursorclass=pymysql.cursors.Cursor,
    )
