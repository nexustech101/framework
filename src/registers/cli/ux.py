"""Plain-text presentation and runtime helpers for :mod:`registers.cli`."""

from __future__ import annotations

from contextlib import contextmanager
import asyncio
import csv
import io
import json
import logging
from typing import Any, Awaitable


class Context:
    """Base class for CLI context objects."""


def print_result(result: Any, *, output: str | None, render: bool = True) -> None:
    text = format_result(result, mode=output or "plain", render=render)
    if text is not None:
        print(text)


def format_result(result: Any, *, mode: str = "plain", render: bool = True) -> str | None:
    if result is None:
        return None
    if not render or mode == "plain":
        return str(result)
    if mode == "json":
        return json.dumps(result, indent=2, sort_keys=True, default=str)
    if mode == "csv":
        return _to_csv(result)
    return _to_plain_structured(result)


def format_error(title: str, message: str) -> str:
    return f"Error: {message}" if title.lower() != "error" else f"Error: {message}"


def run_awaitable(awaitable: Awaitable[Any], *, event_loop: Any | None = None) -> Any:
    if event_loop is not None:
        return event_loop.run_until_complete(awaitable)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("run() cannot execute an async command while an event loop is already running; use run_async().")


async def await_if_needed(value: Any) -> Any:
    if asyncio.iscoroutine(value) or isinstance(value, Awaitable):
        return await value
    return value


@contextmanager
def capture_logs(enabled: bool, *, level: str | int | None = None) -> Any:
    if not enabled:
        yield ""
        return

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    old_level = root.level
    if level is not None:
        root.setLevel(level if isinstance(level, int) else getattr(logging, str(level).upper(), logging.INFO))
    root.addHandler(handler)
    try:
        yield stream
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)


def _to_csv(result: Any) -> str:
    rows: list[dict[str, Any]]
    if isinstance(result, list) and all(isinstance(item, dict) for item in result):
        rows = result
    elif isinstance(result, dict):
        rows = [result]
    else:
        return str(result)
    if not rows:
        return ""
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().rstrip("\r\n")


def _to_plain_structured(result: Any) -> str:
    if isinstance(result, dict):
        return "\n".join(f"{key}: {value}" for key, value in result.items())
    if isinstance(result, list):
        if all(isinstance(item, dict) for item in result):
            return _plain_table(result)
        return "\n".join(f"- {item}" for item in result)
    return str(result)


def _plain_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers = list(dict.fromkeys(key for row in rows for key in row))
    widths = {
        header: max(len(str(header)), *(len(str(row.get(header, ""))) for row in rows))
        for header in headers
    }
    lines = ["  ".join(str(header).ljust(widths[header]) for header in headers)]
    lines.append("  ".join("-" * widths[header] for header in headers))
    for row in rows:
        lines.append("  ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers))
    return "\n".join(lines)
