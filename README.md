# burrow

CLI for querying PostgreSQL databases behind a bastion host via SSH tunnel.

Named after the mole's burrow — a tunnel dug quietly underground to reach somewhere it has no business being. That's exactly what this tool does: bores through a bastion over SSH and surfaces inside your database as if the database were local.

## Claude Code Integration

This repository includes [`SKILL.md`](SKILL.md) — a skill definition that enables AI coding agents (primarily [Claude Code](https://code.claude.com)) to use burrow effectively. The skill teaches Claude when and how to use burrow for database operations.

While designed for Claude Code, the skill's markdown documentation can be used by other AI coding assistants as reference material.

## Installation

- **uv (recommended):**

  ```bash
  uv tool install git+https://github.com/nobleknightt/burrow.git
  ```

  If this is your first `uv tool install`, restart your shell so `~/.local/bin` is on `PATH`.

- **pip:**

  ```bash
  pip install git+https://github.com/nobleknightt/burrow.git
  ```

  Restart your shell.

## Setup

Run the interactive wizard to configure your first profile:

```bash
burrow config set
```

To configure additional named profiles (e.g. staging, prod), pass `--profile`:

```bash
burrow --profile staging config set
```

## Configuration

Priority order (highest wins):

1. **Environment variables** — `BURROW_SSH_HOST`, `BURROW_DB_PASSWORD`, etc.
2. **Config file** — `~/.config/burrow/config.toml` (override with `$BURROW_CONFIG`)
3. **Built-in defaults** for optional fields

The config file supports named profiles:

```toml
[default]
ssh_host     = "bastion.example.com"
ssh_user     = "ec2-user"
ssh_key_path = "~/.ssh/id_rsa"
db_host      = "mydb.cluster.us-east-1.rds.amazonaws.com"
db_user      = "myuser"
db_password  = "secret"
db_name      = "mydb"
db_schema    = "public"

[staging]
ssh_host     = "bastion-staging.example.com"
ssh_user     = "ec2-user"
ssh_key_path = "~/.ssh/id_rsa"
db_host      = "mydb-staging.cluster.us-east-1.rds.amazonaws.com"
db_user      = "myuser"
db_password  = "secret"
db_name      = "mydb_staging"
db_schema    = "public"
```

## Usage

```bash
# one-shot query
burrow query "SELECT id, name FROM users LIMIT 10"
burrow query "SELECT * FROM orders" --output json
burrow query "SELECT * FROM products" --output csv

# use a named profile
burrow --profile staging query "SELECT count(*) FROM users"

# inspect schema
burrow describe                    # list all tables
burrow describe --table users      # columns, types, PKs

# interactive REPL
burrow shell

# configure profiles
burrow config set
burrow --profile staging config set

# check resolved config (passwords redacted)
burrow config get
burrow --profile staging config get
```
