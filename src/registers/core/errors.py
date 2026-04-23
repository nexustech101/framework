"""
Shared framework error primitives.
"""

from __future__ import annotations

from typing import Any


class FrameworkErrorBase(Exception):
    """
    Base error with optional structured context payload.

    Context keys are additive and intended for structured logs or API responses.
    """

    def __init__(
        self,
        message: str | None = None,
        *,
        operation: str | None = None,
        module: str | None = None,
        entity: str | None = None,
        details: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(message or self.__class__.__name__)

        payload: dict[str, Any] = {}
        if operation is not None:
            payload["operation"] = operation
        if module is not None:
            payload["module"] = module
        if entity is not None:
            payload["entity"] = entity
        if details is not None:
            payload["details"] = details

        if context:
            payload.update(context)
        payload.update({key: value for key, value in extra.items() if value is not None})

        self.operation = operation
        self.module = module
        self.entity = entity
        self.details = details
        self.context = payload

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": type(self).__name__,
            "message": str(self),
            **self.context,
        }
