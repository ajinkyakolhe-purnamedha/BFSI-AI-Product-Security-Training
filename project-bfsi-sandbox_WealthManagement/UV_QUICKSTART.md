# uv in 7 commands

Use these from your project's root folder. Commands that add or remove packages
change the project's dependencies; the package below is just an example.

| # | Command | Purpose |
| --- | --- | --- |
| 1 | `uv python install 3.13` | Install Python 3.13. |
| 2 | `uv python pin 3.13` | Save the project's Python choice in `.python-version`. |
| 3 | `uv init my-project` | Create a new project. Skip this for an existing repository. |
| 5 | `uv remove rich` | Remove that package from the project. |
| 6 | `uv sync` | Create/update `.venv` and install the project's dependencies. |
| 7 | `uv run python -m pytest -q` | Run tests through the project's Python. |

## For this Chronos repository

Python 3.13 is already pinned. Include the optional AI dependencies:

```bash
uv sync --extra ai
uv run --extra ai python -m pytest -q
```

The same `uv run` command starts applications:

```bash
uv run --extra ai python -m uvicorn chronos.app_startup:app --reload
uv run --extra ai python -m streamlit run ui/app_navigation.py
```

Run the backend and UI in separate terminals.

Check the selected Python:

```bash
uv run python --version
```

`python -m pytest` loads pytest as a module. Without `-m`, Python looks for a
script named `pytest`. Using `uv run python -m ...` keeps the interpreter explicit;
no environment activation is needed.

## Remember four files

- `.python-version`: selected Python version.
- `pyproject.toml`: project dependencies and settings.
- `uv.lock`: exact dependency versions; commit it, let uv manage it.
- `.venv/`: local Python environment; keep it out of Git.

References: [Installing Python](https://docs.astral.sh/uv/guides/install-python/)
and [Working on projects](https://docs.astral.sh/uv/guides/projects/).
