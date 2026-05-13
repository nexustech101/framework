<div align="center">

# `registers.cron`

**Production automation and scheduling runtime for Python-defined jobs, durable event processing, and operational workflow orchestration.**

[![Module](https://img.shields.io/badge/module-registers.cron-5C6BC0?style=for-the-badge)](#) [![Type](https://img.shields.io/badge/type-Automation%20%26%20Scheduling-1F2937?style=for-the-badge)](#) [![Runtime](https://img.shields.io/badge/runtime-Async%20Workers-0F766E?style=for-the-badge)](#) [![Triggers](https://img.shields.io/badge/triggers-Interval%20%7C%20Cron%20%7C%20Event-7C3AED?style=for-the-badge)](#) [![Ops](https://img.shields.io/badge/ops-fx%20Cron%20Control%20Plane-9333EA?style=for-the-badge)](#) [![Maturity](https://img.shields.io/badge/status-Production%20Manual-2563EB?style=for-the-badge)](#)

</div>

## Tags

`Job Registration` `Daemon Runtime` `Retry Policies` `Dead Letters` `Workflow Registration` `Deployment Artifacts` `Observability` `Scheduler Targets`

> **Positioning:** Use `registers.cron` when job logic, runtime state, and operator workflows must live in one coherent automation surface instead of being scattered across ad hoc scripts.

---

`registers.cron` is a Python automation and scheduling runtime for declaring jobs in code, syncing them into durable runtime state, executing queued events, and generating deployment artifacts for supported scheduler targets.

This refactored manual is written for application engineers, platform operators, and downstream AI agents that need to design, run, deploy, and troubleshoot cron/event automation without reading framework internals.

## Audience

Use this manual if you are:

- declaring Python jobs with interval, cron-expression, manual, file-change, or webhook triggers;
- running a local async job daemon;
- generating Linux cron, Windows Task Scheduler, or GitHub Actions artifacts;
- building repeatable workflow automation around `fx cron`;
- documenting job lifecycle, retry, dead-letter, and observability behavior.

## Operating Model

`registers.cron` has three layers:

| Layer | Responsibility |
|---|---|
| Registration | Decorators and trigger builders define job metadata. |
| Runtime | Project job discovery, durable event state, async workers, run history, and dead-letter handling. |
| Operations | Workspace creation, workflow registration, artifact generation, scheduler apply operations, and status reporting through `fx cron`. |

## Production Contract

A production job surface should use:

- stable job names;
- explicit triggers and targets;
- idempotent handlers;
- bounded runtime for long-running jobs;
- explicit retry policy for unstable network or deployment work;
- environment-backed webhook tokens and secrets;
- observable workflows through `.fx/fx.db`, `fx cron status`, and run history.

---
## 1. What `registers.cron` Is

`registers.cron` is a Python automation/scheduling module with three layers:

1. Registration layer:
- define jobs with decorators (`@cron.job(...)`)
- use trigger builders (`interval`, `cron`, `event`)

2. Runtime layer:
- sync discovered jobs into control-plane state
- run asynchronous workers that process queued events

3. Workspace + deployment layer:
- prepare ops/workflow directories
- register workflow files
- generate/apply deployment artifacts through adapters

`fx` is the operator CLI that drives the same runtime and workspace primitives (`fx cron ...`).

> **Key point:** `registers.cron` defines jobs in Python, then executes and operationalizes them through runtime state and optional `fx` workflows.

## 2. Imports and Public API

Primary import styles:

```python
import registers.cron as cron
```

```python
from registers.cron import CronRegistry
```

```python
from registers import CronRegistry  # Recommended
```

Public module exports:

- Decorators and trigger builders:
  - `job`
  - `watch`
  - `interval`
  - `cron`
  - `event`
- Facade operations:
  - `run`
  - `register`
  - `start`
  - `install_cli`
- Registry access:
  - `get_registry`
  - `reset_registry`
  - `CronRegistry`
- Runtime:
  - `sync_project_jobs`
  - `run_daemon`
- Workspace/workflows:
  - `ensure_workspace`
  - `register_workflow`
  - `list_workflows`
  - `run_registered_workflow`

> **Key point:** use module-level API for convenience; use `CronRegistry` for explicit, isolated job surfaces.

## 3. Architecture Decision: Module-Level vs Class Instance

Use this rule before writing jobs.

### 3.1 Module-level (`import registers.cron as cron`)

Use when all are true:
- one scheduler surface
- simple app or single runtime context
- no isolation requirement between job groups

Benefits:
- shortest code
- fastest onboarding
- default singleton registry is enough

### 3.2 Class instance (`cron = CronRegistry()`)

Use when any are true:
- tests need isolated registries
- one process has multiple automation scopes/tenants
- explicit runtime wiring is required (`registry=` in runtime calls)
- avoiding global singleton side effects matters

Benefits:
- deterministic isolation
- explicit dependency boundaries
- cleaner composition in larger systems

> **Key point:** module-level is the default path; class-instance is the production path for isolation and composition.

## 4. Trigger API

### 4.1 Interval trigger

```python
cron.interval(seconds=30)
cron.interval(minutes=5)
cron.interval(hours=1)
```

Rules:
- combined duration must be positive
- stored internally as total seconds

### 4.2 Cron expression trigger

```python
cron.cron("*/15 * * * *")
cron.cron("0 2 * * *", timezone="local")
```

Rules:
- expression must have exactly 5 fields: `m h dom mon dow`
- supports:
  - `*`
  - `*/N`
  - comma-separated numeric values

### 4.3 Event trigger

```python
cron.event("manual")
cron.event("file_change", paths=["src/**/*.py"], debounce_seconds=2)
cron.event("webhook", path="/deploy", token="change-me")
cron.watch("src/**/*.py", debounce_seconds=2)
```

Supported event kinds:
- `manual`
- `file_change`
- `webhook`

Validation rules:
- `file_change` requires non-empty `paths`
- `webhook` requires `path` starting with `/`

File-change triggers are powered by `watchdog`. Native OS observers are used by default, with watchdog polling available internally for environments that need it.

> **Key point:** choose `interval` for fixed cadence, `cron` for calendar scheduling, `event` for push/manual/file-driven automation, and `watch` for the common file-change decorator.

## 5. Job Decorator API

`@cron.job(...)` supports `@cron.job`, `@cron.job()`, and `@cron.job(name=..., trigger=...)`.
When `trigger` is omitted, the job defaults to `cron.event("manual")`.

`@cron.job(...)` supports:

- identity:
  - `name` (defaults to function name with `_` converted to `-`)
- trigger and routing:
  - `trigger`
  - `target` (`local_async`, `linux_cron`, `windows_task_scheduler`, `github_actions`)
  - `deployment_file`
- execution behavior:
  - `enabled`
  - `max_runtime`
  - `tags`
  - `overlap_policy` (`skip` only in v1)
- retries:
  - `retry_policy` (`none`, `fixed`, `exponential`)
  - `retry_max_attempts`
  - `retry_backoff_seconds`
  - `retry_max_backoff_seconds`
  - `retry_jitter_seconds`

Handler injection behavior:
- if handler has `event` parameter, runtime passes:
  - `{"id": <event_id>, "source": <source>, "payload": <payload_dict>}`
- if handler has `payload` parameter, runtime passes payload dict
- handlers may be sync or async

`cron.run("job-name", payload={...})` executes one job immediately and returns the handler result.
`cron.register("job-name", root=".", apply=True)` syncs job metadata, generates deployment artifacts, and applies supported OS scheduler targets.
`cron.start(...)` is the friendly foreground daemon wrapper around `run_daemon(...)`.
`cron.install_cli()` installs a `registers.cli` command so the script that defines jobs can manage them directly.

> **Key point:** the job decorator captures runtime metadata, deployment target metadata, and retry policy in one declaration; facade methods run or durably register jobs.

## 6. Retry, Backoff, and Dead-Letter Behavior

Retry policy semantics:

- `retry_policy="none"`
  - no retries
  - terminal failure status: `failed`

- `retry_policy="fixed"`
  - fixed delay per retry (`retry_backoff_seconds`)

- `retry_policy="exponential"`
  - delay = base backoff * `2^(attempt-1)`
  - optional max cap (`retry_max_backoff_seconds`)

Jitter:
- if `retry_jitter_seconds > 0`, runtime adds random `0..jitter` delay

Attempt defaults:
- if policy is `fixed`/`exponential` and `retry_max_attempts=0`, runtime defaults to `3`

Terminal states:
- retries exhausted with retry policy enabled -> `dead_letter`
- no retry policy -> `failed`

Internal retry metadata:
- runtime stores retry bookkeeping under `__fx_retry` in event payload records

> **Key point:** use exponential retry for network/deploy instability, fixed retry for predictable retries, and inspect dead letters for terminal failures.

## 7. Module-Level Usage (Default Facade)

```python
from __future__ import annotations

from registers import CronRegistry


cron = CronRegistry()

@cron.job
def rebuild(payload: dict | None = None) -> str:
    dry_run = bool((payload or {}).get("dry_run", False))
    return f"rebuilt (dry_run={dry_run})"

@cron.watch("src/**/*.py", debounce_seconds=1.0)
def rebuild_on_source_change(event: dict) -> str:
    path = event["payload"]["path"]
    return f"source changed: {path}"

@cron.job(
    name="nightly-maintenance",
    trigger=cron.cron("0 2 * * *"),
    target="linux_cron",
    deployment_file="ops/workflows/cron/nightly-maintenance.cron",
    tags=("ops", "maintenance"),
)
def nightly_maintenance() -> str:
    return "maintenance complete"

@cron.job(
    name="deploy-webhook",
    trigger=cron.event("webhook", path="/deploy", token="${DEPLOY_TOKEN}"),
    target="github_actions",
    deployment_file="ops/workflows/ci/deploy-webhook.yml",
    retry_policy="exponential",
    retry_max_attempts=5,
    retry_backoff_seconds=5,
    retry_max_backoff_seconds=120,
    retry_jitter_seconds=2,
)
def deploy_webhook(event: dict) -> str:
    env_name = event.get("payload", {}).get("env", "staging")
    return f"deploy requested for {env_name}"

if __name__ == "__main__":
    print(cron.run("rebuild", payload={"dry_run": True}))
    cron.register("nightly-maintenance", root=".", apply=False)
```

> **Key point:** module-level decorators are ideal for concise single-surface cron automation.

### 7.1 Script-Local CLI Management

`fx` is not required to manage jobs from the script that defines them. Add a
`cron` command to a normal `registers.cli` script:

```python
from __future__ import annotations

from registers import CommandRegistry
import registers.cron as cron

@cron.job
def rebuild(payload: dict | None = None) -> str:
    return f"rebuilt:{bool((payload or {}).get('dry_run'))}"

@cron.job(name="nightly", trigger=cron.cron("0 2 * * *"))
def nightly() -> str:
    return "nightly complete"

cron.install_cli()

if __name__ == "__main__":
    cli.run(shell_title="Automation")
```

Run script-local commands:

```bash
python app.py cron jobs
python app.py cron run rebuild . --payload '{"dry_run":true}'
python app.py cron register nightly . --target auto --apply
python app.py cron status .
```

`--target auto` maps to the platform scheduler: Windows Task Scheduler on
Windows, Linux cron elsewhere. The generated persistent schedule calls back into
the same script with `cron run <job>`, so it does not depend on `fx`.

> **Key point:** use `cron.install_cli()` when you want a self-contained automation script with its own job-management commands.

## 8. Class-Instance Usage (Isolated Registries)

```python
from __future__ import annotations

from registers import CronRegistry

cron = CronRegistry()

@cron.job(
    name="cleanup-cache",
    trigger=cron.interval(minutes=30),
    target="local_async",
    retry_policy="fixed",
    retry_max_attempts=3,
    retry_backoff_seconds=10,
)
def cleanup_cache(payload: dict | None = None) -> str:
    return "cache cleaned"

# Immediate execution and durable registration mirror the module facade.
cron.run("cleanup-cache", payload={"dry_run": True})
cron.register("cleanup-cache", root=".", apply=False)
```

### 8.1 Why this matters

- one test can use its own registry without global collisions
- two services in one process can each own separate scheduler surfaces
- runtime calls can explicitly bind to a registry

> **Key point:** class-instance decorators are first-class and preferred when job surfaces must be isolated.

## 9. Explicit Runtime Wiring (Discovery + Daemon)

You can bind runtime operations to an explicit registry instance.

```python
from __future__ import annotations

import asyncio
from registers import CronRegistry
from registers.cron.runtime import sync_project_jobs, run_daemon

cron = CronRegistry()

# define jobs on this instance ...

# Import/discover project jobs and sync into state using explicit registry
package, loaded_modules, synced_jobs = sync_project_jobs(".", registry=cron)
print(package, loaded_modules, synced_jobs)

# Run daemon with explicit registry
# asyncio.run(run_daemon(root=".", workers=4, registry=cron))
```

Important notes:
- `sync_project_jobs(...)` discovers job modules from project package imports, executes decorators, and syncs entries into `.fx/fx.db` state
- if your project uses `src/<package>`, discovery uses that package
- if no discoverable package exists, no jobs are loaded from discovery

> **Key point:** pass `registry=` when you need deterministic runtime behavior tied to a specific `CronRegistry` instance.


Workspace helper:

```python
from registers.cron import ensure_workspace

result = ensure_workspace(".")
print("created", len(result.created), "existing", len(result.existing))
```

`ensure_workspace` prepares:
- `ops/workflows/cron`
- `ops/workflows/windows`
- `ops/workflows/ci`
- `ops/scripts`
- `src/app/ops/jobs`
- `src/app/ops/__init__.py`
- `src/app/ops/jobs/__init__.py`

> **Key point:** keep Python job definitions and generated workflow artifacts separate for clean operations and version control.

## 10. `fx` Integration: End-to-End Operator Flow

`fx` exposes the operational surface for `registers.cron`.

### 10.1 Prepare workspace

```bash
fx cron workspace .
```

Expected output pattern:

```text
fx Cron Workspace Result
Status: success
Project: <abs-path>
Created:
  - ...
Existing:
  - ...
```

### 10.2 Discover/sync jobs

```bash
fx cron jobs .
```

Expected output pattern:

```text
fx Cron Jobs Result
Status: success
Project: <abs-path>
Jobs:
  <job-name> (<trigger>, target=<target>, enabled=<bool>, retry=<...>)
```

### 10.3 Start runtime

Foreground:

```bash
fx cron start . --workers 4 --foreground
```

Background:

```bash
fx cron start . --workers 4
```

### 10.4 Trigger jobs manually

```bash
fx cron trigger nightly-maintenance .
fx cron trigger deploy-webhook . --payload '{"env":"prod","sha":"abc123"}'
```

### 10.5 Observe runtime

```bash
fx cron status .
```

Includes counters:
- `Pending events`
- `Queued events`
- `Failed events`
- `Dead-letter events`
- `Runs`

### 10.6 Generate deployment artifacts

```bash
fx cron generate .
fx cron generate . --target github_actions
```

### 10.7 Apply artifacts where supported

```bash
fx cron apply . --target linux_cron
fx cron apply . --target windows_task_scheduler
```

### 10.8 Stop runtime

```bash
fx cron stop .
```

> **Key point:** `fx cron` is the operator control-plane over `registers.cron` runtime, event queue, and deployment artifacts.

## 11. Workflow File Registration and Execution

Use this when deployment/workflow files are managed explicitly and should be invoked in a consistent way.

### 11.1 Register a workflow linked to a cron job

```bash
fx cron register deploy-workflow . \
  --workflow-file ops/workflows/ci/deploy-workflow.yml \
  --job deploy-webhook \
  --target github_actions
```

### 11.2 Register a workflow that executes a shell command directly

```bash
fx cron register db-backup . \
  --workflow-file ops/workflows/cron/db-backup.cron \
  --command "bash ops/scripts/backup.sh" \
  --target linux_cron
```

### 11.3 List registered workflows

```bash
fx cron workflows .
```

### 11.4 Execute registered workflow

```bash
fx cron run-workflow deploy-workflow . --payload '{"env":"prod"}'
```

Behavior:
- `--job` mode: enqueues linked cron job event
- `--command` mode: executes shell command from project root

Constraints:
- `--workflow-file` is required
- workflow file must already exist
- exactly one execution mode:
  - `--job`, or
  - `--command`

> **Key point:** registered workflows provide a stable, named execution surface for jobs and scripted operations.

## 12. Deployment Targets and Adapter Behavior

Targets:
- `local_async`
- `linux_cron`
- `windows_task_scheduler`
- `github_actions`

Generation behavior (`fx cron generate` / adapters):
- all targets support artifact generation

Apply behavior (`fx cron apply` / adapters):
- currently supported:
  - `linux_cron`
  - `windows_task_scheduler`
- generate-only in v1:
  - `github_actions`
  - `local_async`

Default artifact paths:
- if `deployment_file` is not set, artifacts are placed under `.fx/cron/deployments`

> **Key point:** generate artifacts for all targets, apply only where host/runtime integration exists.

## 13. Runtime State and Observability

Control-plane database:

- `.fx/fx.db`

Core runtime records:
- cron jobs (`fx_cron_jobs`)
- events queue (`fx_cron_events`)
- run history (`fx_cron_runs`)
- runtime heartbeat (`fx_cron_runtime`)
- workflow registrations (`fx_cron_workflows`)

Operational observability commands:

```bash
fx cron status .
fx cron jobs .
fx cron workflows .
fx history 50 .
```

Operational practices:
- check dead-letter count after failures
- inspect run history for repeated failures
- keep workflow files in `ops/workflows` for auditability

> **Key point:** cron operations are persisted and observable through `.fx/fx.db` plus `fx` reporting commands.

## 14. Simple vs Medium Project Patterns

### 14.1 Simple script pattern

Use when:
- one or two jobs
- one app scope
- little need for isolation

Pattern:
- module-level decorators
- `local_async` target
- manual/interval triggers

### 14.2 Medium automation project pattern

Use when:
- multiple jobs across domains (build/deploy/cleanup)
- workflows and deployment artifacts matter
- operational visibility and repeatability matter

Pattern:
- `src/app/ops/jobs/*` job modules
- `ops/workflows/*` artifacts
- `fx cron workspace/jobs/start/status/generate/apply` lifecycle
- class-instance registries when multiple scopes exist in one process

> **Key point:** start small with module-level jobs; move to structured ops layout + explicit registries as scope grows.

## 15. Professional Deployment Example (GitHub Actions + Manual Trigger)

```python
from __future__ import annotations

from registers import CronRegistry


cron = CronRegistry()

@cron.job(
    name="deploy-production",
    trigger=cron.event("manual"),
    target="github_actions",
    deployment_file="ops/workflows/ci/deploy-production.yml",
    tags=("deploy", "prod"),
    retry_policy="exponential",
    retry_max_attempts=5,
    retry_backoff_seconds=10,
    retry_max_backoff_seconds=180,
    retry_jitter_seconds=2,
)
def deploy_production(payload: dict | None = None) -> str:
    env_name = (payload or {}).get("env", "prod")
    sha = (payload or {}).get("sha", "latest")
    return f"deploy queued env={env_name} sha={sha}"
```

Operations:

```bash
fx cron workspace .
fx cron jobs .
fx cron generate . --target github_actions
fx cron register deploy-production-workflow . --workflow-file ops/workflows/ci/deploy-production.yml --job deploy-production --target github_actions
fx cron trigger deploy-production . --payload '{"env":"prod","sha":"abc123"}'
fx cron status .
```

Expected result shape:
- workflow artifact generated under `ops/workflows/ci`
- manual trigger creates pending event
- daemon processes event and records run outcome

> **Key point:** this is the standard deployment automation path when Python-defined jobs orchestrate CI workflow artifacts.

## 16. Error Paths and Troubleshooting

### 16.1 Common registration errors

- duplicate job name:
  - `ValueError: Cron job '<name>' is already registered.`
- invalid trigger object:
  - `TypeError` if `trigger` is not from `interval/cron/event`
- unsupported target:
  - `target must be one of `local_async`, `linux_cron`, `windows_task_scheduler`, or `github_actions`...`
- invalid retry values:
  - negative attempts/backoff/jitter, or invalid cap relationship

### 16.2 Common workflow errors

- missing workflow file at registration time -> `FileNotFoundError`
- both `--job` and `--command` provided -> `ValueError`
- neither `--job` nor `--command` provided -> `ValueError`

### 16.3 Runtime/discovery pitfalls

- no discoverable package under `src` -> no jobs loaded by discovery
- if project layout differs from `src/<package>`, ensure your import path and package structure are explicit
- if jobs are not found, run `fx cron jobs .` and confirm package/module loading counts

### 16.4 Deployment apply pitfalls

- `linux_cron` apply on Windows host -> unsupported
- `windows_task_scheduler` apply on non-Windows host -> unsupported
- CI targets are generate-only in v1

> **Key point:** most issues come from package discovery, workflow registration mode, or host/target mismatch during apply.

## 17. Security and Reliability Guidance

- keep webhook tokens out of source code (env/config only)
- keep job handlers idempotent so retries are safe
- use explicit retry policies for external network/deploy operations
- set `max_runtime` for long-running jobs to avoid worker starvation
- use stable job names for auditability and long-term ops continuity

> **Key point:** secure tokens, idempotent handlers, bounded runtime, and explicit retry policy are the baseline for production automation.

## 18. Agent Build Recipe (Downstream Automation Agent)

When asked to create cron automation with this module:

1. Choose architecture.
- module-level for simple scope
- class-instance for isolation/multi-surface scope

2. Define jobs with explicit names, triggers, targets, retries.

3. Prepare workspace.

```bash
fx cron workspace <root>
```

4. Verify job discovery.

```bash
fx cron jobs <root>
```

5. Start runtime and test manual trigger.

```bash
fx cron start <root>
fx cron trigger <job_name> <root> --payload '{"dry_run":true}'
fx cron status <root>
```

6. Generate/apply artifacts as needed.

```bash
fx cron generate <root> --target <target>
fx cron apply <root> --target <target>
```

7. Register workflows if named execution surfaces are needed.

```bash
fx cron register <workflow_name> <root> --workflow-file <path> --job <job_name>
```

> **Key point:** always move in this order: architecture -> job definition -> workspace -> discovery -> runtime test -> deployment artifacts -> workflow registration.

## 19. Quick Command Cheat Sheet

```bash
# workspace
fx cron workspace .

# discovery/listing
fx cron jobs .

# runtime
fx cron start . --workers 4
fx cron status .
fx cron stop .

# triggers
fx cron trigger <job> . --payload '{"k":"v"}'

# artifacts
fx cron generate . --target github_actions
fx cron apply . --target linux_cron

# workflows
fx cron register <name> . --workflow-file <path> --job <job>
fx cron workflows .
fx cron run-workflow <name> . --payload '{"k":"v"}'
```

> **Key point:** these are the core commands you will use most in day-to-day cron automation operations.

---

## Production Readiness Checklist

Before deploying `registers.cron` jobs, verify the following:

- [ ] Every job has a stable explicit name.
- [ ] Every job declares an intentional trigger.
- [ ] Deployment targets are chosen deliberately, not left implicit for production jobs.
- [ ] Webhook tokens are loaded from environment or secret storage, never hard-coded.
- [ ] Handlers are idempotent or explicitly protected against duplicate execution.
- [ ] Long-running jobs set `max_runtime` when worker starvation is possible.
- [ ] Network, deployment, and external-service jobs use fixed or exponential retry policy.
- [ ] Dead-letter events are monitored through `fx cron status` and run history.
- [ ] Generated artifacts are checked into the expected `ops/workflows/*` path when appropriate.
- [ ] Host-specific apply behavior is tested on the target platform.

## Recommended Positioning

Use `registers.cron` when Python-defined automation should be treated as operational infrastructure: discoverable, triggerable, observable, and deployable. For simple in-process intervals, module-level jobs are enough. For multi-service automation, long-lived operator workflows, or CI/deployment orchestration, prefer explicit project layout, `fx cron`, stable workflow registration, and runtime observability.