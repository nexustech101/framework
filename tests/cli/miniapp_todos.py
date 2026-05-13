from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from time import strftime

import registers.cli as cli
import registers.db as db
from pydantic import BaseModel
from registers.db import db_field

DB_PATH = os.environ.get("REGISTERS_TASK_DB", str(Path(__file__).with_suffix(".db")))


def now() -> str:
    return strftime("%Y-%m-%d %H:%M:%S")


class TaskStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    BLOCKED = "blocked"


@db.database_registry(DB_PATH, table_name="tasks", key_field="id")
class Task(BaseModel):
    id: int | None = db_field(default=None, id_strategy="autoincrement")
    title: str = db_field(index=True)
    owner: str = db_field(default="platform", index=True)
    status: TaskStatus = db_field(default=TaskStatus.OPEN)
    notes: str = db_field(default="")
    created_at: str = db_field(default_factory=now)
    updated_at: str = db_field(default_factory=now)


@cli.register(name="add", description="Create an engineering task")
@cli.argument("title", type=str, help="Short task title")
@cli.argument("owner", type=str, default="platform", help="Responsible team")
@cli.argument("notes", type=str, default="", help="Optional implementation notes")
@cli.option("--add")
@cli.option("-a")
def add_task(title: str, owner: str = "platform", notes: str = "") -> dict[str, object]:
    task = Task(title=title, owner=owner, notes=notes)
    task.save()
    return {"id": task.id, "title": task.title, "owner": task.owner, "status": task.status.value}


@cli.register(name="list", description="List tasks by status or owner", default_output="json")
@cli.argument("status", type=cli.types.Choice([item.value for item in TaskStatus]), default="open")
@cli.argument("owner", type=str, default="", help="Optional owner filter")
@cli.option("--list")
@cli.option("-l")
def list_tasks(status: str = "open", owner: str = "") -> list[dict[str, object]]:
    tasks = Task.objects.filter(status=TaskStatus(status))
    if owner:
        tasks = [task for task in tasks if task.owner == owner]
    return [
        {
            "id": task.id,
            "title": task.title,
            "owner": task.owner,
            "status": task.status.value,
            "updated_at": task.updated_at,
        }
        for task in tasks
    ]


@cli.register(name="block", description="Mark a task as blocked")
@cli.argument("task_id", type=int, help="Task ID")
@cli.argument("notes", type=str, default="", help="Blocker details")
def block_task(task_id: int, notes: str = "") -> str:
    task = Task.objects.get(id=task_id)
    if task is None:
        return f"Task {task_id} was not found."
    task.status = TaskStatus.BLOCKED
    task.notes = notes or task.notes
    task.updated_at = now()
    task.save()
    return f"Blocked task {task_id}: {task.title}"


@cli.register(name="complete", description="Mark a task as done")
@cli.argument("task_id", type=int, help="Task ID")
@cli.option("--complete")
@cli.option("-c")
def complete_task(task_id: int) -> str:
    task = Task.objects.get(id=task_id)
    if task is None:
        return f"Task {task_id} was not found."
    task.status = TaskStatus.DONE
    task.updated_at = now()
    task.save()
    return f"Completed task {task_id}: {task.title}"


@cli.register(name="handoff", description="Generate a handoff summary", default_output="plain")
@cli.argument("owner", type=str, default="platform", help="Team to summarize")
def handoff(owner: str = "platform") -> str:
    tasks = Task.objects.filter(owner=owner)
    if not tasks:
        return f"No tasks found for {owner}."
    lines = [f"Handoff for {owner}"]
    for task in tasks:
        note = f" - {task.notes}" if task.notes else ""
        lines.append(f"{task.id}: {task.title} [{task.status.value}]{note}")
    return "\n".join(lines)


if __name__ == "__main__":
    cli.run(
        shell_title="Task Desk",
        shell_description="Track small internal engineering tasks.",
        shell_banner=True,
        shell_usage=True,
    )
