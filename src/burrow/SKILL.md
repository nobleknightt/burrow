---
name: burrow
version: "0.4.0"
description: Queries PostgreSQL and MySQL databases using the burrow CLI — via SSH tunnel through a bastion host or direct connection. Use when the user needs to run SQL queries, inspect database tables or schemas, explore data structure, or analyze data in remote databases. Trigger for database queries, postgres, postgresql, mysql, SQL, SSH tunnel, bastion host, remote database, schema inspection, table exploration, data analysis, burrow CLI.
when_to_use: database queries, inspect tables, SQL, postgres, postgresql, mysql, SSH tunnel, bastion, remote database, burrow, schema inspection, data exploration, table structure
allowed-tools: Bash(burrow *)
---

# Burrow — Database Queries via SSH Tunnel or Direct Connection

`burrow` opens an SSH tunnel through a bastion host (or connects directly) and runs queries against PostgreSQL or MySQL databases.

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
burrow -p <profile> describe --schema public --table some_table
```

## Workflow

1. Run `burrow config list` to discover profiles if not specified by the user.
2. Use `describe` to explore table names and columns before writing queries.
3. Use `--output json` when results will be processed programmatically.
4. Always `LIMIT` exploratory queries to avoid large result sets.
