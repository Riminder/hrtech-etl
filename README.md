<p align="center">
<div style="width:260px; height:100px; overflow:hidden; border-radius:8px;">
  <img src="./logo.png" style="width:100%; height:auto; object-fit:cover; object-position:center 50%;" />
</div>

<p align="center">
  <a href="https://pypi.org/project/hrtech-etl/"><img src="https://img.shields.io/pypi/v/hrtech-etl.svg" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/hrtech-etl/"><img src="https://img.shields.io/pypi/pyversions/hrtech-etl.svg" alt="Python Versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
</p>


# HrTech ETL (WIP)

Open-source ETL framework for **HRTech data** (jobs & profiles) across **ATS, CRM, Jobboard, and HCM** systems.

- Focused on **connectors** (per external warehouse)
- Uses **Pydantic models** for native & unified objects
- Supports **cursor-based incremental sync**, **pre-filtering**, **post-filtering**
- Supports **pull & push pipelines** for **resources** and **events**
- Uses **pluggable formatters** (Python or mapping-based)
- Metadata-driven **query params**: `cursor_*`, `search_binding`, `in_binding`
- Ships with a **FastAPI backend** (API + Playground) and a **CLI** for scripting

👉 See also: [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## Table of Contents

1. [Features](#features)  
2. [Quick Start (Python)](#quick-start-python)  
   2.1. [Pull: Jobs & Profiles](#21-pull-jobs--profiles)  
   2.2. [Push: Native Resources](#22-push-native-resources)  
   2.3. [Push: Events → Resources](#23-push-events--resources)  
   2.4. [Custom Formatters](#24-custom-formatters)  
   2.5. [Prefilters (WHERE) & Postfilters (HAVING)](#25-prefilters-where--postfilters-having)  
   2.6. [JSON / Mapping-based Formatters](#26-json--mapping-based-formatters)  
3. [CLI Usage](#cli-usage)  
4. [FastAPI App: API vs Playground](#fastapi-app-api-vs-playground)  
5. [Core Concepts](#core-concepts)  
   5.1. [Resources & Push Modes](#51-resources--push-modes)  
   5.2. [Connectors & Actions](#52-connectors--actions)  
   5.3. [Native & Unified Models](#53-native--unified-models)  
   5.4. [Cursor & Cursor Modes](#54-cursor--cursor-modes)  
   5.5. [Formatters](#55-formatters)  
   5.6. [Conditions, Prefilters & UI Schema](#56-conditions-prefilters--ui-schema)  
   5.7. [Query Param Bindings: cursor / search / IN](#57-query-param-bindings-cursor--search--in)  
6. [Repository Structure](#repository-structure)  
7. [Roadmap / Status](#roadmap--status)  
8. [Contributing](#contributing)  
9. [License](#license)

---

## Features

- 🔌 **Warehouse Connectors** for ATS, CRM, Jobboard, HCM  
- 🧱 **Pydantic-native models** per warehouse (jobs & profiles)
- 🧬 Optional **UnifiedJob / UnifiedProfile / UnifiedJobEvent / UnifiedProfileEvent** as normalized layer
- 🔄 **Cursor-based incremental pull** on:
  - `id`
  - `created_at`
  - `updated_at`
- 🎛️ **Prefilters** on origin (metadata-driven, via `prefilter` in `json_schema_extra`)
- 🎚️ **Postfilters** in core on native origin objects (any field, richer operators)
- 🧩 **Formatter functions**:
  - explicit native→native (e.g. `WarehouseAJob → WarehouseBJob`)
  - implicit native→unified→native via connector hooks
  - JSON-driven mapping formatters (built in the UI)
- 🧷 **Metadata-driven query params**:
  - `cursor_start_min` / `cursor_end_max` / `cursor_order_up` / `cursor_order_down`
  - `search_binding` with `field_join` / `value_join` (e.g. `(title OR text) AND (skills...)`)
  - `in_binding` for `IN` queries (e.g. `board_key` → `board_keys` as `array`, `csv`, or `array_string`)
- 📡 **Push pipeline** with two modes:
  - `PushMode.RESOURCES` → push native resources
  - `PushMode.EVENTS` → push from events (`UnifiedJobEvent` / `UnifiedProfileEvent`)
- 🌐 **FastAPI backend**:
  - `/api/...` JSON endpoints (connectors, schema, pull/push, formatters)
  - `/playground` HTML UI for no-code mapping + pre/post filters + cursor control + events/resources JSON
- 🖥 **CLI** for running pull/push jobs from the shell

---

## Quick Start (Python)

### 2.1. Pull: Jobs & Profiles

The core pull primitive is:

```python
from hrtech_etl.core.types import Resource, Cursor, CursorMode
from hrtech_etl.core.auth import ApiKeyAuth, BearerAuth
from hrtech_etl.core.pipeline import pull

from hrtech_etl.connectors.warehouse_a import WarehouseAConnector
from hrtech_etl.connectors.warehouse_b import WarehouseBConnector
from hrtech_etl.formatters import a_to_b

# --- Instantiate connectors ---

origin = WarehouseAConnector(
    auth=ApiKeyAuth(
        base_url="https://api.warehouse-a.example",
        header_name="X-API-Key",
        api_key="AAA",
        extra_headers={"X-Tenant-ID": "tenant-123"},
    )
)

target = WarehouseBConnector(
    auth=BearerAuth(
        base_url="https://api.warehouse-b.com",
        token="bbb"
    )
)

# start from scratch (no cursor yet)
cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc")

# --- PULL JOBS: A -> B ---
cursor_jobs = pull(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    cursor=cursor,
    formatter=a_to_b.format_job,   # JOB formatter (optional)
    batch_size=5000,
)

print("jobs cursor_start:", cursor_jobs.start)
print("jobs cursor_end:", cursor_jobs.end)

# --- PULL PROFILES: A -> B ---
cursor_profiles = pull(
    resource=Resource.PROFILE,
    origin=origin,
    target=target,
    cursor=cursor,
    formatter=a_to_b.format_profile,  # PROFILE formatter (optional)
    batch_size=5000,
)

print("profiles cursor_end:", cursor_profiles.end)

# Store cursor_jobs.end / cursor_profiles.end to resume on next run.
```

---

### 2.2. Push: Native Resources

Push directly from **native resources** (jobs or profiles):

```python
from hrtech_etl.core.types import Resource, PushMode
from hrtech_etl.core.pipeline import push

# Assume you already have a list of native jobs from WarehouseA
jobs_to_push = [...]  # list[WarehouseAJob]

result = push(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    mode=PushMode.RESOURCES,
    resources=jobs_to_push,
    events=None,
    having=None,                # optional postfilters on native origin objects
    formatter=a_to_b.format_job,
    batch_size=1000,
    dry_run=False,
)

print("pushed:", result.total_resources_pushed)
print("skipped_missing:", result.skipped_missing)
print("skipped_having:", result.skipped_having)
print("errors:", result.errors)
```

---

### 2.3. Push: Events → Resources

Push based on **events** (`UnifiedJobEvent` / `UnifiedProfileEvent`):

```python
from hrtech_etl.core.models import UnifiedJobEvent
from hrtech_etl.core.types import Resource, PushMode
from hrtech_etl.core.pipeline import push

raw_events = read_raw_events_somewhere()

events: list[UnifiedJobEvent] = []
for raw in raw_events:
    ev = origin.parse_resource_event(Resource.JOB, raw)
    if ev is not None:
        events.append(ev)

result = push(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    mode=PushMode.EVENTS,
    events=events,
    resources=None,
    having=None,                # optional postfilters on native origin jobs
    formatter=a_to_b.format_job,
    batch_size=1000,
    dry_run=False,
)

print("total events:", result.total_events)
print("resources fetched:", result.total_resources_fetched)
print("pushed:", result.total_resources_pushed)
```

Under the hood for `PushMode.EVENTS`:

1. Connector translates unified events → native fetch:

   * `origin.fetch_resources_by_events(Resource.JOB, events)`
2. Core applies `having` (postfilters) to **native** jobs/profiles.
3. Core uses `safe_format_resources(...)` to:

   * either call your `formatter` directly,
   * or fallback to **unified** (origin-native → Unified → target-native) if `formatter is None`.
4. Core calls `target.write_resources_batch(Resource.JOB, formatted_resources)`.

---

### 2.4. Custom Formatters

You can write your own Python formatter for each resource:

```python
from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob, WarehouseAProfile
from hrtech_etl.connectors.warehouse_b.models import WarehouseBJob, WarehouseBProfile

def format_job(job: WarehouseAJob) -> WarehouseBJob:
    return WarehouseBJob(
        job_id=job.job_id,
        title=job.title,
        created_at=job.created_at,
        updated_at=job.updated_at,
        payload=job.payload,
    )

def format_profile(profile: WarehouseAProfile) -> WarehouseBProfile:
    return WarehouseBProfile(
        profile_id=profile.profile_id,
        full_name=profile.full_name,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        payload=profile.payload,
    )

cursor_jobs = pull(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    cursor=cursor,
    formatter=format_job,
)
```

If `formatter` is `None`, the core automatically:

* converts origin-native → unified (`to_unified_job` / `to_unified_profile`)
* then unified → target-native (`from_unified_job` / `from_unified_profile`).

---

### 2.5. Prefilters (WHERE) & Postfilters (HAVING)

#### Prefilters (origin WHERE)

Prefilters are pushed down to the origin warehouse via `Prefilter(...)` plus field metadata (`json_schema_extra["prefilter"]`).

```python
from datetime import datetime
from hrtech_etl.core.expressions import Prefilter
from hrtech_etl.core.types import Resource, Cursor, CursorMode
from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob

prefilters = [
    Prefilter(WarehouseAJob, "title").contains("engineer"),
    Prefilter(WarehouseAJob, "created_at").gte(datetime(2024, 1, 1)),
]

cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc")

cursor_jobs = pull(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    cursor=cursor,
    where=prefilters,      # prefilters (optional)
    having=None,
    formatter=None,
)
```

Example of field metadata:

```python
from pydantic import BaseModel, Field

class WarehouseAJob(BaseModel):
    title: str = Field(
        ...,
        json_schema_extra={
            "prefilter": {"operators": ["eq", "contains"]},
        },
    )
    created_at: datetime = Field(
        ...,
        json_schema_extra={
            "cursor": "created_at",
            "prefilter": {"operators": ["gte", "lte"]},
        },
    )
```

#### Postfilters (origin HAVING)

Postfilters are applied **in memory** on native origin objects:

```python
from hrtech_etl.core.types import Condition, Operator

postfilters = [
    Condition(field="title", op=Operator.CONTAINS, value="Senior"),
]

cursor_jobs = pull(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    cursor=cursor,
    where=prefilters or None,
    having=postfilters or None,
    formatter=None,
)
```

For postfilters:

* All fields are eligible.
* All operators are available (`EQ`, `GT`, `GTE`, `LT`, `LTE`, `IN`, `CONTAINS`).
* No extra metadata required.

---

### 2.6. JSON / Mapping-based Formatters

You can build a formatter from a **mapping spec**. This is what the UI uses behind the scenes.

```python
from hrtech_etl.formatters.base import build_mapping_formatter

mapping = [
    {"from": "job_id", "to": "id"},
    {"from": "title",  "to": "name"},
]

formatter = build_mapping_formatter(mapping)

cursor_jobs = pull(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    cursor=cursor,
    formatter=formatter,
)
```

`build_mapping_formatter(mapping)` returns a callable:

```python
def formatter(origin_obj) -> dict:
    data = {}
    for item in mapping:
        src = item["from"]
        dst = item["to"]
        data[dst] = getattr(origin_obj, src, None)
    return data
```

In the API layer, we store mapping specs in `FORMATTER_REGISTRY` with a `formatter_id`, and rebuild the formatter at runtime.

---

## CLI Usage

The CLI lives in `hrtech_etl/cli.py` and exposes commands like `pull-cmd`.

Typical usage (from the project root):

```bash
python -m hrtech_etl.cli pull-cmd \
  --resource job \
  --origin warehouse_a \
  --target warehouse_b \
  --cursor-mode updated_at \
  --cursor-start "2024-01-01T00:00:00Z" \
  --cursor-sort-by asc \
  --batch-size 1000 \
  --dry-run True
```

You can also pass **WHERE** and **HAVING** as JSON lists of conditions:

```bash
python -m hrtech_etl.cli pull-cmd \
  --resource job \
  --origin warehouse_a \
  --target warehouse_b \
  --cursor-mode updated_at \
  --cursor-start "2024-01-01T00:00:00Z" \
  --cursor-sort-by asc \
  --where '[
    {"field": "board_key", "op": "in",       "value": ["board-1", "board-2"]},
    {"field": "name",      "op": "contains", "value": "engineer"}
  ]' \
  --having '[
    {"field": "updated_at", "op": "gte", "value": "2024-02-01T00:00:00Z"}
  ]' \
  --batch-size 1000 \
  --dry-run True
```

Internally:

* `_parse_conditions(...)` converts each JSON object into a `Condition`.
* `pull(...)` receives `where` and `having` exactly like the Python API.

Once packaged, you can expose this as an entry-point (`hrtech-etl pull-cmd ...`) via `pyproject.toml` if you want.

---

## FastAPI App: API vs Playground

The FastAPI app lives in `app/` and can expose:

* **API** (JSON endpoints)
* **Playground** (HTML UI)
* Or **both**

`app/main.py` builds a single `FastAPI` instance and wires routers based on `HRTECH_ETL_MODE`:

```python
# app/main.py (simplified)
import os
from fastapi import FastAPI
from .api import router as api_router
from .playground import router as playground_router

def create_app() -> FastAPI:
    app = FastAPI(title="hrtech-etl")

    mode = os.getenv("HRTECH_ETL_MODE", "both").lower()
    # "api" | "playground" | "both"

    if mode in ("api", "both"):
        app.include_router(api_router, prefix="/api", tags=["api"])

    if mode in ("playground", "both"):
        app.include_router(playground_router, tags=["playground"])

    return app

app = create_app()
```

### Run in different modes

```bash
# API only (JSON endpoints)
HRTECH_ETL_MODE=api uvicorn app.main:app --reload

# Playground only (HTML UI at /playground)
HRTECH_ETL_MODE=playground uvicorn app.main:app --reload

# Both API + Playground
HRTECH_ETL_MODE=both uvicorn app.main:app --reload
```

### API Highlights

* `GET /api/connectors`
  → list registered connectors (name, label, warehouse_type)

* `GET /api/schema/{connector_name}/{resource}?only_prefilterable=false`
  → native model fields (with cursor/prefilter metadata if declared)

* `GET /api/schema/unified/{resource}`
  → unified model fields (job/profile)

* `POST /api/run/pull`
  → run a pull with `ResourcePullConfig`

* `POST /api/run/push`
  → run a push with `ResourcePushConfig`

* `POST /api/formatters/build`
  → store a mapping spec and return a `formatter_id`

* `POST /api/run/pull_with_formatter` / `POST /api/run/push_with_formatter`
  → same as above, but using a stored `formatter_id`.

### Playground Highlights

`/playground` provides:

* Select origin / target connector
* Select resource (`job`, `profile`)
* Select operation (`pull`, `push`)
* For `pull`:

  * set cursor mode & cursor start / direction
  * configure mapping (origin→target)
  * set prefilters (WHERE) and postfilters (HAVING)
* For `push`:

  * choose `PushMode.RESOURCES` or `PushMode.EVENTS`
  * paste **Resources JSON** (native objects) for `RESOURCES` mode
  * paste **Events JSON** (`UnifiedJobEvent` / `UnifiedProfileEvent`) for `EVENTS` mode

---

## Core Concepts

### 5.1. Resources & Push Modes

In `core/types.py`:

* `Resource` enum:

  * `Resource.JOB`
  * `Resource.PROFILE`
* `PushMode` enum:

  * `PushMode.RESOURCES`
  * `PushMode.EVENTS`

All pull/push operations are parameterized by `resource`.

---

### 5.2. Connectors & Actions

* **BaseConnector** (`core/connector.py`):

  * Knows its native job & profile models:

    * `job_native_cls`
    * `profile_native_cls`
  * Implements generic resource methods:

    * `read_resources_batch(resource, cursor, where, batch_size)`
    * `write_resources_batch(resource, resources)`
    * `get_resource_id(resource, native)`
    * `parse_resource_event(resource, raw)`
    * `fetch_resources_by_events(resource, events)`

* **Per-warehouse connectors** (`connectors/warehouse_a`, `connectors/warehouse_b`, ...):

  * Implement `BaseConnector` for their system.
  * Use an `Actions` class (e.g. `WarehouseAActions`) to perform concrete HTTP / DB / SDK calls.
  * Use `build_connector_params(...)` to translate **unified Conditions + Cursor** into backend query params based on model metadata.

---

### 5.3. Native & Unified Models

* Native models: e.g. `WarehouseAJob`, `WarehouseAProfile`

  * Pydantic models with connector-specific fields.
  * Use `json_schema_extra` to annotate:

    * cursor metadata
    * prefilter operators
    * search binding
    * IN binding

* Unified models (`core/models.py`):

  * `UnifiedJob`, `UnifiedProfile`
  * `UnifiedJobEvent`, `UnifiedProfileEvent`
  * Provide a standardized layer when no explicit formatter is provided.

Connectors implement:

* `to_unified_job(...)` / `from_unified_job(...)`
* `to_unified_profile(...)` / `from_unified_profile(...)`

---

### 5.4. Cursor & Cursor Modes

`Cursor` and `CursorMode` (in `core/types.py`):

```python
class CursorMode(str, Enum):
    UID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

class Cursor(BaseModel):
    mode: CursorMode
    start: str | None = None
    end: str | None = None
    sort_by: str = "asc"  # "asc" | "desc"
```

Unified models and native models declare cursor fields via `json_schema_extra`:

```python
from pydantic import BaseModel, Field
from hrtech_etl.core.types import CursorMode

class UnifiedJob(BaseModel):
    created_at: Optional[str] = Field(
        ...,
        json_schema_extra={
            "cursor": CursorMode.CREATED_AT.value,
            "cursor_start_min": "date_range_min",
            "cursor_end_max": "date_range_max",
            "cursor_order_up": "asc",
            "cursor_order_down": "desc",
            "prefilter": {"operators": ["gte", "lte"]},
        },
    )
```

`build_cursor_query_params(...)` in `core/utils.py` reads those metadata and builds:

* the correct param names for ranges (`date_range_min`, `date_range_max` or fallbacks)
* consistent handling of `asc` / `desc` across `start` and `end`.

---

### 5.5. Formatters

In `formatters/base.py`:

* `JobFormatter` / `ProfileFormatter` Protocols
* `build_mapping_formatter(mapping)` to build a dict-based formatter
* `FORMATTER_REGISTRY` to store mapping specs in memory for the API & Playground

Core uses a single helper:

```python
safe_format_resources(
    resource,
    origin,
    target,
    formatter,
    native_resources,
)
```

Behavior:

* If `formatter` is provided:

  * For each native resource, call `formatter(...)`.
  * If it returns:

    * a `BaseModel` → used as is.
    * a `dict` → wrapped into the target native model.
* If `formatter` is `None`:

  * Fallback path: origin-native → unified → target-native.

---

### 5.6. Conditions, Prefilters & UI Schema

* `Condition` / `Operator` (in `core/types.py`) model filter expressions.
* `Prefilter` (in `core/expressions.py`) builds metadata-aware prefilters on a given model.
* `export_model_fields(model_cls, only_prefilterable)` (in `core/ui_schema.py`) exposes:

  * `name`: field name
  * `type`: Python type name
  * `cursor`: cursor tag (if any)
  * `prefilter`: config (`operators`, etc.)

This is used by:

* the API (`/api/schema/...`)
* the Playground UI to populate dropdowns.

---

### 5.7. Query Param Bindings: cursor / search / IN

The generic query param builder lives in `core/utils.py`:

```python
build_connector_params(
    resource_cls: Type[BaseModel],
    where: Optional[List[Condition]],
    cursor: Optional[Cursor],
    *,
    sort_by_unified: Optional[str],
    sort_param_name: Optional[str],
) -> Dict[str, Any]
```

Under the hood it orchestrates:

* `build_eq_query_params(...)`
* `build_in_query_params(...)`
* `build_search_query_params(...)`
* `build_cursor_query_params(...)`

#### IN Binding (`in_binding`)

In models:

```python
board_key: str = Field(
    ...,
    json_schema_extra={
        "prefilter": {"operators": ["in"]},
        "in_binding": {
            "query_field": "board_keys",   # HTTP query name
            "formatter": "string_array",   # "array" | "csv" | "array_string"
        },
    },
)
```

If `query_field` is omitted, default is `field__in`.
If `formatter` is omitted, default is `array` (Python list).

`build_in_query_params(...)` handles grouping and formatting.

#### Search Binding (`search_binding`)

In unified models:

```python
from hrtech_etl.core.types import BoolJoin

name: str = Field(
    ...,
    json_schema_extra={
        "prefilter": {"operators": ["contains"]},
        "search_binding": {
            "search_field": "keywords",
            "field_join": BoolJoin.OR,    # how this field joins other fields
            "value_join": BoolJoin.AND,   # how multiple values on this field are joined
        },
    },
)

text: str = Field(
    ...,
    json_schema_extra={
        "search_binding": {
            "search_field": "keywords",
            "field_join": BoolJoin.AND,
            "value_join": BoolJoin.OR,
        },
    },
)
```

Given `WHERE` conditions like:

* `name CONTAINS "data"`
* `text CONTAINS "science"`
* `skills CONTAINS ["python", "sql"]` (with its own binding)

`build_search_query_params(...)` will produce something like:

```python
{
  "keywords": "(data) AND (science) AND (python OR sql)"
}
```

depending on `field_join` / `value_join` per field.

---

## Repository Structure

```bash
hrtech-etl/
├─ pyproject.toml
├─ README.md
├─ CONTRIBUTING.md
├─ LICENSE
├─ cli.py                      # CLI entrypoint (pull_cmd, push_cmd using core.pipeline)
│
├─ src/
│  └─ hrtech_etl/
│     ├─ __init__.py
│     │
│     ├─ core/
│     │  ├─ __init__.py
│     │  ├─ auth.py            # BaseAuth, ApiKeyAuth, BearerAuth, ...
│     │  ├─ types.py           # Resource, WarehouseType, Cursor, CursorMode, Condition, Operator,
│     │  │                     # PushMode, PushResult, BoolJoin, Formatter, ...
│     │  ├─ models.py          # UnifiedJob, UnifiedProfile, UnifiedJobEvent, UnifiedProfileEvent
│     │  │                     # + metadata: prefilter, search_binding, in_binding, cursor_*
│     │  ├─ connector.py       # BaseConnector (generic jobs/profiles/events abstraction)
│     │  ├─ expressions.py     # Prefilter(...) → metadata-aware Condition builders
│     │  ├─ ui_schema.py       # export_model_fields(...) for UI (cursor + prefilter metadata)
│     │  ├─ utils.py           # safe_format_resources, apply_postfilters,
│     │  │                     # get_cursor_native_name/value, build_eq_query_params,
│     │  │                     # build_in_query_params, build_search_query_params,
│     │  │                     # build_cursor_query_params, build_connector_params
│     │  ├─ registry.py        # ConnectorMeta, register_connector, get_connector_instance
│     │  └─ pipeline.py        # pull(...), push(...), ResourcePullConfig, ResourcePushConfig,
│     │                        # run_resource_pull_from_config(...), run_resource_push_from_config(...)
│     │
│     ├─ connectors/
│     │  ├─ __init__.py
│     │  ├─ warehouse_a/
│     │  │  ├─ __init__.py     # WarehouseAConnector implementation + registration via ConnectorMeta
│     │  │  ├─ models.py       # WarehouseAJob, WarehouseAProfile, WarehouseAJobEvent, WarehouseAProfileEvent
│     │  │  ├─ actions.py      # WarehouseAActions (low-level HTTP/DB/SDK client using build_connector_params)
│     │  │  └─ test.py         # Merged tests:
│     │  │                     #  - direct pull(...) with DummyActions
│     │  │                     #  - FastAPI integration tests via TestClient (api.run_pull / api.run_push)
│     │  └─ warehouse_b/
│     │     ├─ __init__.py     # (placeholder / example connector)
│     │     ├─ models.py       # (placeholder native models)
│     │     ├─ actions.py      # (placeholder actions client)
│     │     └─ test.py         # (optional example tests or left minimal)
│     │
│     └─ formatters/
│        ├─ __init__.py
│        ├─ base.py            # FORMATTER_REGISTRY, JobFormatter/ProfileFormatter Protocols,
│        │                     # build_mapping_formatter(mapping) for mapping-based formatters
│        └─ a_to_b.py          # Example formatter: WarehouseA → WarehouseB (job/profile mapping)
│
├─ app/
│  ├─ __init__.py
│  ├─ api.py                   # JSON API routes:
│  │                           #  - /api/connectors
│  │                           #  - /api/schema/{connector}/{resource}
│  │                           #  - /api/schema/unified/{resource}
│  │                           #  - /api/run/pull
│  │                           #  - /api/run/push
│  │                           #  - /api/formatters/build, /api/formatters/{id},
│  │                           #  - /api/run/pull_with_formatter, /api/run/push_with_formatter
│  ├─ playground.py            # HTML playground:
│  │                           #  - configure origin/target, resource, cursor
│  │                           #  - build mapping, prefilters (WHERE), postfilters (HAVING)
│  │                           #  - push RESOURCES / EVENTS via pasted JSON
│  ├─ main.py                  # create_app() using HRTECH_ETL_MODE = api | playground | both
│  └─ templates/
│     └─ playground.html       # Jinja2 template powering the playground UI
│
└─ tests/
   └─ (empty for now)          # Reserved for future core / integration tests
                               # Connector-specific tests live close to connectors
```

---

## Roadmap / Status

> This is a **WIP** (work in progress).

Planned / in-progress:

* [ ] DevOps v1: local integration environment (Poetry / uv)
* [ ] DevOps v2: GitHub workflow + package release bumping through PR
* [ ] Real-world ATS / CRM / Jobboard / HCM connectors
* [ ] Better type coercion for filters (dates, ints, enums)
* [ ] Worker-style pull pipeline + event hooks for push
* [ ] Add MCP / Agent integrations
* [ ] Expand test coverage & CI (lint, type-check, e2e scenarios)

---

## Contributing

Contributions are very welcome ❤️

* Add a new connector (ATS / CRM / Jobboard / HCM)
* Extend the playground
* Add new filter operators or cursor strategies
* Improve docs and examples

See [CONTRIBUTING.md](./CONTRIBUTING.md) for:

* repo layout
* dev setup
* coding guidelines
* how to add a connector
* how to extend the API / playground
* how to submit a PR

---

## License

Distributed under the **MIT License**. See [LICENSE](./LICENSE) for details.

