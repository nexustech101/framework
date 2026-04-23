"""
All registers-level exceptions in one place. Application code can catch
these without importing from deeper registers modules.
"""

from __future__ import annotations

from typing import Any

from registers.core.errors import FrameworkErrorBase


class FrameworkError(FrameworkErrorBase):
    """Base class for all registers CLI errors."""

    def __init__(
        self,
        message: str | None = None,
        *,
        context: dict[str, Any] | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(
            message or self.__class__.__name__,
            module="cli",
            context=context,
            **extra,
        )


class DuplicateCommandError(FrameworkError):
    """Raised when a command name is registered more than once."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Command '{name}' is already registered.", command=name)
        self.name = name


class UnknownCommandError(FrameworkError):
    """Raised when a requested command has no registered handler."""

    def __init__(self, name: str) -> None:
        super().__init__(f"No command registered for '{name}'.", command=name)
        self.name = name


class DependencyNotFoundError(FrameworkError):
    """Raised when the DI container cannot resolve a requested type."""

    def __init__(self, dep_type: Any) -> None:
        dep_name = getattr(dep_type, "__name__", repr(dep_type))
        super().__init__(
            f"No instance registered for type '{dep_name}'. "
            "Register it with container.register() before dispatching.",
            dependency=dep_name,
        )
        self.dep_type = dep_type


class CommandExecutionError(FrameworkError):
    """Raised by CommandRegistry.run() when a handler fails unexpectedly."""

    def __init__(self, command: str, reason: str) -> None:
        super().__init__(
            f"Command '{command}' failed: {reason}",
            command=command,
            reason=reason,
        )
        self.command = command
        self.reason = reason


class PluginLoadError(FrameworkError):
    """Raised when a plugin module fails to import."""

    def __init__(self, module_path: str, reason: str) -> None:
        super().__init__(
            f"Failed to load plugin '{module_path}': {reason}",
            plugin=module_path,
            reason=reason,
        )
        self.module_path = module_path
        self.reason = reason
