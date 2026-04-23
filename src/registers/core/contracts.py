"""
Shared Protocol contracts for registry-style modules.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, TypeVar, runtime_checkable


RegistryT = TypeVar("RegistryT")
EntryT = TypeVar("EntryT")


@runtime_checkable
class RegistryAccessorContract(Protocol[RegistryT]):
    """Contract for modules exposing an instance accessor helper."""

    def get_registry(self) -> RegistryT:
        ...


@runtime_checkable
class RegistryCollectionContract(Protocol[EntryT]):
    """Contract for in-memory map-like registries used by decorators."""

    def all(self) -> Mapping[str, EntryT]:
        ...

    def clear(self) -> None:
        ...

    def __len__(self) -> int:
        ...


@runtime_checkable
class RegistryLifecycleContract(
    RegistryAccessorContract[Any],
    RegistryCollectionContract[Any],
    Protocol,
):
    """Combined lifecycle contract for registries with reset semantics."""

    def reset_registry(self) -> None:
        ...
