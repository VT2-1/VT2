# VT2

VT2 is a PySide6 text editor with a plugin API. Plugins are trusted Python code and run with the same permissions as the application.

## Requirements

- Python 3.12+
- Linux packages required by Qt/PySide6, including OpenGL (`libGL.so.1` on many distributions)
- Python dependencies from `requirements.txt`

## Setup

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The repository includes a pure-Python `api.py` fallback so the app can run on non-Windows platforms. The Cython source remains in `API2Compile/api.pyx` for optional compiled builds.

## Run

```bash
python main.py
```

## Test

For headless Linux CI, set Qt to offscreen mode:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

## Plugins and security

Plugins are not sandboxed. Install plugins only from trusted sources. The automatic Basic plugin installer validates ZIP member paths before extraction, but downloaded plugin code is still trusted application code.
