---
name: burrow
description: Queries PostgreSQL databases using the burrow CLI — primarily via SSH tunnel through a bastion host, with optional direct connection mode. Use when the user needs to run SQL queries, inspect database tables or schemas, explore data structure, analyze data, or connect to remote PostgreSQL databases. Trigger for database queries, postgres, postgresql, SQL, SSH tunnel, bastion host, remote database, schema inspection, table exploration, data analysis, burrow CLI.
when_to_use: database queries, inspect tables, SQL, postgres, postgresql, SSH tunnel, bastion, remote database, burrow, schema inspection, data exploration, table structure
allowed-tools: Bash(burrow *)
---

# Burrow — PostgreSQL via SSH Tunnel (or Direct Connection)

`burrow` primarily opens an SSH tunnel through a bastion host and runs queries against PostgreSQL databases behind it. It also supports direct connections when no SSH tunnel is needed (`use_ssh = false`).

## Configuration priority

1. Environment variables (`BURROW_SSH_HOST`, `BURROW_DB_PORT`, etc.)
2. `~/.config/burrow/config.toml` (TOML, supports named profiles)
3. Built-in defaults

## Discover available profiles

```bash
burrow config list
```

Always ask the user which profile to use if not specified. Pass `-p <profile>` before the subcommand.

## Commands

### Run a SQL query

```bash
burrow -p <profile> query "SELECT * FROM some_table LIMIT 10"
burrow -p <profile> query --output json "SELECT id, name FROM some_table"
burrow -p <profile> query --output csv  "SELECT * FROM some_table"
```

`--output` options: `table` (default), `json`, `csv`  
`--no-header` suppresses column headers (table/csv)

### Inspect tables and columns

```bash
burrow -p <profile> describe                          # list all tables
burrow -p <profile> describe --table some_table       # show columns, types, primary keys
burrow -p <profile> describe --schema myschema --table some_table
```

### Interactive SQL REPL

```bash
burrow -p <profile> shell
```

### Connection diagnostics

```bash
burrow -p <profile> dig
```

### Manage config profiles

```bash
burrow config list                    # list all profiles
burrow -p <profile> config get        # show resolved config (password redacted)
burrow config set                     # interactively create/update a profile
burrow config unset <profile>         # remove a profile
```

## Config file format (`~/.config/burrow/config.toml`)

SSH tunnel (default — `use_ssh` defaults to `true` when omitted):

```toml
[default]
ssh_host     = "bastion.example.com"
ssh_user     = "ec2-user"
ssh_key_path = "~/.ssh/id_rsa"
ssh_port     = 22
db_host      = "mydb.rds.amazonaws.com"
db_port      = 5432
db_user      = "myuser"
db_password  = "secret"
db_name      = "mydb"
db_schema    = "public"

[staging]
# same fields, different values
```

Direct connection (no SSH — set `use_ssh = false`, SSH fields not required):

```toml
[local]
use_ssh     = false
db_host     = "localhost"
db_port     = 5432
db_user     = "myuser"
db_password = "secret"
db_name     = "mydb"
```

## Workflow

1. Run `burrow config list` to discover profiles if not specified by the user.
2. Use `describe` to explore table names/columns before writing queries.
3. Use `--output json` when results will be processed programmatically.
4. Always `LIMIT` exploratory queries to avoid large result sets.
