# `registers.cli`

`registers.cli` is a decorator-first runtime for small scripts, internal operator tools, and plugin-composed command surfaces. It keeps framework behavior plain and scriptable: command parsing, grouped command resolution, context injection, async execution, prompts, confirmations, dry-runs, output modes, plugins, and an aliasal interactive shell.

Rich is not part of the framework API. If a particular CLI script wants a Rich table or panel, use Rich directly inside that script and return `None` so `registers.cli` does not print a second result.

## 1. Quick Start: Todo CLI

Use the module-level facade for a small script with one command surface.

```python
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from time import strftime

from registers import CommandRegistry
import registers.db as db
from pydantic import BaseModel
from registers import db_field, DatabaseRegistry

DB_PATH = str(Path(__file__).with_suffix(".db"))
NOW = lambda: strftime("%Y-%m-%d %H:%M:%S")

cli = CommandRegistry()
db = DatabaseRegistry()

class TodoStatus(StrEnum):
    OPEN = "open"
    DONE = "done"


@db.database_registry(DB_PATH, table_name="todos", key_field="id")
class TodoItem(BaseModel):
    id: int | None = db_field(default=None, id_strategy="autoincrement")
    title: str = db_field(index=True)
    description: str = db_field(default="")
    status: TodoStatus = db_field(default=TodoStatus.OPEN)
    created_at: str = db_field(default_factory=NOW)


@cli.register(name="add", description="Create a todo item")
@cli.argument("title", type=str, help="Todo title")
@cli.argument("description", type=str, default="", help="aliasal details")
@cli.alias("--add")
@cli.alias("-a")
def add_todo(title: str, description: str = "") -> dict[str, object]:
    todo = TodoItem(title=title, description=description)
    todo.save()
    return {"id": todo.id, "title": todo.title, "status": todo.status.value}


@cli.register(name="list", description="List todo items", default_output="json")
@cli.argument("status", type=cli.types.Choice(["open", "done"]), default="open")
@cli.alias("--list")
@cli.alias("-l")
def list_todos(status: str = "open") -> list[dict[str, object]]:
    todos = TodoItem.objects.filter(status=TodoStatus(status))
    return [{"id": t.id, "title": t.title, "status": t.status.value} for t in todos]


@cli.register(name="complete", description="Mark a todo item as done")
@cli.argument("todo_id", type=int, help="Todo ID")
@cli.alias("--complete")
@cli.alias("-c")
def complete(todo_id: int) -> str:
    todo = TodoItem.objects.get(id=todo_id)
    if todo is None:
        return f"Todo {todo_id} was not found."
    todo.status = TodoStatus.DONE
    todo.save()
    return f"Completed todo {todo_id}: {todo.title}"


if __name__ == "__main__":
    cli.run(
        shell_title="Todo Console",
        shell_description="Manage local todo items.",
        shell_usage=True,
    )
```

Run:

```bash
python todos.py add "Buy milk" "2%"
python todos.py list
python todos.py list done
python todos.py complete 1
python todos.py --interactive
```

Important decorator behavior:

- `@register(name="...")` sets the public command name. Without `name=`, the first long alias is used, then the function name.
- `@argument("name", type=..., help="...")` declares a public command argument.
- `@argument(..., default=...)` makes the argument aliasal and shows the default in command help.
- `@option("--flag")` and `@alias("-f")` register command aliases.
- `@alias("--flag")` and `@alias("-f")` alias for `@option`.
- `default_output="json"` or `"csv"` sets a command’s normal structured output.
- `Choice([...])` validates values and displays choices in help and usage.

## 2. Script-Level Rich Output

Keep Rich as an application choice. This gives a specific command a polished operator view without adding Rich concepts to the framework.

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from registers import CommandRegistry

# ── Rich availability – checked once at import time ───────────────────────────
try:
    from rich.console import Console
    from rich.table import Table as RichTable
    _console = Console()
    _RICH = True
except ImportError:
    _RICH = False


# ── Lightweight column spec ───────────────────────────────────────────────────
@dataclass(frozen=True)
class Column:
    key: str
    header: str
    style: str = ""          # Rich style; ignored in plain fallback


# ── Single render_table that dispatches on availability ───────────────────────
def render_table(
    title: str,
    columns: list[Column],
    rows: list[dict[str, str]],
) -> None:
    if _RICH:
        _render_rich(title, columns, rows)
    else:
        _render_plain(columns, rows)


def _render_rich(
    title: str,
    columns: list[Column],
    rows: list[dict[str, str]],
) -> None:
    table = RichTable(title=title)
    for col in columns:
        table.add_column(col.header, style=col.style)
    for row in rows:
        table.add_row(*(row[col.key] for col in columns))
    _console.print(table)


def _render_plain(
    columns: list[Column],
    rows: list[dict[str, str]],
) -> None:
    keys = [col.key for col in columns]
    headers = [col.header for col in columns]
    widths = {
        col.key: max(len(col.header), *(len(row[col.key]) for row in rows))
        for col in columns
    }
    print("  ".join(h.ljust(widths[k]) for k, h in zip(keys, headers)))
    print("  ".join("-" * widths[k] for k in keys))
    for row in rows:
        print("  ".join(row[k].ljust(widths[k]) for k in keys))


# ── App wiring ────────────────────────────────────────────────────────────────
registry = CommandRegistry()

SERVICE_COLUMNS = [
    Column("service", "Service", style="bold cyan"),
    Column("owner",   "Owner"),
    Column("env",     "Environment", style="green"),
    Column("region",  "Region",      style="magenta"),
]


class OpsContext(cli.Context):
    def __init__(self, env: str = "prod", region: str = "us-east-1") -> None:
        self.env = env
        self.region = region


@registry.context_factory
def build_context(env: str = "prod", region: str = "us-east-1") -> OpsContext:
    return OpsContext(env, region)


services = registry.group("services", aliases=["svc"], description="Service inventory")


def service_rows(ctx: OpsContext) -> list[dict[str, str]]:
    return [
        {"service": "api",     "owner": "platform",    "env": ctx.env, "region": ctx.region},
        {"service": "worker",  "owner": "automation",  "env": ctx.env, "region": ctx.region},
        {"service": "billing", "owner": "finance-eng", "env": ctx.env, "region": ctx.region},
    ]


@services.register("list", description="List services in the selected environment")
async def list_services(ctx: OpsContext) -> None:
    await asyncio.sleep(0)
    render_table("Service Inventory", SERVICE_COLUMNS, service_rows(ctx))


if __name__ == "__main__":
    registry.run(
        shell_title="Ops Desk", 
        shell_usage=True
    )
```

Run:

```bash
python ops.py --env stage --region us-west-2 services list
python ops.py --interactive
```

The handler returns `None` because it owns printing. If a command returns a `dict` or `list`, the framework prints it using the selected output mode.

## 3. Groups, Plugins, Context, And Newer CLI Features

Use `CommandRegistry()` when a CLI has grouped commands, async handlers, plugins, context, or isolated command scopes.

```python
from __future__ import annotations

import asyncio
from registers import CommandRegistry

registry = cli.CommandRegistry()


class OpsContext(cli.Context):
    def __init__(self, env: str = "prod", region: str = "us-east-1") -> None:
        self.env = env
        self.region = region


@registry.context_factory
def build_context(env: str = "prod", region: str = "us-east-1") -> OpsContext:
    return OpsContext(env, region)


services = registry.group("services", description="Service inventory", aliases=["svc"])
deploy = registry.group("deploy", description="Deployment workflows", aliases=["d"])
incidents = registry.group("incidents", description="Incident runbooks", aliases=["inc"])


@services.register("list", description="List services", default_output="json")
async def list_services(ctx: OpsContext) -> list[dict[str, str]]:
    await asyncio.sleep(0)
    return [
        {"env": ctx.env, "region": ctx.region, "service": "api", "owner": "platform"},
        {"env": ctx.env, "region": ctx.region, "service": "worker", "owner": "automation"},
    ]


@deploy.register("service", description="Deploy one service with a safety preview")
@deploy.argument("name", type=cli.types.Choice(["api", "worker", "billing"]), help="Service to deploy")
@deploy.argument("version", type=str, default="latest", help="Artifact version")
@deploy.dry_run()
def deploy_service(ctx: OpsContext, name: str, version: str = "latest", dry_run: bool = False) -> str:
    action = "Would deploy" if dry_run else "Deploying"
    return f"{action} {name}:{version} to {ctx.env}/{ctx.region}"


@incidents.register("page", description="Prepare a page", default_output="json")
@incidents.argument("service", type=cli.types.Choice(["api", "worker", "billing"]), help="Impacted service")
@incidents.argument("severity", type=cli.types.Choice(["sev1", "sev2", "sev3"]), default="sev2")
def page_team(ctx: OpsContext, service: str, severity: str = "sev2") -> dict[str, str]:
    owner = {"api": "platform", "worker": "automation", "billing": "finance-eng"}[service]
    return {"env": ctx.env, "region": ctx.region, "service": service, "severity": severity, "page": f"{owner}-oncall"}
```

Run:

```bash
python ops.py --env stage services list
python ops.py --env stage svc list --output json
python ops.py deploy service api
python ops.py deploy service api 2026.05 --dry-run
python ops.py incidents page billing sev1
python ops.py help incidents
python ops.py help incidents page
```

Help surfaces choices and defaults:

```text
Command group: incidents, inc
  page <service: api|worker|billing> [severity: sev1|sev2|sev3]  Prepare a page

Arguments
  service   (choice: api | worker | billing, required)              Impacted service
  severity  (choice: sev1 | sev2 | sev3, aliasal, default='sev2')  -
```

Runtime flags:

- `--output json`, `--output csv`, `--output plain`
- `--quiet`
- `--no-color`
- `--force` for confirmed commands
- `--dry-run` for commands decorated with `@dry_run()`
- `--cli-output` when the command itself owns an `output` argument

Plugin composition keeps larger CLIs modular:

```python
from registers.cli import CommandRegistry
from cli.commands.billing import cli as billing_cli
from cli.commands.ops import cli as ops_cli
from cli.commands.users import cli as users_cli

registry = CommandRegistry()
registry.register_plugin(users_cli)
registry.register_plugin(billing_cli)
registry.register_plugin(ops_cli)

if __name__ == "__main__":
    registry.run(shell_title="Admin Console", shell_usage=True)
```

Each plugin can export its own registry:

```python
# cli/commands/users.py
from registers import CommandRegistry

cli = cli.CommandRegistry()
users = cli.group("users", aliases=["u"], description="User commands")


@users.register("list", description="List users", default_output="json")
def list_users() -> list[dict[str, str]]:
    return [{"email": "ada@example.com", "role": "admin"}]
```

Duplicate command names or aliases fail during registration; plugins do not silently overwrite each other.

## 4. Larger Internal CLI Tools

For larger internal tools, treat the CLI as a thin operator surface over application services. Keep the command layer small, explicit, and boring.

Recommended structure:

```text
internal_admin/
  app_context.py
  services/
    users.py
    billing.py
    deploys.py
  cli/
    main.py
    commands/
      users.py
      billing.py
      deploy.py
      incidents.py
```

Pattern:

```python
# cli/main.py
from registers.cli import CommandRegistry
from internal_admin.cli.commands.users import cli as users_cli
from internal_admin.cli.commands.billing import cli as billing_cli
from internal_admin.cli.commands.deploy import cli as deploy_cli

registry = CommandRegistry()
registry.register_plugin(users_cli)
registry.register_plugin(billing_cli)
registry.register_plugin(deploy_cli)


@registry.context_factory
def build_context(env: str = "prod", region: str = "us-east-1", profile: str = "default"):
    return AppContext(env=env, region=region, profile=profile)


if __name__ == "__main__":
    registry.run(
        shell_title="Internal Admin",
        shell_description="Operate users, billing, deployments, and incidents.",
        shell_usage=True,
        completion=True,
        history=True,
    )
```

Guidelines:

- Use `CommandRegistry()` for the host app and plugin registries.
- Use `group(...)` for domain areas such as `users`, `billing`, `deploy`, `incidents`, and `ops`.
- Use `context_factory` for environment, region, tenant, account, and profile selection.
- Use `Choice(...)` for public alias sets so help shows valid values.
- Use `default=...` on `argument(...)` when a missing value should be safe and predictable, such as `version="latest"` or `severity="sev2"`.
- Use `confirm(...)` for destructive actions and `dry_run()` for previewable workflows.
- Use `default_output="json"` or `default_output="csv"` for automation-friendly commands.
- Use app-level Rich only for commands that are meant for humans, not for data that scripts consume.
- Keep shell built-ins simple: `help`, `commands`, `exec`, `exit`, and `quit`.
- Prefer miniapp verification scripts over presentation-sensitive unit tests for CLI examples.

Public API checklist:

- Module facade: `register`, `argument`, `alias`, `alias`, `group`, `confirm`, `dry_run`, `context_factory`, `run`, `run_async`, `run_shell`
- Registry API: `CommandRegistry`, `register_plugin`, `load_plugins`, `dispatch`, `dispatch_async`
- Runtime helpers: `Context`, `types`, `DIContainer`, `Dispatcher`, `MiddlewareChain`
- Exceptions: `RegistrationError`, `DuplicateCommandError`, `UnknownCommandError`, `CommandExecutionError`, `PluginLoadError`
