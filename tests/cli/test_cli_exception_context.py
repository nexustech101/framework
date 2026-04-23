from __future__ import annotations

from registers.cli.exceptions import CommandExecutionError, FrameworkError


def test_framework_error_supports_structured_context() -> None:
    err = FrameworkError("cli failure", request_id="abc123", operation="run")
    payload = err.to_dict()

    assert payload["type"] == "FrameworkError"
    assert payload["message"] == "cli failure"
    assert payload["module"] == "cli"
    assert payload["request_id"] == "abc123"
    assert payload["operation"] == "run"


def test_command_execution_error_exposes_context_payload() -> None:
    err = CommandExecutionError("sync", "boom")
    payload = err.to_dict()

    assert payload["message"] == "Command 'sync' failed: boom"
    assert payload["command"] == "sync"
    assert payload["reason"] == "boom"
