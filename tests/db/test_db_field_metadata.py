from __future__ import annotations

import pytest
from pydantic import BaseModel
from sqlalchemy import inspect

from conftest import db_url
from registers.db import ConfigurationError, UniqueConstraintError, database_registry, db_field


def test_db_field_index_creates_database_index(tmp_path):
    @database_registry(db_url(tmp_path), table_name="products", key_field="id")
    class Product(BaseModel):
        id: int
        sku: str = db_field(index=True)
        name: str

    indexes = inspect(Product.objects._engine).get_indexes(Product.objects.table_name)
    indexed_columns = {tuple(index["column_names"]) for index in indexes}

    assert ("sku",) in indexed_columns


def test_db_field_unique_enforces_constraint_without_unique_fields_option(tmp_path):
    @database_registry(db_url(tmp_path), table_name="users", key_field="id")
    class User(BaseModel):
        id: int
        email: str = db_field(unique=True)

    User.objects.create(id=1, email="alice@example.com")
    with pytest.raises(UniqueConstraintError):
        User.objects.create(id=2, email="alice@example.com")


def test_db_field_autoincrement_enables_generated_ids(tmp_path):
    @database_registry(db_url(tmp_path), table_name="users", key_field="id")
    class User(BaseModel):
        id: int | None = db_field(primary_key=True, autoincrement=True, default=None)
        name: str

    u1 = User.objects.create(name="Alice")
    u2 = User.objects.create(name="Bob")

    assert (u1.id, u2.id) == (1, 2)


def test_db_field_primary_key_must_match_configured_key_field(tmp_path):
    with pytest.raises(ConfigurationError, match="db_field\\(primary_key=True\\)"):
        @database_registry(db_url(tmp_path), table_name="sessions", key_field="id")
        class Session(BaseModel):
            id: int
            session_id: int = db_field(primary_key=True)


def test_db_field_foreign_key_requires_table_column_format():
    with pytest.raises(ConfigurationError, match="table.column"):
        db_field(foreign_key="users")

    with pytest.raises(ConfigurationError, match="table.column"):
        db_field(foreign_key="users.")

    with pytest.raises(ConfigurationError, match="table.column"):
        db_field(foreign_key="")


def test_db_field_rejects_non_boolean_flags():
    with pytest.raises(ConfigurationError, match="must be a bool"):
        db_field(index="yes")  # type: ignore[arg-type]

    with pytest.raises(ConfigurationError, match="must be a bool"):
        db_field(unique=1)  # type: ignore[arg-type]


def test_db_field_normalizes_foreign_key_whitespace(tmp_path):
    @database_registry(db_url(tmp_path), table_name="users", key_field="id")
    class User(BaseModel):
        id: int

    @database_registry(db_url(tmp_path), table_name="sessions", key_field="id")
    class Session(BaseModel):
        id: int
        user_id: int = db_field(foreign_key="  users.id   ")

    # Creation should succeed when FK metadata is normalized.
    User.objects.create(id=1)
    created = Session.objects.create(id=1, user_id=1)
    assert created.user_id == 1
