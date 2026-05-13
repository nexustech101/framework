from __future__ import annotations

from datetime import date

import registers.cli as cli

registry = cli.CommandRegistry()

SERVICES = {
    "api": {"owner": "platform", "risk": "medium", "checks": "db,cache,queue"},
    "worker": {"owner": "automation", "risk": "low", "checks": "queue,cron"},
    "billing": {"owner": "finance-eng", "risk": "high", "checks": "db,payments,ledger"},
}


@registry.register(name="plan", description="Show the release plan for a service", default_output="json")
@registry.argument("service", type=cli.types.Choice(sorted(SERVICES)), help="Service name")
@registry.argument("version", type=str, help="Version to release")
@registry.option("--plan")
def plan_release(service: str, version: str) -> dict[str, object]:
    service_info = SERVICES[service]
    return {
        "service": service,
        "version": version,
        "owner": service_info["owner"],
        "risk": service_info["risk"],
        "date": date.today().isoformat(),
        "preflight": service_info["checks"].split(","),
    }


@registry.register(name="approve", description="Approve a release after preflight checks")
@registry.argument("service", type=cli.types.Choice(sorted(SERVICES)), help="Service name")
@registry.argument("version", type=str, help="Version to approve")
@registry.confirm("Approve {service} {version} for release?", confirm_phrase="approve {service} {version}")
@registry.option("--approve")
def approve_release(service: str, version: str) -> str:
    owner = SERVICES[service]["owner"]
    return f"Approved {service} {version}; notify {owner}."


@registry.register(name="deploy", description="Preview or run release deployment")
@registry.argument("service", type=cli.types.Choice(sorted(SERVICES)), help="Service name")
@registry.argument("version", type=str, help="Version to deploy")
@registry.dry_run()
@registry.option("--deploy")
def deploy_release(service: str, version: str, dry_run: bool = False) -> str:
    action = "Would deploy" if dry_run else "Deploying"
    return f"{action} {service} {version} with checks: {SERVICES[service]['checks']}"


if __name__ == "__main__":
    registry.run(
        shell_title="Release Desk",
        shell_description="Plan, approve, and deploy internal service releases.",
        shell_usage=True,
    )
