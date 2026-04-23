# `registers.db` Operations Manual

This guide is intentionally exhaustive.

Goal: if an engineer or an agent reads this file, they can build production
backends with `registers.db` without inspecting framework internals.

---

## 1. What `registers.db` Gives You

`registers.db` is a persistence layer for Pydantic models, powered by SQLAlchemy
engines and a registry/manager pattern.

Core capabilities:

- Declarative model registration via `@database_registry(...)`
- Manager-based persistence surface (`Model.objects`)
- Instance persistence helpers (`save`, `delete`, `refresh`)
- Query operators (`field__operator=value`) with type validation
- Bulk create/upsert helpers
- Additive schema evolution helpers (`ensure_column`, `add_column`, `rename_table`)
- Relationship descriptors (`HasMany`, `BelongsTo`, `HasManyThrough`)
- Password hashing/verification integration
- Structured exception model with context payloads

Primary target use cases:

- Backend APIs (FastAPI, service layers)
- Data-model-heavy business logic
- CRUD-centric applications with moderate schema evolution needs

**Summary**: `registers.db` is optimized for backend data modeling and CRUD-heavy service code with practical schema/lifecycle tooling.

---

## 2. Architecture Model and Design Rules

`registers.db` uses a manager pattern:

- All persistence operations live on `Model.objects` (or your custom `manager_attr`).
- The model class remains primarily a Pydantic schema definition.
- Only instance helpers are injected into model instances:
  - `save()`
  - `delete()`
  - `refresh()`
  - `verify_password()` (only when model has a `password` field)
- Schema helpers are exposed as class forwarders:
  - `create_schema()`, `drop_schema()`, `schema_exists()`, `truncate()`

Two supported construction styles:

1. Decorator-first (recommended)
2. Direct manager construction (`DatabaseRegistry(...)`) for explicit wiring

**Summary**: define models with Pydantic, persist through the attached manager, and treat instance helpers as convenience wrappers over manager behavior.

---

## 3. Install and Core Imports

Install:

```bash
pip install registers
```

Common imports:

```python
from pydantic import BaseModel
from registers.db import (
    database_registry,
    DatabaseRegistry,
    db_field,
    HasMany,
    BelongsTo,
    HasManyThrough,
    dispose_all,
)
```

**Summary**: for most projects, you only need `database_registry`, `db_field`, relationship descriptors, and lifecycle cleanup helpers.

---

## 4. Architecture Decision Gate (Simple vs Complex)

Use this gate before implementation.

Choose **simple decorator usage** when:

- You have one service/database surface.
- You want minimal boilerplate.
- Model classes map directly to persistence tables.

Choose **direct `DatabaseRegistry` construction** when:

- You need explicit registry ownership in factories/tests.
- You want to wire managers outside model decoration flow.
- You need advanced composition in framework internals.

Choose **multi-model backend architecture** when:

- You are building API services with entity boundaries (users/orders/payments/etc.).
- You need lifecycle startup/shutdown hooks for schema and engine disposal.
- You need predictable operational exception mapping.

**Summary**: start with decorator mode, escalate to explicit registry wiring only when composition or test architecture requires it.

---

## 5. Quick Start (Decorator Mode)

```python
from pydantic import BaseModel
from registers.db import database_registry


@database_registry(
    "sqlite:///app.db",
    table_name="users",
    key_field="id",
    unique_fields=["email"],
)
class User(BaseModel):
    id: int | None = None
    email: str
    name: str


created = User.objects.create(email="alice@example.com", name="Alice")
fetched = User.objects.require(created.id)
fetched.name = "Alicia"
fetched.save()
fetched.delete()
```

Expected behavior:

- `id` is DB-generated when autoincrement policy applies.
- `require(...)` raises `RecordNotFoundError` if no match.
- `save()` performs upsert semantics.

**Summary**: decorator mode gives you fast model-to-table persistence with minimal setup and a stable manager API.

---

## 6. Quick Start (Direct `DatabaseRegistry` Mode)

```python
from pydantic import BaseModel
from registers.db import DatabaseRegistry


class User(BaseModel):
    id: int | None = None
    email: str
    name: str


users = DatabaseRegistry(
    User,
    "sqlite:///app.db",
    table_name="users",
    key_field="id",
    autoincrement=True,
    unique_fields=["email"],
)

user = users.create(email="alice@example.com", name="Alice")
```

Use this style when you need explicit manager instances without decorator injection.

**Summary**: direct registry mode is an advanced integration path; functionally similar manager API, explicit ownership.

---

## 7. Model Registration Contract

Decorator signature:

```python
@database_registry(
    database_url="sqlite:///app.db",   # bare path also supported
    table_name="users",
    key_field="id",
    manager_attr="objects",
    auto_create=True,
    autoincrement=False,               # decorator can auto-enable for id: int | None
    unique_fields=["email"],
)
class User(BaseModel):
    ...
```

Important validation rules:

- Class must be a `pydantic.BaseModel` subclass.
- `key_field` must exist on model.
- `manager_attr` cannot collide with model fields/attributes.
- `unique_fields` must reference valid fields and contain no duplicates.
- `autoincrement=True` requires integer key field allowing `None`.

Default behaviors (when options omitted):

- `table_name` defaults to snake_case pluralized model name.
- `database_url` defaults to a SQLite file URL based on that table name.
- `manager_attr` defaults to `objects`.
- `auto_create=True` defers unresolved foreign-key DDL until related models are registered.

Primary key policy:

- `id: int | None = None` + autoincrement -> DB-managed key.
- `id: int` (manual) -> caller-supplied key expected.
- Explicit assignment of DB-managed key on create raises `InvalidPrimaryKeyAssignmentError`.
- Mutating persisted key then saving raises `ImmutableFieldError`.

**Summary**: registration is strict by design; invalid model/config combinations fail early with clear configuration exceptions.

---

## 8. `db_field(...)` Metadata Controls

`db_field` lets you attach DB metadata at field definition:

```python
from pydantic import BaseModel
from registers.db import database_registry, db_field


@database_registry("sqlite:///app.db", table_name="accounts", key_field="id")
class Account(BaseModel):
    id: int | None = None
    email: str = db_field(unique=True, index=True)
    manager_id: int | None = db_field(foreign_key="users.id", default=None)
```

Supported metadata:

- `primary_key`
- `autoincrement`
- `unique`
- `index`
- `foreign_key`

Notes:

- `db_field(primary_key=True)` must align with configured `key_field`.
- Non-key autoincrement metadata is rejected.
- `db_field(unique=True)` merges into unique-field config.
- `db_field` metadata flags must be booleans.
- `db_field(foreign_key=...)` must use `table.column` format.

**Summary**: `db_field` is the fine-grained column metadata layer for index/unique/fk behavior beyond basic type mapping.

---

## 9. CRUD API Surface (`Model.objects`)

Write operations:

- `create(**data)`
- `strict_create(**data)` (alias of `create`)
- `upsert(instance | **data)`
- `save(instance)`
- `update_where(criteria, **updates)`
- `delete(key_value)`
- `delete_where(**criteria)`
- `bulk_create(list[dict])`
- `bulk_upsert(list[dict])`

Read operations:

- `get(pk_or_criteria)`
- `require(pk_or_criteria)`
- `filter(...)`
- `all(...)`
- `get_all()`
- `exists(**criteria)`
- `count(**criteria)`
- `first(...)`
- `last(...)`
- `refresh(instance)`

Instance helpers (injected):

- `instance.save()`
- `instance.delete()`
- `instance.refresh()`

**Summary**: the manager is the canonical persistence interface; instance methods are thin convenience wrappers.

---

## 10. Query Semantics, Operators, Sorting, Pagination

Use `field__operator=value` syntax in `filter`, `count`, `exists`, etc.

Supported operators:

- `eq` (default; scalar values only)
- `not`
- `gt`, `gte`, `lt`, `lte`
- `like`, `ilike`
- `in`, `not_in`
- `is_null`
- `between`
- `contains`, `startswith`, `endswith`

Examples:

```python
User.objects.filter(age__gte=18, age__lt=65)
User.objects.filter(status__in=["active", "trial"])
User.objects.filter(deleted_at__is_null=True)
User.objects.filter(score__between=(70, 100))
User.objects.filter(name__ilike="ali%")
```

Sorting:

```python
User.objects.filter(order_by="name")
User.objects.filter(order_by="-created_at")
User.objects.all(order_by=["role", "-name"])
```

Pagination:

```python
User.objects.filter(order_by="id", limit=20, offset=40)
```

Validation behavior:

- Unknown fields/operators raise `InvalidQueryError`.
- Invalid value shapes/types raise `InvalidQueryError`.
- Iterable equality values (for example `id=[1, 2]`) are rejected; use `id__in=[1, 2]`.
- `limit` and `offset` must be `>= 0`.

**Summary**: query operators are expressive but strongly validated, making filter contracts predictable for API/service code.

---

## 11. Upsert and Identity Rules

`upsert(...)` behavior:

- With key present: upsert by key.
- With autoincrement key absent:
  - if `unique_fields` configured, upsert can target unique conflict keys
  - otherwise falls back to create path

Identity immutability:

- Persisted key is stamped and considered immutable for subsequent saves.

Example:

```python
@database_registry("sqlite:///app.db", table_name="users", unique_fields=["email"])
class User(BaseModel):
    id: int | None = None
    email: str
    name: str

User.objects.create(email="alice@example.com", name="Alice")
updated = User.objects.upsert(email="alice@example.com", name="Alicia")
```

**Summary**: upsert is key/constraint-aware and intentionally strict about primary key immutability after persistence.

---

## 12. Bulk Operations and Atomicity Expectations

Bulk helpers:

```python
rows = User.objects.bulk_create(
    [
        {"email": "a@example.com", "name": "A"},
        {"email": "b@example.com", "name": "B"},
    ]
)

rows = User.objects.bulk_upsert(
    [
        {"id": 1, "email": "a@example.com", "name": "A+"},
        {"id": 3, "email": "c@example.com", "name": "C"},
    ]
)
```

Behavior highlights:

- Empty list returns `[]`.
- Integrity violations raise normalized DB exceptions.
- Operations execute inside engine transaction contexts.

**Summary**: bulk operations are optimized for service-layer write batches with normalized error behavior and predictable return values.

---

## 13. Schema Lifecycle and Evolution

Class-level schema helpers:

```python
User.create_schema()
User.schema_exists()
User.truncate()
User.drop_schema()
```

Manager-level evolution helpers:

```python
User.objects.add_column("timezone", str, nullable=True)
created = User.objects.ensure_column("timezone", str, nullable=True)  # bool
columns = User.objects.column_names()
User.objects.rename_table("users_archive")
```

Operational guidance:

- Prefer `ensure_column(...)` for startup-safe idempotent migrations.
- Use `add_column(...)` when you explicitly want failure on existing columns.
- `rename_table(...)` rebinds manager state; subsequent `Model.objects` operations use new table immediately.

**Summary**: schema APIs favor safe additive evolution and explicit destructive actions, with rename state transitions handled for you.

---

## 14. Relationships (`HasMany`, `BelongsTo`, `HasManyThrough`)

Define relationships **after** class decoration:

```python
from pydantic import BaseModel
from registers.db import database_registry, HasMany, BelongsTo, HasManyThrough

DB = "sqlite:///app.db"

@database_registry(DB, table_name="authors")
class Author(BaseModel):
    id: int | None = None
    name: str

@database_registry(DB, table_name="posts")
class Post(BaseModel):
    id: int | None = None
    author_id: int | None = None
    title: str

@database_registry(DB, table_name="tags")
class Tag(BaseModel):
    id: int | None = None
    name: str

@database_registry(DB, table_name="post_tags")
class PostTag(BaseModel):
    id: int | None = None
    post_id: int
    tag_id: int

Author.posts = HasMany(Post, foreign_key="author_id")
Post.author = BelongsTo(Author, local_key="author_id")
Post.tags = HasManyThrough(Tag, through=PostTag, source_key="post_id", target_key="tag_id")
```

Behavior notes:

- Relationships are lazy-loaded on access.
- Descriptors are read-only.
- Null/dangling foreign keys safely resolve to `None`/`[]`.
- `HasManyThrough` deduplicates repeated related IDs.

**Summary**: relationships are explicit, lazy, safe by default, and intended for read traversal rather than write mutation via descriptor assignment.

---

## 15. Password Field Behavior and Security Helpers

If a model has a field literally named `password`, write operations hash it automatically.

Hashing applies to:

- `create`
- `strict_create`
- `upsert`
- `save`
- `update_where`

Example:

```python
@database_registry("sqlite:///app.db", table_name="accounts")
class Account(BaseModel):
    id: int | None = None
    email: str
    password: str

acct = Account.objects.create(email="alice@example.com", password="secret123")
assert acct.password != "secret123"
assert acct.verify_password("secret123")
```

Additional exports:

- `hash_password(value)`
- `is_password_hash(value)`
- `verify_password(raw, stored_hash)`

**Summary**: password handling is built in for conventionally named password fields, with safe hash/verify helpers available for service-layer auth flows.

---

## 16. Transactions and Engine Lifecycle

Transaction context:

```python
from sqlalchemy import text

with User.objects.transaction() as conn:
    conn.execute(text("UPDATE users SET name = :name WHERE id = :id"), {"name": "Alicia", "id": 1})
```

Important note:

- Public manager methods (`create`, `update_where`, etc.) open their own transaction contexts.
- Use the yielded `conn` for low-level grouped SQL work when you need explicit control.

Engine/runtime notes:

- Engines are cached per database URL.
- SQLite file engines enable WAL mode and foreign key enforcement.
- In-memory SQLite uses a shared static pool pattern for process-local visibility.

Engine lifecycle:

```python
User.objects.dispose()  # one manager's DB URL
```

Global cleanup:

```python
from registers.db import dispose_all
dispose_all()
```

**Summary**: use manager transactions for explicit low-level batching, and always dispose engines during app shutdown/test teardown.

---

## 17. FastAPI Backend Integration Pattern

Startup/shutdown lifecycle:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not User.schema_exists():
        User.create_schema()
    yield
    User.objects.dispose()

app = FastAPI(lifespan=lifespan)
```

Typical route/service pattern:

- `require(...)` for strict lookup + 404 mapping
- `create(...)` for inserts
- mutate + `save()` for entity updates
- structured exception mapping to HTTP status codes

See robust backend example patterns in:

- `C:\\Users\\charl\\Documents\\Python\\ecommerce-backend-example\\models.py`
- `C:\\Users\\charl\\Documents\\Python\\ecommerce-backend-example\\app.py`
- `C:\\Users\\charl\\Documents\\Python\\ecommerce-backend-example\\utils.py` (API helper middleware/logging utilities)

**Summary**: the recommended API integration is lifecycle-managed schema/engine control plus service-layer exception mapping around manager operations.

---

## 18. Exception Model and Structured Diagnostics

Exception hierarchy root:

- `RegistryError`

Common operational exceptions:

- `ConfigurationError`
- `ModelRegistrationError`
- `SchemaError`
- `MigrationError`
- `RelationshipError`
- `DuplicateKeyError`
- `InvalidPrimaryKeyAssignmentError`
- `ImmutableFieldError`
- `UniqueConstraintError`
- `RecordNotFoundError`
- `InvalidQueryError`

Structured diagnostics:

- Every `RegistryError` supports `exc.context`
- Every `RegistryError` supports `exc.to_dict()`

Example:

```python
try:
    User.objects.require(email="missing@example.com")
except RecordNotFoundError as exc:
    payload = exc.to_dict()
    # log payload to structured logging pipeline
```

**Summary**: error handling is production-oriented: specific exception types plus structured context for observability and API responses.

---

## 19. Public API Surface

Exports from `registers.db`:

- Core:
  - `database_registry`
  - `DatabaseRegistry`
  - `db_field`
- Security:
  - `hash_password`
  - `is_password_hash`
  - `verify_password`
- Relationships:
  - `HasMany`
  - `BelongsTo`
  - `HasManyThrough`
- Schema:
  - `SchemaManager`
- Engine:
  - `get_engine`
  - `dispose_engine`
  - `dispose_all`
- Config:
  - `RegistryConfig`
- Exceptions:
  - `RegistryError` and subclasses

**Summary**: this is the canonical API index for backend/service code and framework integrations.

---

## 20. Agent Build Recipe

When asked to build a backend/data layer with `registers.db`, use this sequence.

1. Define Pydantic data models.
2. Register persistence (`@database_registry(...)`) and set key/unique policy.
3. Add schema startup hooks (`create_schema`/`schema_exists`) and shutdown disposal.
4. Implement CRUD/service methods via `Model.objects`.
5. Add query filters/sorting/pagination for read endpoints.
6. Add write invariants (`update_where`, `upsert`, unique constraints).
7. Add schema evolution (`ensure_column`) for startup-safe migrations.
8. Add relationships after model decoration where traversal is needed.
9. Map exceptions to transport-level contracts (HTTP/status/messages).
10. Add tests for happy paths, collisions, and error boundaries.

**Summary**: this sequence keeps backend development deterministic, testable, and operationally safe.

---

## 21. Production Backend Blueprint (Ecommerce-Scale Pattern)

For larger scopes (users/customers/products/orders/payments):

1. Separate persistence models from API payload models.
2. Use `.objects` manager methods in service/route handlers.
3. Enforce write-side invariants in service layer:
   - stock checks
   - default-address uniqueness per customer
   - transactional compensation logic where needed
4. Use `require(...)` for strict fetches and map not-found to 404.
5. Use `unique_fields` for natural keys (email, SKU-like values).
6. Use lifecycle disposal to prevent stale pool issues in long-running services.

This pattern is demonstrated in your reference backend under:

- `models.py` (entity registration)
- `app.py` (route + service behavior)

**Summary**: at medium/large backend scale, `registers.db` works best when model registration, service invariants, and API exception mapping are treated as separate layers.

---

## 22. Ecommerce API Build Blueprint (File-by-File)

If an agent is asked to build an ecommerce API, use this concrete structure:

```text
ecommerce_api/
  app/
    __init__.py
    models.py
    schemas.py
    services/
      __init__.py
      orders.py
    api.py
  tests/
    test_ecommerce_api.py
  pyproject.toml
```

`models.py` pattern (persistence models only):

```python
from pydantic import BaseModel
from registers.db import database_registry

DB = "sqlite:///ecommerce.db"

@database_registry(DB, table_name="customers", key_field="id", unique_fields=["email"])
class Customer(BaseModel):
    id: int | None = None
    name: str
    email: str
    password: str
    created_at: str
    updated_at: str

@database_registry(DB, table_name="products", key_field="id")
class Product(BaseModel):
    id: int | None = None
    name: str
    price: float
    stock: int
    created_at: str
    updated_at: str

@database_registry(DB, table_name="orders", key_field="id")
class Order(BaseModel):
    id: int | None = None
    customer_id: int
    total_amount: float
    created_at: str
    updated_at: str
```

`api.py` pattern (transport + lifecycle + exception mapping):

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from registers.db import RecordNotFoundError, UniqueConstraintError, RegistryError

from .models import Customer, Product, Order

MODEL_REGISTRY = [Customer, Product, Order]

@asynccontextmanager
async def lifespan(app: FastAPI):
    for model in MODEL_REGISTRY:
        if not model.schema_exists():
            model.create_schema()
    yield
    for model in MODEL_REGISTRY:
        model.objects.dispose()

app = FastAPI(lifespan=lifespan)

@app.exception_handler(UniqueConstraintError)
async def unique_error(_request, _exc):
    return JSONResponse(status_code=409, content={"detail": "Unique constraint violation"})

@app.exception_handler(RecordNotFoundError)
async def not_found_error(_request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(RegistryError)
async def registry_error(_request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
```

`services/orders.py` pattern (write invariants + compensation):

```python
from fastapi import HTTPException
from ..models import Order, Product

def create_order(customer_id: int, items: list[dict], now: str) -> Order:
    snapshots: dict[int, Product] = {}
    total = 0.0
    for item in items:
        product = Product.objects.require(item["product_id"])
        if product.stock < item["quantity"]:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for product {product.id}")
        snapshots[product.id] = product
        total += product.price * item["quantity"]

    created: Order | None = None
    try:
        created = Order.objects.create(
            customer_id=customer_id,
            total_amount=round(total, 2),
            created_at=now,
            updated_at=now,
        )
        for item in items:
            product = snapshots[item["product_id"]]
            Product.objects.update_where({"id": product.id}, stock=product.stock - item["quantity"])
        return created
    except Exception as exc:
        if created is not None:
            Order.objects.delete(created.id)
        for product_id, snapshot in snapshots.items():
            Product.objects.update_where({"id": product_id}, stock=snapshot.stock)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

Use your full project example for expanded coverage:

- `C:\\Users\\charl\\Documents\\Python\\ecommerce-backend-example\\models.py`
- `C:\\Users\\charl\\Documents\\Python\\ecommerce-backend-example\\app.py`
- `C:\\Users\\charl\\Documents\\Python\\ecommerce-backend-example\\utils.py`

**Summary**: this section is the direct implementation scaffold an agent can follow to build an ecommerce API, not just conceptual guidance.

---

## 23. Endpoint-to-Manager Mapping for Ecommerce APIs

Recommended mapping:

- `POST /customers` -> `Customer.objects.create(...)`
- `GET /customers/{id}` -> `Customer.objects.require(id)`
- `PATCH /customers/{id}` -> mutate model then `instance.save()`
- `DELETE /customers/{id}` -> `instance.delete()`
- `GET /products` -> `Product.objects.filter(order_by="-id", limit=..., offset=..., **filters)`
- `POST /orders/checkout` -> service method using `require`, `create`, `update_where`, and compensation logic
- `GET /orders/{id}` -> `Order.objects.require(id)` + child collections via `filter(...)`

Operator-friendly list endpoints:

```python
filters = {}
if min_price is not None:
    filters["price__gte"] = min_price
rows = Product.objects.filter(
    order_by="-id",
    limit=limit,
    offset=offset,
    **filters,
)
```

When optional criteria are used, prefer building a `filters` dict first so you
do not pass `None` values unintentionally.

**Summary**: agents should map each HTTP operation to one or two specific manager methods, keeping service code deterministic and easy to test.

---

## 24. Runbook: Build, Run, Verify

Run the API:

```bash
uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload
```

Smoke checks:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/customers -H "Content-Type: application/json" -d "{\"name\":\"Alice\",\"email\":\"alice@example.com\",\"password\":\"secret123\"}"
curl http://127.0.0.1:8000/products?limit=20&offset=0
```

Expected outcomes:

- Health returns success payload.
- Customer create returns object without raw password.
- Product list supports pagination and optional filters.

**Summary**: this runbook gives agents and engineers concrete verification steps to confirm a newly generated ecommerce API is operational.

---

## 25. Compatibility Notes

- Legacy package names/imports (`functionals`, `decorates`) should be migrated to `registers`.
- Keep docs/examples standardized on:
  - `import registers.db as db` or direct named imports from `registers.db`

**Summary**: use `registers` consistently in new code and docs to avoid drift and broken imports across projects.
