"""Database driver factory. Each driver module exposes connect(config, local_port)."""


def get_driver(db_type: str):
    if db_type == "mysql":
        from burrow.drivers import mysql

        return mysql
    from burrow.drivers import postgres

    return postgres
