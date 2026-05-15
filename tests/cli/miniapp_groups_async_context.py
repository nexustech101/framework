from __future__ import annotations

import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import registers.cli as cli

registry = cli.CommandRegistry()


class OpsContext(cli.Context):
    def __init__(self, env: str = "prod", region: str = "us-east-1") -> None:
        self.env = env
        self.region = region


@registry.context_factory
def build_context(env: str = "prod", region: str = "us-east-1") -> OpsContext:
    return OpsContext(env=env, region=region)


services = registry.group("services", description="Service inventory", aliases=["svc"], tags=["inventory"])
deploy = registry.group("deploy", description="Deployment workflows", aliases=["d"], tags=["deploy"])
incidents = registry.group("incidents", description="Incident runbooks", aliases=["inc"], tags=["ops"])


def service_inventory(ctx: OpsContext) -> list[dict[str, str]]:
    return [
        {"env": ctx.env, "region": ctx.region, "service": "api", "owner": "platform"},
        {"env": ctx.env, "region": ctx.region, "service": "worker", "owner": "automation"},
        {"env": ctx.env, "region": ctx.region, "service": "billing", "owner": "finance-eng"},
    ]


def print_service_table(rows: list[dict[str, str]]) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
    except Exception:
        headers = ["service", "owner", "env", "region"]
        widths = {
            header: max(len(header), *(len(row[header]) for row in rows))
            for header in headers
        }
        print("  ".join(header.ljust(widths[header]) for header in headers))
        print("  ".join("-" * widths[header] for header in headers))
        for row in rows:
            print("  ".join(row[header].ljust(widths[header]) for header in headers))
        return

    table = Table(title="Service Inventory", show_lines=False)
    table.add_column("Service", style="bold cyan", no_wrap=True)
    table.add_column("Owner", style="white")
    table.add_column("Environment", style="green")
    table.add_column("Region", style="magenta")
    for row in rows:
        table.add_row(row["service"], row["owner"], row["env"], row["region"])
    Console().print(table)


@services.register(
    "list",
    description="List services in the selected environment",
    examples=[
        "ops services list",
        "ops --env stage --region us-west-2 services list",
        "ops svc list",
    ],
)
async def list_services(ctx: OpsContext) -> None:
    await asyncio.sleep(0)
    print_service_table(service_inventory(ctx))


@deploy.register(
    "service",
    description="Deploy one service with a safety preview",
    examples=[
        "ops deploy service api",
        "ops deploy service worker 2026.05.13 --dry-run",
        "ops d service billing latest",
    ],
)
@deploy.argument("name", type=cli.types.Choice(["api", "worker", "billing"]), help="Service to deploy")
@deploy.argument("version", default="latest", type=str, help="Artifact version")
@deploy.dry_run()
def deploy_service(ctx: OpsContext, name: str, version: str, dry_run: bool = False) -> str:
    action = "Would deploy" if dry_run else "Deploying"
    return f"{action} {name}:{version} to {ctx.env}/{ctx.region}"


@incidents.register(
    "page",
    description="Prepare a page for the owning team",
    default_output="json",
    examples=[
        "ops incidents page api sev1",
        "ops incidents page worker",
        "ops inc page billing sev2",
    ],
)
@incidents.argument("service", type=cli.types.Choice(["api", "worker", "billing"]), help="Impacted service")
@incidents.argument("severity", type=cli.types.Choice(["sev1", "sev2", "sev3"]), default="sev2")
def page_team(ctx: OpsContext, service: str, severity: str = "sev2") -> dict[str, str]:
    owner = {"api": "platform", "worker": "automation", "billing": "finance-eng"}[service]
    return {
        "env": ctx.env,
        "region": ctx.region,
        "service": service,
        "severity": severity,
        "page": f"{owner}-oncall",
    }


if __name__ == "__main__":
    registry.run(
        shell_title="Ops Desk",
        shell_description="Inspect services, deploy safely, and prepare incident pages.",
        shell_usage=True,
    )
