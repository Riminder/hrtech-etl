<p align="center">
<div style="width:260px; height:100px; overflow:hidden; border-radius:8px;">
  <img src="./logo.png"
       style="width:100%; height:auto; object-fit:cover; object-position:center 50%;" />
</div>

<p align="center">
  <a href="https://pypi.org/project/jobcurator/"><img src="https://img.shields.io/pypi/v/jobcurator.svg" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/jobcurator/"><img src="https://img.shields.io/pypi/pyversions/jobcurator.svg" alt="Python Versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
</p>

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
   - [Connectors & Requests](#connectors--requests)  
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
- 🧬 Optional **UnifiedJob / UnifiedProfile** as a normalized layer
- 🔄 **Cursor-based incremental sync** (ID / created_at / updated_at)
- 🎛️ **Prefilters** on origin (metadata-driven, via `prefilter` JSON schema on fields)
- 🎚️ **Postfilters** in core on native origin objects (any field, richer operators)
- 🧩 **Formatter functions**:
  - explicit native→native (e.g. WarehouseAJob → WarehouseBJob)
  - native→unified→native via connector hooks
  - JSON-driven mapping formatters
- 🌐 **FastAPI backend**:
  - `/api/...` JSON endpoints (connectors, schema, run ETL, build formatter)
  - `/playground` HTML UI for no-code mapping + pre/post filters + cursor control


---

## Quick Start (Python)

### Basic Jobs & Profiles Sync

```python
from hrtech_etl.core.types import CursorMode
from hrtech_etl.core.auth import ApiKeyAuth, BearerAuth
from hrtech_etl.core.pipeline import pull_jobs, pull_profiles

from hrtech_etl.connectors.warehouse_a import WarehouseAConnector, WarehouseARequests
from hrtech_etl.connectors.warehouse_b import WarehouseBConnector, WarehouseBRequests

from hrtech_etl.formatters import a_to_b

# --- Instantiate connectors ---

origin = WarehouseAConnector(
    auth=ApiKeyAuth("X-API-Key", "AAA"),
    requests=WarehouseARequests(client_a),
)

target = WarehouseBConnector(
    auth=BearerAuth("BBB"),
    requests=WarehouseBRequests(client_b),
)

# --- Sync JOBS: A -> B using formatter a_to_b.format_job ---
last_job_cursor = pull_jobs(
    origin=origin,
    target=target,
    cursor_mode=CursorMode.UPDATED_AT,  # or CREATED_AT / ID
    formatter=a_to_b.format_job,        # standard job formatter
    limit=5000,
)

# --- Sync PROFILES: A -> B using formatter a_to_b.format_profile ---
last_profile_cursor = pull_profiles(
    origin=origin,
    target=target,
    cursor_mode=CursorMode.UPDATED_AT,
    formatter=a_to_b.format_profile,
    limit=5000,
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
    formatter=format_job,
)
```

---

### Prefilters (origin WHERE)

Prefilters are pushed down to the origin warehouse (SQL / HTTP WHERE), and are **metadata-driven** on the Pydantic models via `json_schema_extra["prefilter"]`.

```python
from hrtech_etl.core.expressions import Prefilter
from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob

prefilters = [
    Prefilter(WarehouseAJob, "job_title").contains("engineer"),
    Prefilter(WarehouseAJob, "created_on").gte(my_date),
]

last_job_cursor = pull_jobs(
    origin=origin,
    target=target,
    cursor_mode=CursorMode.UPDATED_AT,
    cursor_start=None,
    where=prefilters,  # prefilters → translated into origin query
    formatter=a_to_b.format_job,
)
```

Each `Condition` is a typed object (`field`, `op`, `value`) that connectors translate into their own query parameters or SQL.

```python
job_title: str = Field(
    ...,
    json_schema_extra={
        "prefilter": {
            "operators": ["eq", "contains"],
        },
    },
)
```

### Postfilters (origin HAVING)

They can target any field and use all operators (no per-field metadata required).

```python 
from hrtech_etl.core.types import Condition, Operator

postfilters = [
    Condition(field="status", op=Operator.EQ, value="open"),
    Condition(field="location", op=Operator.CONTAINS, value="Remote"),
]

last_job_cursor = pull_jobs(
    origin=origin,
    target=target,
    cursor_mode=CursorMode.UPDATED_AT,
    where=where_jobs,          # prefilters (optional)
    having=postfilters,   # postfilters applied in-memory on native objects
    format_fn=a_to_b.format_job,
)
```

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
    formatter = build_mapping_formatter(mapping)

    return pull_jobs(
        origin=origin,
        target=target,
        cursor_mode=CursorMode.UPDATED_AT,
        formatter=formatter,
        limit=5000,
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

### Connectors & Requests

* **BaseConnector** (`core/connector.py`):

  * Abstract class that defines:

    * `read_jobs_batch`, `write_jobs_batch`
    * `read_profiles_batch`, `write_profiles_batch`
    * which native Pydantic models it uses (`job_native_cls`, `profile_native_cls`)
* **Warehouse connectors** (e.g. `connectors/warehouse_a`, `connectors/warehouse_b`):

  * Implement `BaseConnector` with warehouse-specific I/O logic.
  * Use **Requests classes** to encapsulate HTTP/DB access:

    * `WarehouseARequests`, `WarehouseBRequests`, etc.

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
│     │  ├─ types.py         # WarehouseType, CursorMode, Condition, Operator
│     │  ├─ models.py        # UnifiedJob, UnifiedProfile (Pydantic)
│     │  ├─ connector.py     # BaseConnector (jobs + profiles, Pydantic-native)
│     │  ├─ requests.py       # BaseRequests (wraps low-level client, tracks _request_count)
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
│     │  │  ├─ requests.py   # WarehouseARequests (HTTP/DB client)
│     │  │  └─ test.py       # tests for this connector
│     │  │
│     │  └─ warehouse_b/
│     │     ├─ __init__.py   # WarehouseBConnector + registry registration
│     │     ├─ models.py     # WarehouseBJob, WarehouseBProfile
│     │     ├─ requests.py   # WarehouseBRequests
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
## TODO
* [ ] Add pull_profiles logic to api
* [ ] Add pull_profiles logic to playground
* [ ] Add push pipeline logic to api
* [ ] Add push pipeline ui to playground
* [ ] Add pull pipeline Worker to playground
* [ ] Add push pipeline Worker to playground
* [ ] Tighten connector implementations (real HTTP/DB clients)
* [ ] Improve type coercion for filters (dates, ints, enums)
* [ ] Add more warehouse templates (ATS / CRM / Jobboard / HCM)
* [ ] Persist formatters & configs (beyond in-memory registry)
* [ ] add pydantic gateway : https://pydantic.dev/ai-gateway 
* [ ] Add more tests & CI

---

## License

MIT Licence.
