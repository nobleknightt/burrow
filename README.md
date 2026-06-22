# burrow

CLI for querying PostgreSQL and MySQL databases — directly or through an SSH tunnel to a bastion host.

Named after the mole's burrow — a tunnel dug quietly underground to reach somewhere it has no business being. That's exactly what this tool does: bores through a bastion over SSH and surfaces inside your database as if the database were local.

## Agent Skills

burrow ships an [Agent Skills](https://agentskills.io) skill. Run `burrow skill install` after installing to register it — the agent will then know when and how to use burrow automatically.

```bash
burrow skill install
```

Installs to `~/.agents/skills/burrow/SKILL.md` — the universal [Agent Skills](https://agentskills.io) path supported by Codex, Cursor, GitHub Copilot, OpenCode, and others. To install for a specific agent or a custom directory:

```bash
burrow skill install --agent claude-code
burrow skill install --agent cursor,copilot
burrow skill install --path /path/to/skills/dir
```

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

After installing, register the agent skill:

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

To update a single field without running the full wizard:

```bash
burrow config set db_host <value>
burrow config set access_mode read
burrow config set db_port 5433
burrow --profile staging config set db_name <value>
```

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
ssh_host     = "ssh.example.com"
ssh_user     = "sshuser"
ssh_key_path = "~/.ssh/id_rsa"
db_host      = "db.example.com"
db_user      = "appuser"
db_name      = "appdb"
db_schema    = "public"
access_mode  = "readwrite"

# Read-only replica (access_mode = "read" blocks INSERT/UPDATE/DELETE/DDL)
[readonly]
db_type      = "postgres"
use_ssh      = true
ssh_host     = "ssh.example.com"
ssh_user     = "sshuser"
ssh_key_path = "~/.ssh/id_rsa"
db_host      = "db-replica.example.com"
db_user      = "appuser"
db_name      = "appdb"
access_mode  = "read"

# MySQL over SSH tunnel
[mysql-prod]
db_type      = "mysql"
use_ssh      = true
ssh_host     = "ssh.example.com"
ssh_user     = "sshuser"
ssh_key_path = "~/.ssh/id_rsa"
db_host      = "db.example.com"
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

> [!WARNING]
> `access_mode = "read"` is a client-side guard — it blocks common write statements (INSERT,
> UPDATE, DELETE, TRUNCATE, DDL) but does not enforce read-only at the database level. For true
> read-only access, use database credentials that only have SELECT privileges.

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

# configure a profile (interactive wizard)
burrow config set
burrow --profile staging config set

# update a single field
burrow config set db_host <value>
burrow config set access_mode read
burrow config set db_port 5433
burrow --profile staging config set db_name <value>

# remove a profile
burrow config unset default
burrow config unset staging

# check resolved config (passwords redacted)
burrow config get
burrow config get db_host
burrow --profile staging config get

# install agent skill
burrow skill install
```
