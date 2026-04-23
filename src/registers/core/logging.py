"""
Shared logging helpers.
"""

from __future__ import annotations

import logging
from typing import Any

from registers.core.errors import FrameworkErrorBase


def log_exception(
    logger: logging.Logger,
    level: int,
    message: str,
    *,
    error: BaseException | None = None,
    **context: Any,
) -> None:
    """
    Log an exception with structured context in a backend-agnostic way.
    """
    payload = {key: value for key, value in context.items() if value is not None}
    if isinstance(error, FrameworkErrorBase):
        payload.setdefault("error_type", type(error).__name__)
        payload.update(error.context)

    exc_info: Any
    if error is None:
        exc_info = True
    else:
        exc_info = (type(error), error, error.__traceback__)

    logger.log(level, message, extra={"registers_context": payload}, exc_info=exc_info)
