"""
Shared internal primitives used across registers modules.
"""

from registers.core.contracts import (
    RegistryAccessorContract,
    RegistryCollectionContract,
    RegistryLifecycleContract,
)
from registers.core.errors import FrameworkErrorBase
from registers.core.logging import log_exception

__all__ = [
    "FrameworkErrorBase",
    "log_exception",
    "RegistryAccessorContract",
    "RegistryCollectionContract",
    "RegistryLifecycleContract",
]
