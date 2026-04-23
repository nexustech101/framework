"""
Public decorator API for ``registers.cron``.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from registers.cron.registry import CronRegistry, TriggerSpec


_default_registry = CronRegistry()  # Singleton registry instance for the module
_active_registry: ContextVar[CronRegistry | None] = ContextVar(
    "registers.cron.active_registry",
    default=None,
)


def _resolve_registry() -> CronRegistry:
    registry = _active_registry.get()
    return _default_registry if registry is None else registry


@contextmanager
def use_registry(registry: CronRegistry):
    """
    Temporarily route module-level decorators to ``registry``.

    This preserves module-level ergonomics while supporting isolated import/discovery.
    """
    token = _active_registry.set(registry)
    try:
        yield registry
    finally:
        _active_registry.reset(token)


def job(
    name: str | None = None,
    *,
    trigger: TriggerSpec,
    target: str = "local_async",
    deployment_file: str = "",
    enabled: bool = True,
    max_runtime: int = 0,
    tags: tuple[str, ...] | list[str] | None = None,
    overlap_policy: str = "skip",
    retry_policy: str = "none",
    retry_max_attempts: int = 0,
    retry_backoff_seconds: float = 0.0,
    retry_max_backoff_seconds: float = 0.0,
    retry_jitter_seconds: float = 0.0,
):
    """Register a decorated callable as a cron job."""

    def decorator(fn: Any) -> Any:
        _resolve_registry().register(
            fn,
            name=name,
            trigger=trigger,
            target=target,
            deployment_file=deployment_file,
            enabled=enabled,
            max_runtime=max_runtime,
            tags=tags,
            overlap_policy=overlap_policy,
            retry_policy=retry_policy,
            retry_max_attempts=retry_max_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            retry_max_backoff_seconds=retry_max_backoff_seconds,
            retry_jitter_seconds=retry_jitter_seconds,
        )
        return fn
    return decorator


# Utility functions to access and manage the singleton registry instance
def get_registry() -> CronRegistry:
    return _resolve_registry()


# This function is primarily for testing purposes to reset the registry state
def reset_registry() -> None:
    _default_registry.clear()
