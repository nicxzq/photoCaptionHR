# Contributing

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Checks

Run these before opening a pull request:

```powershell
python -m compileall core utils main.py gui.py
```

If you add tests, include the command in this file and keep it reproducible without private images or local model caches.

## Pull Requests

- Keep changes focused.
- Do not commit generated PyInstaller output from `build/`, `dist/`, or `release/`.
- Do not commit private images, local exports, credentials, or machine-specific config.
- Use synthetic or explicitly redistributable data for examples and tests.
