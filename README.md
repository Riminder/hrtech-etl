<p align="center">
<div style="width:260px; height:100px; overflow:hidden; border-radius:8px;">
  <img src="./logo.png" style="width:100%; height:auto; object-fit:cover; object-position:center 50%;" />
</div>

<p align="center">
  <a href="https://pypi.org/project/jobcurator/"><img src="https://img.shields.io/pypi/v/jobcurator.svg" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/jobcurator/"><img src="https://img.shields.io/pypi/pyversions/jobcurator.svg" alt="Python Versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
</p>


# HrTech ETL (WIP)

Opensource ETL framework for **HRTech data** (jobs & profiles) across **ATS, CRM, Jobboard, and HCM** systems.

- Focused on **connectors** (per external warehouse)
- Uses **Pydantic models** for native & unified objects
- Supports **cursor-based incremental sync**, **pre-filtering**, **post-filtering**
- Supports **pull & push pipelines** for **resources** and **events**
- Uses **pluggable formatters** (Python or mapping-based)
- Ships with a **FastAPI backend** that can run in **API**, **Playground**, or **both** modes

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
3. [FastAPI App: API vs Playground](#fastapi-app-api-vs-playground)  
4. [Core Concepts](#core-concepts)  
   4.1. [Resources & Push Modes](#41-resources--push-modes)  
   4.2. [Connectors & Requests](#42-connectors--requests)  
   4.3. [Native & Unified Models](#43-native--unified-models)  
   4.4. [Cursor & Cursor Modes](#44-cursor--cursor-modes)  
   4.5. [Formatters](#45-formatters)  
   4.6. [Conditions, Prefilters & UI Schema](#46-conditions-prefilters--ui-schema)  
5. [Repository Structure](#repository-structure)  
6. [Roadmap / Status](#roadmap--status)  
7. [Contributing](#contributing)  
8. [License](#license)

---

## Features

- 🔌 **Warehouse Connectors** for ATS, CRM, Jobboard, HCM  
- 🧱 **Pydantic-native models** per warehouse (jobs & profiles)
- 🧬 Optional **UnifiedJob / UnifiedProfile / UnifiedJobEvent / UnifiedProfileEvent** as normalized layer
- 🔄 **Cursor-based incremental pull** on:
  - `id`
  - `created_at`
  - `updated_at`
- 🎛️ **Prefilters** on origin (metadata-driven, via `prefilter` JSON schema on fields)
- 🎚️ **Postfilters** in core on native origin objects (any field, richer operators)
- 🧩 **Formatter functions**:
  - explicit native→native (e.g. `WarehouseAJob → WarehouseBJob`)
  - native→unified→native via connector hooks
  - JSON-driven mapping formatters (built in the UI)
- 📡 **Push pipeline** with two modes:
  - `PushMode.RESOURCES` → push native resources
  - `PushMode.EVENTS` → push from events (`UnifiedJobEvent` / `UnifiedProfileEvent`)
- 🌐 **FastAPI backend**:
  - `/api/...` JSON endpoints (connectors, schema, run pull/push, build formatters)
  - `/playground` HTML UI for no-code mapping + pre/post filters + cursor control + events/resources JSON

---

## Quick Start (Python)

### 2.1. Pull: Jobs & Profiles

The core pull primitive is:

```python
from hrtech_etl.core.types import Resource, Cursor, CursorMode
from hrtech_etl.core.auth import ApiKeyAuth, BearerAuth
from hrtech_etl.core.pipeline import pull

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

# start from scratch (no cursor yet)
cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None)

# --- PULL JOBS: A -> B ---
cursor_jobs = pull(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    cursor=cursor,
    formatter=a_to_b.format_job,   # JOB formatter
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
    formatter=a_to_b.format_profile,  # PROFILE formatter
    batch_size=5000,
)

print("profiles cursor_end:", cursor_profiles.end)

# Store cursor_jobs.end / cursor_profiles.end to resume on next run.
````

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

# Connector-specific decoding: raw → UnifiedJobEvent
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

1. The connector translates **unified events** → internal fetch requests:

   * `fetch_resources_by_events(Resource.JOB, events)`
2. Core applies `having` (postfilters) to the **native** jobs.
3. Core uses `safe_format_resources(...)` to:

   * either use your `formatter` directly
   * or fall back to unified (origin-native → Unified → target-native) if no formatter.
4. Core calls `target.write_resources_batch(Resource.JOB, formatted_resources)`.

---

### 2.4. Custom Formatters

You can write your own Python formatter for each resource:

```python
from hrtech_etl.formatters.base import JobFormatter, ProfileFormatter
from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob, WarehouseAProfile
from hrtech_etl.connectors.warehouse_b.models import WarehouseBJob, WarehouseBProfile

def format_job(job: WarehouseAJob) -> WarehouseBJob:
    return WarehouseBJob(
        job_id=job.job_id,
        title=job.job_title,
        # ...
    )

def format_profile(profile: WarehouseAProfile) -> WarehouseBProfile:
    return WarehouseBProfile(
        profile_id=profile.profile_id,
        full_name=profile.full_name,
        # ...
    )

cursor_jobs = pull(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    cursor=cursor,
    formatter=format_job,
)
```

If `formatter` is `None`, the core will automatically:

* convert origin-native → unified (`to_unified_job` / `to_unified_profile`)
* then unified → target-native (`from_unified_job` / `from_unified_profile`).

---

### 2.5. Prefilters (WHERE) & Postfilters (HAVING)

#### Prefilters (origin WHERE)

Prefilters are pushed down to the origin warehouse via `Prefilter(...)` and metadata on fields (`json_schema_extra["prefilter"]`).

```python
from hrtech_etl.core.expressions import Prefilter
from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob
from hrtech_etl.core.types import Cursor, CursorMode, Resource

prefilters = [
    Prefilter(WarehouseAJob, "job_title").contains("engineer"),
    Prefilter(WarehouseAJob, "created_on").gte(my_date),
]

cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None)

cursor_jobs = pull(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    cursor=cursor,
    where=prefilters,      # prefilters (optional)
    having=None,
    formatter=a_to_b.format_job,
)
```

Each `Prefilter(...)` call checks allowed operators for the field from the model’s metadata:

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

#### Postfilters (origin HAVING)

Postfilters are applied **in memory** on native origin objects (after each batch for pull, before push):

```python
from hrtech_etl.core.types import Condition, Operator

postfilters = [
    Condition(field="status", op=Operator.EQ, value="open"),
    Condition(field="location", op=Operator.CONTAINS, value="Remote"),
]

cursor_jobs = pull(
    resource=Resource.JOB,
    origin=origin,
    target=target,
    cursor=cursor,
    where=prefilters or None,
    having=postfilters or None,
    formatter=a_to_b.format_job,
)
```

For postfilters:

* All fields are eligible.
* All operators are allowed (`EQ`, `GT`, `GTE`, `LT`, `LTE`, `IN`, `CONTAINS`).
* No field-level metadata required.

---

### 2.6. JSON / Mapping-based Formatters

You can build a formatter from a **mapping spec**. This is useful for the no-code UI.

```python
from hrtech_etl.formatters.base import build_mapping_formatter

mapping = [
    {"from": "job_title", "to": "title"},
    {"from": "location", "to": "city"},
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

In the **API** layer, you can store mapping specs by `formatter_id`:

```python
from hrtech_etl.formatters.base import FORMATTER_REGISTRY, build_mapping_formatter

def run_pull_with_formatter_id(origin, target, resource, cursor, formatter_id: str):
    info = FORMATTER_REGISTRY[formatter_id]
    mapping = info["mapping"]
    formatter = build_mapping_formatter(mapping)
    return pull(
        resource=resource,
        origin=origin,
        target=target,
        cursor=cursor,
        formatter=formatter,
    )
```

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

* `POST /api/run/pull` with `ResourcePullConfig`
  → run `pull(...)` with JSON config

* `POST /api/run/push` with `ResourcePushConfig`
  → run `push(...)` with JSON config

* `POST /api/formatters/build`
  → store a mapping spec and return a `formatter_id`

### Playground Highlights

`/playground` provides:

* Select origin / target connector
* Select resource (`job`, `profile`)
* Select operation (`pull`, `push`)
* For `pull`:

  * set cursor mode & cursor start
  * configure mapping (origin→target fields)
  * set prefilters (origin WHERE) and postfilters (HAVING)
* For `push`:

  * choose `PushMode.RESOURCES` or `PushMode.EVENTS`
  * paste **Resources JSON** (native objects) for `RESOURCES` mode
  * paste **Events JSON** (`UnifiedJobEvent` / `UnifiedProfileEvent`) for `EVENTS` mode

---

## Core Concepts

### 4.1. Resources & Push Modes

In `core/types.py`:

* `Resource` enum:

  * `Resource.JOB`
  * `Resource.PROFILE`
* `PushMode` enum:

  * `PushMode.RESOURCES`
  * `PushMode.EVENTS`

All pull/push operations are parameterized by `resource`.

---

### 4.2. Connectors & Requests

* **BaseConnector** (`core/connector.py`):

  * Knows its native job & profile models:

    * `job_native_cls`
    * `profile_native_cls`
  * Implements generic resource methods:

    * `read_resources_batch(resource, where, cursor_start, cursor_mode, batch_size)`
    * `write_resources_batch(resource, resources)`
    * `get_cursor_from_native_resource(resource, native, cursor_mode)`
    * `get_resource_id(resource, native)`
    * `parse_resource_event(resource, raw)`
    * `fetch_resources_by_events(resource, events)`

* **Per-warehouse connectors** (`connectors/warehouse_a`, `connectors/warehouse_b`, ...):

  * Implement `BaseConnector` for their system.
  * Use a `Requests` class (e.g. `WarehouseARequests`) to actually call HTTP / DB.

---

### 4.3. Native & Unified Models

* Native models: e.g. `WarehouseAJob`, `WarehouseAProfile`:

  * Pydantic models with connector-specific fields
  * Use `json_schema_extra` to annotate cursor and prefilter metadata
* Unified models (`core/models.py`):

  * `UnifiedJob`, `UnifiedProfile`
  * `UnifiedJobEvent`, `UnifiedProfileEvent`
  * Provide a standard layer to use when `formatter` is `None`.

Connectors implement:

* `to_unified_job(...)` / `from_unified_job(...)`
* `to_unified_profile(...)` / `from_unified_profile(...)`

---

### 4.4. Cursor & Cursor Modes

`Cursor` and `CursorMode` (in `core/types.py`):

```python
class CursorMode(Enum):
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

class Cursor(BaseModel):
    mode: CursorMode
    start: str | None = None
    end: str | None = None
```

Connectors annotate cursor candidates on fields:

```python
from pydantic import BaseModel, Field

class WarehouseAJob(BaseModel):
    job_id: str = Field(
        ...,
        json_schema_extra={"cursor": ["id"]},
    )
    updated_at: datetime = Field(
        ...,
        json_schema_extra={"cursor": ["updated_at"], "prefilter": {"operators": ["gte", "lte"]}},
    )
    created_at: datetime = Field(
        ...,
        json_schema_extra={"cursor": ["created_at"]},
    )
```

Core uses `get_cursor_from_native_resource(...)` to extract the right value based on `CursorMode`.

---

### 4.5. Formatters

In `formatters/base.py`:

* `JobFormatter` / `ProfileFormatter` Protocols
* `build_mapping_formatter(mapping)`:

  * mapping: `[{ "from": "...", "to": "..." }, ...]`
  * returns a callable that builds a `dict` from an origin object
* `FORMATTER_REGISTRY`: global in-memory store for formatter configs (for API/Playground)

If `formatter` is passed to `pull`/`push`:

* It is applied per native resource:

  ```python
  def safe_format_resources(resource, origin, target, formatter, native_resources) -> list[BaseModel]:
      if formatter is not None:
          return [formatter(r) for r in native_resources]
      # else unified path...
  ```

If no formatter is passed:

* `safe_format_resources(...)` uses unified path: origin-native → Unified → target-native.

---

### 4.6. Conditions, Prefilters & UI Schema

* `Condition` / `Operator` (in `core/types.py`) model filter expressions.
* `Prefilter(model_cls, field_name)` (in `core/expressions.py`) builds a **ConditionBuilder**:

  * fully aware of allowed operators from field metadata.
* `export_model_fields(model_cls, only_prefilterable: bool)` (in `core/ui_schema.py`) exposes:

  * field name
  * type
  * `cursor` metadata
  * `prefilter` metadata (operators)
* These are used by:

  * the API (`/api/schema/...`)
  * the Playground UI (to build dropdowns).

---

## Repository Structure

```bash
hrtech-etl/
├─ pyproject.toml
├─ README.md
├─ CONTRIBUTING.md
│
├─ src/
│  └─ hrtech_etl/
│     ├─ __init__.py
│     │
│     ├─ core/
│     │  ├─ __init__.py
│     │  ├─ auth.py          # BaseAuth, ApiKeyAuth, TokenAuth, BearerAuth
│     │  ├─ types.py         # Resource, WarehouseType, Cursor, CursorMode, Condition, Operator, PushMode, PushResult, Formatter, ...
│     │  ├─ models.py        # UnifiedJob, UnifiedProfile, UnifiedJobEvent, UnifiedProfileEvent
│     │  ├─ connector.py     # BaseConnector (generic for jobs/profiles/events)
│     │  ├─ expressions.py   # Prefilter(...) → ConditionBuilder
│     │  ├─ ui_schema.py     # export_model_fields(...) (fields + cursor/prefilter meta)
│     │  ├─ utils.py         # safe_format_resources, apply_postfilters, helper functions
│     │  ├─ registry.py      # ConnectorMeta, register_connector, get_connector_instance
│     │  └─ pipeline.py      # pull(...), push(...), config runners
│     │
│     ├─ connectors/
│     │  ├─ __init__.py
│     │  ├─ warehouse_a/
│     │  │  ├─ __init__.py   # WarehouseAConnector + registration
│     │  │  ├─ models.py     # WarehouseAJob, WarehouseAProfile
│     │  │  ├─ requests.py   # WarehouseARequests (HTTP/DB client)
│     │  │  └─ test.py       # connector tests
│     │  └─ warehouse_b/
│     │     ├─ __init__.py
│     │     ├─ models.py
│     │     ├─ requests.py
│     │     └─ test.py
│     │
│     └─ formatters/
│        ├─ __init__.py
│        ├─ base.py          # FORMATTER_REGISTRY, Protocols, build_mapping_formatter
│        └─ a_to_b.py        # example: WarehouseA → WarehouseB
│
├─ app/
│  ├─ __init__.py
│  ├─ api.py                 # JSON API routes
│  ├─ playground.py          # HTML playground routes
│  └─ main.py                # create_app() with HRTECH_ETL_MODE switch
│
└─ tests/
   └─ test.py                # core tests (pipeline, utils, etc.)
```

---

## Roadmap / Status

> This is a **WIP** (work in progress).

Planned / in-progress:

* [ ] DevOps v1: local integration environment (Poetry)
* [ ] DevOps v2: GitHub workflow + package release bumping through PSR
* [ ] Add real-world ATS/CRM/Jobboard/HCM connectors
* [ ] Improve type coercion for filters (dates, ints, enums)
* [ ] Persist formatters and configs (instead of in-memory `FORMATTER_REGISTRY`)
* [ ] Add worker-style pull pipeline and event hook for push in the playground
* [ ] Add more warehouse templates and examples
* [ ] Integrate with Pydantic AI Gateway
* [ ] Add MCP / Agent integrations
* [ ] Expand test coverage & CI

---

## Contributing

Contributions are very welcome ❤️

* To add a new connector (ATS/CRM/Jobboard/HCM)
* To extend the playground
* To add new filter operators or cursor strategies

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

---
