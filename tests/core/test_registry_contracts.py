from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

import registers.cli as cli
import registers.cron as cron
from registers.core.contracts import RegistryAccessorContract, RegistryLifecycleContract
from registers.db.registry import DatabaseRegistry


class ContractModel(BaseModel):
    id: int | None = None
    name: str


def test_cli_and_cron_registry_lifecycle_contracts() -> None:
    cli_registry = cli.CommandRegistry()
    cron_registry = cron.CronRegistry()

    assert isinstance(cli_registry, RegistryLifecycleContract)
    assert isinstance(cron_registry, RegistryLifecycleContract)


def test_db_registry_accessor_contract(tmp_path: Path) -> None:
    registry = DatabaseRegistry(
        ContractModel,
        tmp_path / "contracts.db",
        table_name="contract_models",
        key_field="id",
        autoincrement=True,
    )

    assert isinstance(registry, RegistryAccessorContract)
    assert registry.get_registry() is registry
