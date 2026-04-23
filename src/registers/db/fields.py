from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from pydantic import Field

from registers.db.exceptions import ConfigurationError


_FK_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def _require_bool(name: str, value: bool) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(
            f"db_field({name}=...) must be a bool, got {type(value).__name__}."
        )
    return value


def _normalize_foreign_key(foreign_key: str | None) -> str | None:
    if foreign_key is None:
        return None
    if not isinstance(foreign_key, str):
        raise ConfigurationError(
            f"db_field(foreign_key=...) must be a string in 'table.column' format, "
            f"got {type(foreign_key).__name__}."
        )
    normalized = foreign_key.strip()
    if not normalized or not _FK_PATTERN.match(normalized):
        raise ConfigurationError(
            "db_field(foreign_key=...) must use 'table.column' format."
        )
    return normalized


def db_field(
    *,
    primary_key: bool = False,
    autoincrement: bool = False,
    unique: bool = False,
    index: bool = False,
    foreign_key: str | None = None,
    **kwargs: Any,
) -> Field:
    normalized_foreign_key = _normalize_foreign_key(foreign_key)

    return Field(
        json_schema_extra={
            "db_primary_key": _require_bool("primary_key", primary_key),
            "db_autoincrement": _require_bool("autoincrement", autoincrement),
            "db_unique": _require_bool("unique", unique),
            "db_index": _require_bool("index", index),
            "db_foreign_key": normalized_foreign_key,
        },
        **kwargs,
    )


def get_db_field_metadata(field_info: Any) -> dict[str, Any]:
    """Return normalized db_field metadata from a Pydantic FieldInfo object."""
    metadata = getattr(field_info, "json_schema_extra", None)
    if not isinstance(metadata, Mapping):
        return {}

    return {
        "db_primary_key": bool(metadata.get("db_primary_key", False)),
        "db_autoincrement": bool(metadata.get("db_autoincrement", False)),
        "db_unique": bool(metadata.get("db_unique", False)),
        "db_index": bool(metadata.get("db_index", False)),
        "db_foreign_key": metadata.get("db_foreign_key"),
    }
