# VT2

VT2 is a PySide6 text editor with a plugin API.

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

## Sandboxed plugins

Plugins can be loaded in a separate Python process when their `config.vt-conf` contains `"sandbox": true`. Legacy plugins without this key continue to run in-process for compatibility, but new plugins should opt into sandboxing. The GUI process injects a small capability API instead of passing the full `VtAPI` object:

- `api.log(message, level="INFO")`
- `api.status_message(message, timeout=0)`
- `api.register_command(name, title=None, description="")`
- `api.plugin_name`

The sandbox runner blocks dangerous builtins such as `open`, `eval`, `exec`, and `compile`, restricts imports to a small allowlist, applies CPU/memory/file-size limits on POSIX systems, and communicates with the GUI only over a message pipe.

This is a defense-in-depth sandbox, not a full VM/container boundary. Keep installing plugins only from trusted sources, but prefer sandboxed plugins and avoid legacy in-process plugins (`"sandbox": false`) unless absolutely necessary.

## Demo sandbox plugin

A minimal plugin is provided in `demo_plugins/SafeDemo`. It demonstrates both normal injected API usage and blocked harmful operations:

- `safe_demo` logs through the injected API and shows a status message.
- `try_harm_device` attempts file write and `subprocess` import; both are blocked by the sandbox.

To try it in the app, copy `demo_plugins/SafeDemo` into your configured `Packages/Plugins` directory and restart VT2.
