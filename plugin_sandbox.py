"""Restricted out-of-process plugin runner for VT2.

The runner executes a plugin in a child Python process with a tiny injected API.
It is a defense-in-depth layer: plugins no longer receive the full in-process
VtAPI object and cannot directly mutate the GUI process.
"""

from __future__ import annotations

import argparse
import builtins
import importlib.util
import json
import os
import sys

try:
    import resource
except ImportError:  # pragma: no cover - Windows fallback
    resource = None
import traceback
from multiprocessing.connection import Connection
from typing import Any


SAFE_IMPORT_ROOTS = {
    "base64",
    "collections",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "functools",
    "hashlib",
    "heapq",
    "html",
    "itertools",
    "json",
    "math",
    "operator",
    "random",
    "re",
    "statistics",
    "string",
    "time",
    "typing",
    "uuid",
    "_io",
}

BLOCKED_BUILTINS = {
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "input",
    "open",
}


class SandboxViolation(PermissionError):
    """Raised when a plugin tries to use functionality outside the injected API."""


class InjectedPluginAPI:
    """Small capability-based API injected into sandboxed plugins."""

    def __init__(self, conn: Connection, manifest: dict[str, Any]):
        self._conn = conn
        self._manifest = manifest

    @property
    def plugin_name(self) -> str:
        return str(self._manifest.get("name") or "Unknown")

    def log(self, message: Any, level: str = "INFO") -> None:
        self._send_event("log", {"message": str(message), "level": str(level)})

    def status_message(self, message: Any, timeout: int = 0) -> None:
        self._send_event("status_message", {"message": str(message), "timeout": int(timeout)})

    def register_command(self, name: str, title: str | None = None, description: str = "") -> None:
        self._send_event(
            "register_command",
            {
                "name": str(name),
                "title": str(title or name),
                "description": str(description),
            },
        )

    def _send_event(self, event: str, payload: dict[str, Any]) -> None:
        self._conn.send({"type": "event", "event": event, "payload": payload})


class RestrictedImporter:
    def __init__(self, allowed_roots: set[str]):
        self._allowed_roots = allowed_roots
        self._original_import = builtins.__import__

    def __enter__(self):
        builtins.__import__ = self._import_hook
        return self

    def __exit__(self, exc_type, exc, tb):
        builtins.__import__ = self._original_import

    def _import_hook(self, name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".", 1)[0]
        if level != 0 or root not in self._allowed_roots:
            raise SandboxViolation(f"Import '{name}' is blocked in sandboxed plugins")
        return self._original_import(name, globals, locals, fromlist, level)


def apply_process_limits(memory_mb: int, cpu_seconds: int) -> None:
    if os.name != "posix" or resource is None:
        return
    memory_bytes = max(16, memory_mb) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (max(1, cpu_seconds), max(1, cpu_seconds + 1)))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    except (ValueError, OSError):
        # Some Linux/container combinations do not allow lowering this limit.
        pass


def make_safe_builtins() -> dict[str, Any]:
    safe = dict(vars(builtins))
    for name in BLOCKED_BUILTINS:
        safe[name] = _blocked_builtin(name)
    safe["__import__"] = _safe_import
    return safe


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".", 1)[0]
    if level != 0 or root not in SAFE_IMPORT_ROOTS:
        raise SandboxViolation(f"Import '{name}' is blocked in sandboxed plugins")
    return builtins.__import__(name, globals, locals, fromlist, level)


def _blocked_builtin(name: str):
    def blocked(*args, **kwargs):
        raise SandboxViolation(f"Builtin '{name}' is blocked in sandboxed plugins")

    return blocked


def load_plugin_module(plugin_file: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, plugin_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load plugin module from {plugin_file}")
    module = importlib.util.module_from_spec(spec)
    module.__builtins__ = make_safe_builtins()
    sys.modules[module_name] = module
    with RestrictedImporter(SAFE_IMPORT_ROOTS):
        spec.loader.exec_module(module)
    return module


def dispatch_command(module, api: InjectedPluginAPI, command: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
    commands = getattr(module, "COMMANDS", None)
    if isinstance(commands, dict) and command in commands:
        return commands[command](api, *args, **kwargs)
    func = getattr(module, command, None)
    if callable(func) and not command.startswith("_"):
        return func(api, *args, **kwargs)
    raise AttributeError(f"Sandboxed plugin command '{command}' not found")


def send_ready(conn: Connection) -> None:
    conn.send({"type": "ready"})


def send_error(conn: Connection, message: str) -> None:
    conn.send({"type": "error", "message": message})


def run_child(conn: Connection, plugin_file: str, manifest_json: str, memory_mb: int, cpu_seconds: int) -> None:
    manifest = json.loads(manifest_json)
    try:
        apply_process_limits(memory_mb, cpu_seconds)
        api = InjectedPluginAPI(conn, manifest)
        module = load_plugin_module(plugin_file, f"vt2_sandbox_{os.getpid()}")
        init = getattr(module, "initAPI", None)
        if callable(init):
            init(api)
        send_ready(conn)
        while True:
            try:
                msg = conn.recv()
            except EOFError:
                break
            if not isinstance(msg, dict):
                continue
            if msg.get("type") == "shutdown":
                break
            if msg.get("type") != "run":
                continue
            request_id = msg.get("id")
            try:
                result = dispatch_command(
                    module,
                    api,
                    str(msg.get("command")),
                    list(msg.get("args") or []),
                    dict(msg.get("kwargs") or {}),
                )
                conn.send({"type": "result", "id": request_id, "ok": True, "result": result})
            except Exception:
                conn.send({"type": "result", "id": request_id, "ok": False, "error": traceback.format_exc()})
    except Exception:
        send_error(conn, traceback.format_exc())
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a VT2 plugin in a restricted child process")
    parser.add_argument("--fd", type=int, required=True)
    parser.add_argument("--plugin-file", required=True)
    parser.add_argument("--manifest-json", required=True)
    parser.add_argument("--memory-mb", type=int, default=64)
    parser.add_argument("--cpu-seconds", type=int, default=2)
    args = parser.parse_args(argv)

    conn = Connection(args.fd)
    run_child(conn, args.plugin_file, args.manifest_json, args.memory_mb, args.cpu_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
