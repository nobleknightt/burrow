"""Database driver factory. Each driver module exposes connect(config, local_port)."""


def get_driver(db_type: str):
    if db_type == "mysql":
        from burrow.drivers import mysql

        return mysql
    if db_type == "postgres":
        from burrow.drivers import postgres

        return postgres
    raise ValueError(f"Unsupported db_type '{db_type}'. Choose 'postgres' or 'mysql'.")
