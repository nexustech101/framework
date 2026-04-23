"""
Typed cron exceptions with backward-compatible builtin inheritance.
"""

from __future__ import annotations

from typing import Any

from registers.core.errors import FrameworkErrorBase


class CronError(FrameworkErrorBase):
    """Base class for cron module errors."""

    def __init__(
        self,
        message: str | None = None,
        *,
        context: dict[str, Any] | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(
            message or self.__class__.__name__,
            module="cron",
            context=context,
            **extra,
        )


class CronRegistrationError(CronError, ValueError):
    """Raised when a cron job cannot be registered due to invalid metadata."""


class CronTriggerError(CronRegistrationError):
    """Raised when trigger helper input is invalid."""


class CronLookupError(CronError, KeyError):
    """Raised when a requested cron job cannot be found."""


class CronRuntimeError(CronError, RuntimeError):
    """Raised for cron runtime failures."""


class CronWorkspaceError(CronError, ValueError):
    """Raised for invalid workspace/workflow configuration."""


class CronWorkspaceRuntimeError(CronRuntimeError):
    """Raised when workflow execution cannot be launched."""


class CronAdapterError(CronRuntimeError):
    """Raised for deployment adapter command and host compatibility failures."""
