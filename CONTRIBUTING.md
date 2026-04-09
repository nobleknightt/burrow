# Contributing

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it, then:

```bash
git clone https://github.com/nobleknightt/burrow.git
cd burrow
uv sync
uv tool install pre-commit
```

If this is your first `uv tool install`, restart your shell so `~/.local/bin` is on `PATH`, then:

```bash
pre-commit install
```

## Running tests

```bash
uv run pytest
```

## Adding a subcommand

1. Create `src/burrow/commands/<name>.py` with a `cmd_<name>(args)` function.
2. Add a subparser in `cli.py` → `build_parser()`.
3. Wire it in `main()`.
4. Add tests in `tests/test_commands_<name>.py`.
