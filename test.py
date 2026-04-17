from __future__ import annotations

import functools
import logging
import sys
import time
from typing import Any, Callable
from pydantic import BaseModel
from enum import StrEnum

import functionals.cli as cli
import functionals.db as db
from functionals.db import db_field


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# ---------------------------------------------------------------------------
# User Persistence
# ---------------------------------------------------------------------------

DATABASE = "todos.db"
TABLE_NAME = "todos"

class TodoStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"

@db.database_registry(
    DATABASE,
    table_name=TABLE_NAME,
    key_field="id"
)
class TodoItem(BaseModel):
    id: int | None = None
    title: str = db_field(index=True)
    description: str = db_field(default="")
    status: TodoStatus = db_field(default=TodoStatus.PENDING.value)
    created_at: str = db_field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = db_field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

@db.database_registry(
    "users.db", 
    table_name="users", 
    key_field="id"
)
class User(BaseModel):
    id: int
    name: str
    email: str
    password: str
    created_at: str
    updated_at: str


def exception_handler(handle_exit: bool = True, log_errors: bool = True) -> Callable:
    """
    Decorator that wraps a CLI cli with standardized error handling.

    Args:
        handle_exit: Call sys.exit(1) on unhandled exceptions.
        log_errors: Emit error messages via the logging module.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                if log_errors:
                    logging.info("'%s' interrupted by user.", func.__name__)
                sys.exit(0)
            except Exception as exc:
                if log_errors:
                    logging.error("'%s' failed: %s", func.__name__, exc)
                print(f"Error: {exc}", file=sys.stderr)
                if handle_exit:
                    sys.exit(1)
                raise
        return wrapper
    return decorator


@cli.register(description="Add a new todo item")  # For registering the cli and giving help menu description
@cli.argument("title", type=str, help="Title of the todo item")  # Specifying arguments in the registry
@cli.argument("description", type=str, help="Description of the todo item", default="")  # ^^^
@cli.option("--add", help="Add a new todo item")  # Add options for the cli in the registry
@cli.option("-a", help="Add a new todo item")  # ^^^
def add_todo(title: str, description: str = "") -> str:
    todo = TodoItem(title=title, description=description)
    todo.save()
    return f"Added todo: {todo.title} (ID: {todo.id})"

@cli.register(description="Delete a todo item")
@cli.argument("_id", type=int, help="ID of the todo item to delete")
@cli.option("--delete", help="Delete a todo item")
@cli.option("-d", help="Delete a todo item")
def delete_todo(_id: int) -> str:
    todo = TodoItem.objects.get(id=_id)
    if not todo:
        return f"Todo item with ID {_id} not found."
    todo.delete()
    return f"Deleted todo ID {_id}."

@cli.register(description="List all todo items")
@cli.option("--list", help="List all todo items")
@cli.option("-l", help="List all todo items")
def list_todos() -> str:
    todos = TodoItem.objects.all()
    if not todos:
        return "No todo items found."
    else:
        todo_list = [f"{todo.id}: {todo.title} - {todo.description} - {todo.status} - {todo.updated_at} - {todo.created_at}" for todo in todos]
        return "\n".join(todo_list)

@cli.register(description="Mark a todo item as completed")
@cli.argument("_id", type=int, help="ID of the todo item to mark as completed")
@cli.option("--complete", help="Mark a todo item as completed")
@cli.option("-c", help="Mark a todo item as completed")
def complete_todo(_id: int) -> str:
    todo = TodoItem.objects.get(id=_id)
    if not todo:
        return f"Todo item with ID {_id} not found."
    todo.status = TodoStatus.COMPLETED.value
    todo.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
    todo.save()
    return f"Marked todo ID {_id} as completed."

@cli.register(description="Update a todo item")
@cli.argument("_id", type=int, help="ID of the todo item to update")
@cli.argument("title", type=str, help="New title of the todo item", default=None)
@cli.argument("description", type=str, help="New description of the todo item", default=None)
@cli.option("--update", help="Update a todo item")
@cli.option("-u", help="Update a todo item")
def update_todo(_id: int, title: str = None, description: str = None) -> str:
    todo = TodoItem.objects.get(id=_id)
    if not todo:
        return f"Todo item with ID {_id} not found."
    if title:
        todo.title = title
    if description:
        todo.description = description
    todo.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
    todo.save()
    return f"Updated todo ID {_id}."


@cli.register(description="Greet someone by name")
@cli.argument("user_id", type=int, help="ID of the user to greet")
@cli.option("--greet", help="Greet someone by name")
@cli.option("-g", help="Greet someone by name")
@exception_handler()
def greet_user(user_id: int) -> str:
    user = User.objects.get(id=user_id)
    if not user:
        return f"User with ID {user_id} not found."
    return f"Hello, {user.name}!"


@cli.register(description="Create and persist a new user")
@cli.argument("id", type=int, help="ID of the user")
@cli.argument("name", type=str, help="Name of the user")
@cli.argument("email", type=str, help="Email of the user")
@cli.argument("password", type=str, help="Password hash of the user")
@exception_handler()
def create_user(id: int, name: str, email: str, password: str) -> str:
    user = User.objects.create(
        id=id,
        name=name,
        email=email,
        password=password,
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        updated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    return str(user)


@cli.register(description="List all persisted users")
@cli.option("--list-users", help="List all users")
@exception_handler()
def get_all_users() -> str:
    users = User.objects.all()
    if not users:
        return "No users found."
    return "\n".join(str(user) for user in users)


@cli.register(description="Get a user by ID")
@cli.argument("user_id", type=int, help="ID of the user to retrieve")
@cli.option("--get-user", help="Get a user by ID")
@exception_handler()
def get_user_by_id_cli(user_id: int) -> str:
    user = User.objects.get(id=user_id)
    return str(user) if user else f"No user found with id {user_id}."


if __name__ == "__main__":
    cli.run(
        shell_title="Todo Console",
        shell_description="Manage tasks.",
        shell_colors=None,  # auto
        shell_banner=True,
    )
