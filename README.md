# HrTech ETL (WIP)

Opensource ETL framework for **HRTech data** (jobs & profiles) across **ATS, CRM, Jobboard, and HCM** systems.

- Focused on **connectors** (per warehouse)
- Uses **Pydantic models** for native & unified objects
- Supports **cursor-based sync**, **pre-filtering**, **post-filtering**, and **pluggable formatters**
- Ships with a **FastAPI backend** that can run in **API** mode or **Playground** (no-code UI) mode

---

## Table of Contents

1. [Features](#features)  
2. [Quick Start (Python)](#quick-start-python)  
   - [Basic Jobs & Profiles Sync](#basic-jobs--profiles-sync)  
   - [Custom Format Functions](#custom-format-functions)  
   - [Where Conditions / Pre-filtering](#where-conditions--pre-filtering)  
   - [Run Pipeline Using JSON / Mapping Formatter](#run-pipeline-using-json--mapping-formatter)  
3. [FastAPI App: API vs Playground](#fastapi-app-api-vs-playground)  
4. [Core Concepts](#core-concepts)  
   - [Connectors & Actions](#connectors--actions)  
   - [Native & Unified Models](#native--unified-models)  
   - [Cursor Modes](#cursor-modes)  
   - [Formatters](#formatters)  
   - [Conditions & UI Schema](#conditions--ui-schema)  
5. [Repository Structure](#repository-structure)  
6. [Roadmap / Status](#roadmap--status)  
7. [License](#license)

---

## Features

- 🔌 **Warehouse Connectors** for ATS, CRM, Jobboard, HCM  
- 🧱 **Pydantic-native models** per warehouse (jobs & profiles)
- 🧩 **UnifiedJob / UnifiedProfile** as optional normalized layer
- 🔄 **Cursor-based incremental sync** (ID / created_at / updated_at)
- 🎛️ **Pre-filtering** (WHERE at origin) using a typed `Condition` model
- 🎚️ **Post-filtering** (in-memory) on native origin objects
- 🧬 **Formatter functions**:
  - native→native (WarehouseAJob → WarehouseBJob)
  - native→unified and unified→native
  - no-code mapping formatter (built from UI)
- 🌐 **FastAPI backend**:
  - `/api/...` JSON endpoints (connectors, schema, run ETL, build formatter)
  - `/playground` HTML UI to build mappings & filters without coding

---

## TODO
- NativeFilersFn to post-filter native resource from Origin Wharehouse
- Add pull_profiles logic to api
- Add pull_profiles logic to playground
- Add pull pipeline Worker to api
- Add pull pipeline Worker to playground
- Add push pipeline logic to api
- Add push pipeline ui to playground
- Add push pipeline Worker to api
- Add push pipeline Worker to playground

## Quick Start (Python)

### Basic Jobs & Profiles Sync

```python
from hrtech_etl.core.types import CursorMode
from hrtech_etl.core.auth import ApiKeyAuth, BearerAuth
from hrtech_etl.core.pipeline import pull_jobs, pull_profiles

from hrtech_etl.connectors.warehouse_a import WarehouseAConnector, WarehouseAActions
from hrtech_etl.connectors.warehouse_b import WarehouseBConnector, WarehouseBActions

from hrtech_etl.formatters import a_to_b

# --- Instantiate connectors ---

origin = WarehouseAConnector(
    auth=ApiKeyAuth("X-API-Key", "AAA"),
    actions=WarehouseAActions(client_a),
)

target = WarehouseBConnector(
    auth=BearerAuth("BBB"),
    actions=WarehouseBActions(client_b),
)

# --- Sync JOBS: A -> B using formatter a_to_b.format_job ---
last_job_cursor = pull_jobs(
    origin=origin,
    target=target,
    cursor_mode=CursorMode.UPDATED_AT,  # or CREATED_AT / ID
    format_fn=a_to_b.format_job,        # standard job formatter
    batch_size=5000,
)

# --- Sync PROFILES: A -> B using formatter a_to_b.format_profile ---
last_profile_cursor = pull_profiles(
    origin=origin,
    target=target,
    cursor_mode=CursorMode.UPDATED_AT,
    format_fn=a_to_b.format_profile,
    batch_size=5000,
)

# You can store last_job_cursor / last_profile_cursor to resume on next run.
````

---

### Custom Format Functions

You can write your own formatter to map from Warehouse A models to Warehouse B models:

```python
from hrtech_etl.formatters.base import JobFormatter, ProfileFormatter
from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob, WarehouseAProfile
from hrtech_etl.connectors.warehouse_b.models import WarehouseBJob, WarehouseBProfile


def format_job(job: WarehouseAJob) -> WarehouseBJob:
    # map fields from A to B
    return WarehouseBJob(
        job_id=job.job_id,
        title=job.job_title,
        # ... other fields
    )


def format_profile(profile: WarehouseAProfile) -> WarehouseBProfile:
    # map fields from A to B
    return WarehouseBProfile(
        profile_id=profile.profile_id,
        full_name=profile.full_name,
        # ... other fields
    )
```

Then:

```python
last_job_cursor = pull_jobs(
    origin=origin,
    target=target,
    cursor_mode=CursorMode.UPDATED_AT,
    format_fn=format_job,
)
```

---

### Where Conditions / Pre-filtering

You can build **pre-filters** using the expression helpers and metadata on the Pydantic models:

```python
from hrtech_etl.core.expressions import field
from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob

where_jobs = [
    field(WarehouseAJob, "job_title").contains("engineer"),
    field(WarehouseAJob, "created_on").gte(my_date),
]

last_job_cursor = pull_jobs(
    origin=origin,
    target=target,
    cursor_mode=CursorMode.UPDATED_AT,
    where=where_jobs,            # list[Condition]
    format_fn=a_to_b.format_job,
)
```

Each `Condition` is a typed object (`field`, `op`, `value`) that connectors translate into their own query parameters or SQL.

---

### Run Pipeline Using JSON / Mapping Formatter

You can also drive the pipeline from **JSON config** and a simple **field mapping** (built from UI):

```python
from hrtech_etl.core.pipeline import pull_jobs
from hrtech_etl.core.types import CursorMode
from hrtech_etl.formatters.base import build_mapping_formatter
from app.main import FORMATTER_REGISTRY


def run_job_pull_with_formatter_id(origin, target, formatter_id: str):
    # formatter_id → stored mapping spec: [{"from": "job_title", "to": "title"}, ...]
    mapping = FORMATTER_REGISTRY[formatter_id]
    format_fn = build_mapping_formatter(mapping)

    return pull_jobs(
        origin=origin,
        target=target,
        cursor_mode=CursorMode.UPDATED_AT,
        format_fn=format_fn,
        batch_size=5000,
    )
```

In this model:

* The **frontend** posts a mapping spec to `/api/formatters/build`.
* The backend stores it in `FORMATTER_REGISTRY` with a `formatter_id`.
* You can then use `formatter_id` in ETL configs to reconstruct the Python formatter with `build_mapping_formatter()`.

---

## FastAPI App: API vs Playground

The project includes a small FastAPI app (in `app/`) with two routers:

* `app/api.py` → JSON API
* `app/playground.py` → HTML UI (no-code playground)

`app/main.py` creates a single `FastAPI` app and wires routers based on an **environment variable**:

```python
# app/main.py
import os
from fastapi import FastAPI
from .api import router as api_router
from .playground import router as playground_router

def create_app() -> FastAPI:
    app = FastAPI(title="hrtech-etl")

    mode = os.getenv("mode", "both").lower()
    # mode can be: "api", "playground", "both"

    if mode in ("api", "both"):
        app.include_router(api_router, prefix="/api", tags=["api"])

    if mode in ("playground", "both"):
        app.include_router(playground_router, tags=["playground"])

    return app


app = create_app()
```

### Start in API / Playground / Both modes

```bash
# API only (JSON endpoints under /api)
mode=api uvicorn app.main:app --reload

# Playground only (HTML UI at /playground)
mode=playground uvicorn app.main:app --reload

# Both API + Playground
mode=both uvicorn app.main:app --reload
```

* API mode: use endpoints like `/api/connectors`, `/api/schema/{connector}/job`, `/api/run/job-pull`, `/api/formatters/build`.
* Playground mode: visit `http://localhost:8000/playground` and configure everything via forms (origin/target, resource, mapping, pre/post filters).

---

## Core Concepts

### Connectors & Actions

* **BaseConnector** (`core/connector.py`):

  * Abstract class that defines:

    * `read_jobs_batch`, `write_jobs_batch`
    * `read_profiles_batch`, `write_profiles_batch`
    * which native Pydantic models it uses (`job_native_cls`, `profile_native_cls`)
* **Warehouse connectors** (e.g. `connectors/warehouse_a`, `connectors/warehouse_b`):

  * Implement `BaseConnector` with warehouse-specific I/O logic.
  * Use **Actions classes** to encapsulate HTTP/DB access:

    * `WarehouseAActions`, `WarehouseBActions`, etc.

### Native & Unified Models

* **Native models**: e.g. `WarehouseAJob`, `WarehouseAProfile` in each connector:

  * Pydantic models with fields like `job_id`, `job_title`, `last_modified`, `created_on`, etc.
  * Use `json_schema_extra` to store:

    * `cursor` role (`"updated_at"`, `"created_at"`, `"id"`)
    * `filter` metadata (`eligible`, `operators`)
* **Unified models** (`core/models.py`):

  * `UnifiedJob`, `UnifiedProfile`:

    * Optional normalized schema across warehouses.
  * Each connector can implement:

    * `to_unified_job`, `from_unified_job`
    * `to_unified_profile`, `from_unified_profile`

Formatters can either use:

* native→native directly, or
* native→unified→native pipeline.

### Cursor Modes

`CursorMode` (in `core/types.py`) defines how incremental sync is done:

* `CursorMode.ID`
* `CursorMode.CREATED_AT`
* `CursorMode.UPDATED_AT`

Connectors read cursor metadata from model fields (via `json_schema_extra["cursor"]`) and use `get_cursor_value` to extract the right value.

### Formatters

Formatters are just callables:

* `JobFormatter`: `(job_native) -> Anything`
* `ProfileFormatter`: `(profile_native) -> Anything`

You have multiple options:

* Standard formatters (e.g. `format_job`, `format_profile` in `formatters/a_to_b.py`)
* Unified-based formatters (`formatters/unified.py`)
* **Mapping-based formatter** built from a list of `{from, to}` mappings via `build_mapping_formatter`.

### Conditions & UI Schema

* `Condition` (`core/types.py`):

  * `field: str`, `op: Operator`, `value: Any`
* `Operator` enum:

  * `EQ`, `GT`, `LT`, `GTE`, `LTE`, `IN`, `CONTAINS`
* `field(model_cls, "field_name")` in `core/expressions.py` builds a typed **Condition builder**:

  * Uses field metadata to check allowed operators.
* `export_model_fields(model_cls, filterable_only=False)` in `core/ui_schema.py`:

  * Returns metadata for the UI:

    * `name`, `type`, `cursor`, `filter` (eligible + operators)
  * Used by the API routes to power the no-code playground.

---

## Repository Structure

```bash
hrtech-etl/
├─ pyproject.toml
├─ README.md
│
├─ src/
│  └─ hrtech_etl/
│     ├─ __init__.py
│     │
│     ├─ core/
│     │  ├─ __init__.py
│     │  ├─ auth.py          # BaseAuth, ApiKeyAuth, TokenAuth, BearerAuth
│     │  ├─ types.py         # WarehouseType, CursorMode, Condition, Operator, FilterFn
│     │  ├─ models.py        # UnifiedJob, UnifiedProfile (Pydantic)
│     │  ├─ connector.py     # BaseConnector (jobs + profiles, Pydantic-native)
│     │  ├─ actions.py       # BaseActions (wraps low-level client, tracks _request_count)
│     │  ├─ utils.py         # single_request, get_cursor_value, shared helpers
│     │  ├─ expressions.py   # field(...) helpers to build Condition objects
│     │  ├─ ui_schema.py     # export_model_fields for UI (fields, filter metadata, cursors)
│     │  ├─ registry.py      # ConnectorMeta, register_connector, get_connector_instance
│     │  └─ pipeline.py      # pull_jobs / pull_profiles + JobPullConfig / run_*_from_config
│     │
│     ├─ connectors/
│     │  ├─ __init__.py      # optional: re-export connectors
│     │  │
│     │  ├─ warehouse_a/
│     │  │  ├─ __init__.py   # WarehouseAConnector + registry registration
│     │  │  ├─ models.py     # WarehouseAJob, WarehouseAProfile (Pydantic, cursor metadata, filter meta)
│     │  │  ├─ actions.py    # WarehouseAActions (HTTP/DB client)
│     │  │  └─ test.py       # tests for this connector
│     │  │
│     │  └─ warehouse_b/
│     │     ├─ __init__.py   # WarehouseBConnector + registry registration
│     │     ├─ models.py     # WarehouseBJob, WarehouseBProfile
│     │     ├─ actions.py    # WarehouseBActions
│     │     └─ test.py       # tests for this connector
│     │
│     └─ formatters/
│        ├─ __init__.py      # registry helpers, type aliases
│        ├─ base.py          # Protocols / type hints, MappingSpec, build_mapping_formatter, FORMATTER_REGISTRY
│        ├─ a_to_b.py        # example: WarehouseA -> WarehouseB standard formatters
│        └─ unified.py       # example: unified<->unified / unified->report format
│
├─ app/
│  ├─ __init__.py
│  ├─ api.py                 # JSON API router (/api/...)
│  ├─ playground.py          # HTML form-based playground (/playground)
│  └─ main.py                # create_app(), mode switch via HRTECH_ETL_MODE env var
│
└─ tests/
   └─ test.py                # core framework tests (pipeline, utils, unified models, etc.)
```

---

## Roadmap / Status

> This is a **WIP** (work in progress).

Planned / in-progress:

* [ ] Tighten connector implementations (real HTTP/DB clients)
* [ ] Improve type coercion for filters (dates, ints, enums)
* [ ] Add more warehouse templates (ATS / CRM / Jobboard / HCM)
* [ ] Persist formatters & configs (beyond in-memory registry)
* [ ] Add more tests & CI

---

## License

TBD (MIT is a good default).
