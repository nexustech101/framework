"""
All package-defined exceptions in one place.

Hierarchy
---------
RegistryError                     ← base; safe to catch everything
├── ConfigurationError            ← bad decorator args, bad field refs
├── ModelRegistrationError        ← model class cannot be decorated
├── SchemaError                   ← DDL failures
│   └── MigrationError            ← schema evolution failures
├── RelationshipError             ← misconfigured relationship descriptor
├── DuplicateKeyError             ← INSERT collides on primary key
├── UniqueConstraintError         ← INSERT/UPDATE violates UNIQUE column
├── RecordNotFoundError           ← require() / require_related() found nothing
└── InvalidQueryError             ← malformed criteria or unknown fields
"""

from __future__ import annotations

from typing import Any

from registers.core.errors import FrameworkErrorBase


class RegistryError(FrameworkErrorBase):
    """Base class for all registers.db exceptions with optional structured context."""

    def __init__(
        self,
        message: str | None = None,
        *,
        operation: str | None = None,
        model: str | None = None,
        table: str | None = None,
        field: str | None = None,
        details: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **extra: Any,
    ) -> None:
        payload: dict[str, Any] = {}
        if model is not None:
            payload["model"] = model
        if table is not None:
            payload["table"] = table
        if field is not None:
            payload["field"] = field
        if context:
            payload.update(context)

        payload.update({key: value for key, value in extra.items() if value is not None})

        super().__init__(
            message or self.__class__.__name__,
            operation=operation,
            module="db",
            details=details,
            context=payload,
        )

        self.model = model
        self.table = table
        self.field = field


class ConfigurationError(RegistryError):
    """Raised when decorator options or field references are invalid."""


class ModelRegistrationError(RegistryError):
    """Raised when a model class cannot be safely decorated."""


class SchemaError(RegistryError):
    """Raised when a DDL operation (CREATE/DROP/ALTER) fails."""


class MigrationError(SchemaError):
    """Raised when a schema evolution step cannot be applied."""


class RelationshipError(RegistryError):
    """Raised when a relationship descriptor is misconfigured or misused."""


class DuplicateKeyError(RegistryError):
    """Raised when an INSERT collides with an existing primary-key value."""


class InvalidPrimaryKeyAssignmentError(RegistryError):
    """Raised when callers assign a database-managed primary key explicitly."""


class ImmutableFieldError(RegistryError):
    """Raised when an immutable persisted field is mutated."""


class UniqueConstraintError(RegistryError):
    """Raised when an INSERT or UPDATE violates a UNIQUE constraint."""


class RecordNotFoundError(RegistryError):
    """Raised by require() and require_related() when no row matches."""


class InvalidQueryError(RegistryError):
    """Raised when filter criteria reference unknown fields or are malformed."""
