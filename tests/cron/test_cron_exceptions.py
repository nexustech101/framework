from __future__ import annotations

import pytest

import registers.cron as cron
from registers.cron.exceptions import CronRegistrationError, CronTriggerError, CronWorkspaceError
from registers.cron.state import clear_state_caches
from registers.cron.workspace import register_workflow


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    cron.reset_registry()
    clear_state_caches()
    yield
    cron.reset_registry()
    clear_state_caches()


def test_duplicate_job_registration_raises_typed_error() -> None:
    @cron.job(name="sync", trigger=cron.interval(seconds=10))
    def _one() -> None:
        return None

    with pytest.raises(CronRegistrationError):
        @cron.job(name="sync", trigger=cron.interval(seconds=20))
        def _two() -> None:
            return None


def test_trigger_validation_raises_typed_error() -> None:
    with pytest.raises(CronTriggerError):
        cron.interval(seconds=0)

    with pytest.raises(CronTriggerError):
        cron.event("webhook", path="missing-leading-slash")


def test_workspace_validation_raises_typed_error(tmp_path) -> None:
    with pytest.raises(CronWorkspaceError):
        register_workflow(
            root=tmp_path,
            name="",
            file_path="ops/workflows/ci/deploy.yml",
            job_name="deploy-job",
        )
