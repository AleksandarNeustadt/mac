# Contributing

Thanks for considering contributing to MAC!

## Workflow
1. Fork the repo and create a feature branch from `main`.
2. Install dev tools and pre-commit hooks:
   ```bash
   pip install -e .
   pip install pre-commit
   pre-commit install
   ```
3. Make your changes and ensure code style/tests pass:
   ```bash
   ruff --fix .
   black .
   pytest -q
   ```
4. Write tests for new features / bug fixes.
5. Open a Pull Request with a clear description and, if relevant, logs or screenshots.

## Commit Style
Use conventional commits when possible, e.g.:
- `feat: add json atomic write`
- `fix: handle wal flush error`
- `refactor: split sqlite driver`
- `docs: add EN/DE/SR docs links`

## Code Style
- Python 3.10+
- Format with `black`, lint with `ruff`.
