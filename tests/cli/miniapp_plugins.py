from __future__ import annotations

from registers.cli import CommandRegistry

users_cli = CommandRegistry()
billing_cli = CommandRegistry()
ops_cli = CommandRegistry()

users = users_cli.group("users", aliases=["u"], description="Account administration")
billing = billing_cli.group("billing", aliases=["b"], description="Billing operations")
ops = ops_cli.group("ops", aliases=["o"], description="Operational runbooks")

USER_ROWS = [
    {"email": "ada@example.com", "role": "admin", "status": "active"},
    {"email": "grace@example.com", "role": "member", "status": "active"},
    {"email": "linus@example.com", "role": "member", "status": "locked"},
]

INVOICES = [
    {"account": "acme", "invoice": "INV-100", "amount": 4200, "state": "open"},
    {"account": "globex", "invoice": "INV-101", "amount": 9800, "state": "paid"},
]


@users.register("list", description="List users by account status", default_output="json")
@users.argument("status", type=str, default="active")
def list_users(status: str = "active") -> list[dict[str, str]]:
    return [row for row in USER_ROWS if row["status"] == status]


@users.register("lock", description="Lock a user account")
@users.argument("email", type=str)
@users.confirm("Lock user {email}?", confirm_phrase="lock {email}")
def lock_user(email: str) -> str:
    return f"Locked {email}; sessions will be revoked."


@billing.register("invoices", description="List invoices for finance review", default_output="csv")
@billing.argument("state", type=str, default="open")
def list_invoices(state: str = "open") -> list[dict[str, object]]:
    return [row for row in INVOICES if row["state"] == state]


@ops.register("health", description="Summarize service health", default_output="json")
def health() -> list[dict[str, str]]:
    return [
        {"service": "api", "status": "ok", "owner": "platform"},
        {"service": "worker", "status": "ok", "owner": "automation"},
        {"service": "billing", "status": "degraded", "owner": "finance-eng"},
    ]


registry = CommandRegistry()
registry.register_plugin(users_cli)
registry.register_plugin(billing_cli)
registry.register_plugin(ops_cli)


if __name__ == "__main__":
    registry.run(
        shell_title="Admin Console",
        shell_description="Compose account, billing, and ops command plugins.",
        shell_usage=True,
    )
