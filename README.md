# burrow

CLI for querying PostgreSQL and MySQL databases — directly or through an SSH tunnel to a bastion host.

Named after the mole's burrow — a tunnel dug quietly underground to reach somewhere it has no business being. That's exactly what this tool does: bores through a bastion over SSH and surfaces inside your database as if the database were local.

## Claude Code Integration

After installing burrow, run `burrow skill install` to register the Claude Code skill. This teaches AI agents when and how to use burrow for database operations.

```bash
burrow skill install
```

The skill is installed to `~/.claude/skills/burrow/SKILL.md` — the standard path Claude Code and compatible agents scan at session startup.

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

After installing, register the Claude Code skill:

```bash
burrow skill install
```

## Upgrading

- **uv:**

  ```bash
  uv tool upgrade burrow
  burrow skill install   # re-install updated skill
  ```

- **pip:**

  ```bash
  pip install --upgrade git+https://github.com/nobleknightt/burrow.git
  burrow skill install   # re-install updated skill
  ```

## Setup

Run the interactive wizard to configure your first profile:

```bash
burrow config set
```

To configure additional named profiles (e.g. staging, prod), pass `--profile`:

```bash
burrow --profile staging config set
```

Passwords are never stored in `config.toml`. The wizard writes them to
`~/.config/burrow/profiles/<profile>.password` (mode `0600`). You can also set
`BURROW_DB_PASSWORD` in your environment.

## Configuration

Priority order (highest wins):

1. **Environment variables** — `BURROW_SSH_HOST`, `BURROW_DB_PASSWORD`, etc.
2. **Config file** — `~/.config/burrow/config.toml` (override with `$BURROW_CONFIG`)
3. **Built-in defaults** for optional fields

The config file supports named profiles. Passwords are stored separately — never in this file:

```toml
# PostgreSQL over SSH tunnel (use_ssh defaults to true when omitted)
[default]
db_type      = "postgres"
use_ssh      = true
ssh_host     = "bastion.example.com"
ssh_user     = "ec2-user"
ssh_key_path = "~/.ssh/id_rsa"
db_host      = "db.cluster.us-east-1.rds.amazonaws.com"
db_user      = "appuser"
db_name      = "appdb"
db_schema    = "public"

# MySQL over SSH tunnel
[mysql-prod]
db_type      = "mysql"
use_ssh      = true
ssh_host     = "bastion.example.com"
ssh_user     = "ec2-user"
ssh_key_path = "~/.ssh/id_rsa"
db_host      = "mysql.internal"
db_user      = "appuser"
db_name      = "appdb"

# Direct connection (no SSH)
[local]
db_type      = "postgres"
use_ssh      = false
db_host      = "localhost"
db_user      = "appuser"
db_name      = "appdb"
```

`use_ssh` defaults to `true`, so existing configs without it continue to work unchanged.

## Usage

```bash
# one-shot query
burrow query "SELECT id, name FROM users LIMIT 10"
burrow query "SELECT * FROM orders" --output json
burrow query "SELECT * FROM products" --output csv

# use a named profile
burrow --profile staging query "SELECT count(*) FROM users"

# inspect schema
burrow describe                               # list all tables
burrow describe --table users                 # columns, types, PKs
burrow describe --schema public --table users

# list all profiles
burrow config list

# configure a profile
burrow config set
burrow --profile staging config set

# remove a profile
burrow config unset default
burrow config unset staging

# check resolved config (passwords redacted)
burrow config get
burrow config get db_host
burrow --profile staging config get

# install Claude Code skill
burrow skill install
```
