# Contributing to **hrtech-etl**

Thank you for contributing to **hrtech-etl** 💙
This document focuses on **how to extend the library**, especially **how to create a new connector correctly**, following the patterns established in `warehouse_a`.

If you're unfamiliar with the project structure or core concepts, please read **`README.md` first**, which explains the architecture, connectors, pipeline, and playground.

---

# Table of Contents

1. [Development Setup](#development-setup)
2. [Running API & Playground](#running-api--playground)
3. [Coding Guidelines](#coding-guidelines)
4. [🚀 Adding a New Connector (Most Important)](#🚀-adding-a-new-connector-most-important)

   * 4.1. Folder structure
   * 4.2. Step 1 — Define models with correct metadata
   * 4.3. Step 2 — Implement actions (low-level client)
   * 4.4. Step 3 — Implement connector logic
   * 4.5. Step 4 — Register connector
   * 4.6. Step 5 — Write tests (including API tests)
   * 4.7. Checklist: **What NOT to forget**
5. [Extending the Playground or API](#extending-the-playground-or-api)
6. [Submitting a Pull Request](#submitting-a-pull-request)
7. [Ideas / Questions](#ideas--questions)

---

# Development Setup

```bash
git clone https://github.com/<your-org>/hrtech-etl.git
cd hrtech-etl
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
pytest
```

---

# Running API & Playground

The FastAPI server can run in 3 modes:

```bash
HRTECH_ETL_MODE=api        uvicorn app.main:app --reload
HRTECH_ETL_MODE=playground uvicorn app.main:app --reload
HRTECH_ETL_MODE=both       uvicorn app.main:app --reload
```

Open the playground at:

```
http://127.0.0.1:8000/playground
```

---

# Coding Guidelines

* Use **Pydantic models** everywhere.
* Do **not** implement filtering manually; use the metadata-driven builders in `core.utils`.
* Keep per-warehouse logic encapsulated under `connectors/<name>/`.
* Do **not** modify core logic unless it's truly generic.
* Always add tests for:

  * connector logic
  * pull/push workflow
  * FastAPI integration

---

# 🚀 Adding a New Connector (Most Important)

A connector consists of **four files**:

```
src/hrtech_etl/connectors/<your_system>/
  ├─ models.py
  ├─ actions.py
  ├─ __init__.py  (the connector implementation)
  └─ test.py
```

The best reference is **warehouse_a**.

---

## 4.1. Folder structure

Create:

```
src/hrtech_etl/connectors/my_system/
  ├── models.py
  ├── actions.py
  ├── __init__.py
  └── test.py
```

---

## 4.2. Step 1 — Define native models (`models.py`)

Each connector must define:

* a **Job model**
* a **Profile model**
* (optional) event models if your warehouse emits events

Most important: **add metadata in `json_schema_extra`**.

### Required metadata

| Purpose             | Metadata key       | Example                                          |
| ------------------- | ------------------ | ------------------------------------------------ |
| Cursor-based paging | `"cursor"`         | `"cursor": ["updated_at"]`                       |
| Prefilters (WHERE)  | `"prefilter"`      | `"prefilter": {"operators": ["eq", "contains"]}` |
| Search binding      | `"search_binding"` | full text search rules                           |
| IN binding          | `"in_binding"`     | control translation of IN operator               |
| Default behavior    | fallback fields    | `payload`                                        |

### Example (minimal)

```python
class MySystemJob(BaseModel):
    job_id: str = Field(
        ..., 
        json_schema_extra={
            "cursor": ["id"],
            "prefilter": {"operators": ["eq", "in"]},
        }
    )

    title: str = Field(
        ..., 
        json_schema_extra={
            "prefilter": {"operators": ["contains"]},
            "search_binding": {
                "search_field": "keywords",
                "field_join": "AND",
                "value_join": "OR",
            },
        }
    )

    updated_at: datetime = Field(
        ..., 
        json_schema_extra={
            "cursor": ["updated_at"],
            "prefilter": {"operators": ["gte", "lte"]},
        }
    )

    payload: dict = {}
```

👉 **If cursor/prefilter/search metadata is missing, the Playground and API will break.**

---

## 4.3. Step 2 — Implement warehouse client (`actions.py`)

This file contains **low-level HTTP / DB calls**.

You must expose:

```python
fetch_jobs(...)
upsert_jobs(...)
fetch_jobs_by_ids(...)

fetch_profiles(...)
upsert_profiles(...)
fetch_profiles_by_ids(...)
```

You SHOULD call:

```python
from hrtech_etl.core.utils import build_connector_params
```

Example:

```python
params = build_connector_params(
    resource_cls=MySystemJob,
    where=where,
    cursor=cursor,
    sort_by_unified="updated_at",
    sort_param_name="order",
)
params["limit"] = batch_size
```

⚠ **Never manually build WHERE/cursor fields** → the metadata drives everything.

---

## 4.4. Step 3 — Implement the connector (`__init__.py`)

Your connector must:

### Required methods

| Method                  | Purpose                      |
| ----------------------- | ---------------------------- |
| `to_unified_job`        | Native → UnifiedJob          |
| `from_unified_job`      | UnifiedJob → Native          |
| `to_unified_profile`    | Native → UnifiedProfile      |
| `from_unified_profile`  | UnifiedProfile → Native      |
| `read_jobs_batch`       | Calls actions.fetch_jobs     |
| `read_profiles_batch`   | Calls actions.fetch_profiles |
| `write_resources_batch` | Write native resources       |
| `get_resource_id`       | Extract job/profile ID       |
| `parse_resource_event`  | Optional event support       |

### Required class attributes

```python
job_native_cls = MySystemJob
profile_native_cls = MySystemProfile
sort_param_name = "order"  # depends on API
```

---

## 4.5. Step 4 — Register the connector

At the bottom of `__init__.py`:

```python
register_connector(
    ConnectorMeta(
        name="my_system",
        label="My System",
        warehouse_type=WarehouseType.ATS,
        job_model="hrtech_etl.connectors.my_system.models.MySystemJob",
        profile_model="hrtech_etl.connectors.my_system.models.MySystemProfile",
        connector_path="hrtech_etl.connectors.my_system.MySystemConnector",
    ),
    factory=_build_default_connector,
)
```

Without registration:

* API cannot list your connector
* Playground cannot load your schema
* Pull/Push via CLI fail

---

## 4.6. Step 5 — Write tests (`test.py`)

Tests MUST include:

### ✔ DummyActions unit tests

```python
class DummyActions(MySystemActions):
    def fetch_jobs(...):
        return [MySystemJob(...)] , None
```

Test:

* connector construction
* cursor extraction
* pull pipeline end-to-end

### ✔ FastAPI API tests

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

resp = client.post("/api/run/pull", json={...})
assert resp.status_code == 200
```

This ensures:

* registration works
* schema export works
* run pull works

---

## 4.7. **Checklist: What NOT to forget**

### In `models.py`

* [ ] `"cursor"` metadata for **every** supported cursor mode
* [ ] `"prefilter"` with **operators list**
* [ ] `"search_binding"` when applicable
* [ ] `"in_binding"` if IN semantics needed
* [ ] Profile model also implemented
* [ ] Event models if warehouse supports events

### In `actions.py`

* [ ] Use `build_connector_params`
* [ ] Implement all fetch/upsert methods
* [ ] Return `(list_of_models, next_cursor)`

### In `__init__.py`

* [ ] Correct `job_native_cls` and `profile_native_cls`
* [ ] Implement unified conversions
* [ ] Implement read/write batch
* [ ] Register connector with `register_connector`

### In `test.py`

* [ ] DummyActions
* [ ] pull test
* [ ] API test (`/api/run/pull`)
* [ ] mapping test (optional)

If any of these are missing, the connector will **not behave correctly** in the pipeline nor in the UI.

---

# Extending the Playground or API

If you add features requiring UI:

* Update `app/api.py` for new endpoints or schema outputs
* Update `app/playground.py` to read new form fields
* Update `templates/playground.html` accordingly

**Do not duplicate core logic in the API or UI.**

---

# Submitting a Pull Request

1. Fork
2. Create feature branch
3. Add connector or improvement
4. Run tests
5. Provide:

   * Description of change
   * Example config or run scenario
   * Screenshots if UI change

---

# Ideas / Questions

Open an issue describing:

* New connector you want to add
* Missing cursor/filter operators
* API or UI improvements
* Suggestions for new ETL capabilities

We actively answer and help design contributions.

---

**Thank you for helping expand hrtech-etl — the universal ETL layer for HRTech. 💙**
