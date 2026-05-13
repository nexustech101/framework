from __future__ import annotations

import registers.cli as cli

registry = cli.CommandRegistry()


class ShellContext(cli.Context):
    def __init__(self, env: str = "stage") -> None:
        self.env = env


@registry.context_factory
def build_context(env: str = "stage") -> ShellContext:
    return ShellContext(env)


services = registry.group("services", aliases=["svc"], description="Service commands")
runbook = registry.group("runbook", aliases=["rb"], description="Runbook commands")


@services.register(
    "status",
    description="Show service status",
    default_output="json",
    examples=[
        "ops-shell services status api",
        "ops-shell svc status worker",
    ],
)
@services.argument("name", type=str, default="api")
def service_status(ctx: ShellContext, name: str = "api") -> dict[str, str]:
    return {"env": ctx.env, "service": name, "status": "ok"}


@runbook.register(
    "restart",
    description="Preview a service restart",
    examples=[
        "ops-shell runbook restart api --dry-run",
        "ops-shell rb restart worker",
    ],
)
@runbook.argument("name", type=str)
@runbook.dry_run()
def restart(ctx: ShellContext, name: str, dry_run: bool = False) -> str:
    action = "Would restart" if dry_run else "Restarting"
    return f"{action} {name} in {ctx.env}"


def scripted_input(lines: list[str]):
    iterator = iter(lines)

    def read(_prompt: str) -> str:
        return next(iterator)

    return read


if __name__ == "__main__":
    registry.run(
        ["--env", "stage", "--interactive"],
        shell_input_fn=scripted_input(
            [
                "help",
                "commands",
                "help services status",
                "services status api",
                "svc status worker",
                "runbook restart api --dry-run",
                "exec echo shell-ok",
                "quit",
            ]
        ),
        shell_title="Ops Shell Demo",
        shell_description="Scripted walkthrough of public shell built-ins.",
        shell_banner=False,
        shell_colors=False,
        output="json",
    )
