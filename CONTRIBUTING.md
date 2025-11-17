Here’s `CONTRIBUTION.md` with a Table of Contents added at the top:

````markdown
# Contributing to hrtech-etl

First of all, thank you for your interest in contributing to **hrtech-etl** 💙  
This document explains how the project is structured, how to set up your dev environment, and how to add or extend connectors, pipelines, and the UI.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Repository Layout](#2-repository-layout)
3. [Development Setup](#3-development-setup)  
   3.1. [Clone & install](#31-clone--install-in-editable-mode)  
   3.2. [Run tests](#32-run-tests)
4. [Running the API & Playground](#4-running-the-api--playground)
5. [Coding Guidelines](#5-coding-guidelines)  
   5.1. [Style](#51-style)  
   5.2. [Pull vs Push](#52-pull-vs-push)
6. [Adding a New Connector](#6-adding-a-new-connector)
7. [Extending the Playground / API](#7-extending-the-playground--api)
8. [Submitting a Pull Request](#8-submitting-a-pull-request)
9. [Questions / Ideas](#9-questions--ideas)

---

## 1. Overview

`hrtech-etl` is an open-source ETL framework for **HRTech data** (jobs & profiles) across ATS, CRM, Jobboard, and HCM systems.

High-level concepts:

- **Resources**: `Resource.JOB` and `Resource.PROFILE`
- **Connectors**: one `BaseConnector` per external system (e.g. Lever, Greenhouse, Salesforce…)
- **Pipelines**:
  - `pull(...)` → incremental sync from origin → target using cursors, prefilters (`WHERE`) and postfilters (`HAVING`)
  - `push(...)` → push using either:
    - resources (native objects)
    - or events (`UnifiedJobEvent` / `UnifiedProfileEvent`)
- **Formatters**:
  - Either custom Python formatters
  - Or mapping-based formatters built from a field mapping (origin → target)
- **API & Playground**:
  - REST API (FastAPI) under `app/api.py`
  - HTML playground under `app/playground.py` + `app/templates/playground.html`

---

## 2. Repository Layout

The relevant parts of the repo:

```bash
hrtech-etl/
├─ pyproject.toml
├─ README.md
├─ CONTRIBUTION.md
│
├─ src/
│  └─ hrtech_etl/
│     ├─ __init__.py
│     │
│     ├─ core/
│     │  ├─ __init__.py
│     │  ├─ auth.py          # BaseAuth, ApiKeyAuth, TokenAuth, BearerAuth
│     │  ├─ types.py         # Resource, WarehouseType, Cursor, CursorMode, Condition, PushMode, PushResult, Formatter, ...
│     │  ├─ models.py        # UnifiedJob, UnifiedProfile, UnifiedJobEvent, UnifiedProfileEvent (Pydantic)
│     │  ├─ connector.py     # BaseConnector (generic for jobs & profiles & events)
│     │  ├─ expressions.py   # Prefilter(...) → ConditionBuilder for prefilters
│     │  ├─ ui_schema.py     # export_model_fields(...) for UI (fields, cursor & prefilter metadata)
│     │  ├─ utils.py         # safe_format_resources, apply_postfilters, helper functions
│     │  ├─ registry.py      # register_connector(...) / get_connector_instance(...)
│     │  └─ pipeline.py      # pull(...), push(...), config-driven runners
│     │
│     ├─ connectors/
│     │  ├─ __init__.py
│     │  ├─ warehouse_a/
│     │  │  ├─ __init__.py   # WarehouseAConnector + registration
│     │  │  ├─ models.py     # WarehouseAJob, WarehouseAProfile (Pydantic, cursor & prefilter metadata)
│     │  │  ├─ requests.py   # low-level client / HTTP/DB access for warehouse A
│     │  │  └─ test.py       # connector-specific tests
│     │  └─ warehouse_b/
│     │     ├─ __init__.py
│     │     ├─ models.py
│     │     ├─ requests.py
│     │     └─ test.py
│     │
│     └─ formatters/
│        ├─ __init__.py
│        ├─ base.py          # formatter Protocols, FORMATTER_REGISTRY, build_mapping_formatter(...)
│        └─ a_to_b.py        # example formatters WarehouseA → WarehouseB
│
├─ app/
│  ├─ main.py                # builds FastAPI app (API + Playground modes)
│  ├─ api.py                 # REST API routes
│  ├─ playground.py          # HTML playground routes
│  └─ templates/
│     └─ playground.html     # UI to play with pull/push/mappings/filters
│
└─ tests/
   └─ test.py                # core tests (pipeline, utils, etc.)
````

---

## 3. Development Setup

### 3.1. Clone & install in editable mode

```bash
git clone https://github.com/your-org/hrtech-etl.git
cd hrtech-etl

# vanilla pip
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

If you’re using Poetry / uv, adapt accordingly (but the project is designed to work fine with plain `pip`).

### 3.2. Run tests

```bash
pytest
```

This should run:

* core tests in `tests/test.py`
* connector tests in `src/hrtech_etl/connectors/**/test.py` (if wired into `pytest` via discovery)

---

## 4. Running the API & Playground

The FastAPI app can expose:

* **API** (JSON only)
* **Playground** (HTML-only)
* Or **both**

This is controlled via the `HRTECH_ETL_MODE` environment variable, and composed in `app/main.py` (one FastAPI `app`):

```bash
# API only
HRTECH_ETL_MODE=api uvicorn app.main:app --reload

# Playground only (HTML UI)
HRTECH_ETL_MODE=playground uvicorn app.main:app --reload

# Both API + Playground
HRTECH_ETL_MODE=both uvicorn app.main:app --reload
```

Typical dev workflow:

1. Start the server with `HRTECH_ETL_MODE=both`.
2. Open the playground at `http://127.0.0.1:8000/playground`.
3. Build mappings, prefilters/postfilters, and run pull/push interactively.
4. Use `/api/...` endpoints to script more advanced scenarios.

---

## 5. Coding Guidelines

### 5.1. Style

* Prefer **type hints** everywhere.
* Use **Pydantic models** for:

  * Connector-native objects (`WarehouseXJob`, `WarehouseXProfile`)
  * Unified objects (`UnifiedJob`, `UnifiedProfile`, `UnifiedJobEvent`, `UnifiedProfileEvent`)
  * Config objects (`ResourcePullConfig`, `ResourcePushConfig`, etc.)
* Keep connector-specific logic inside the respective `connectors/<name>/` folder.
* Keep generic logic in `core/` and `formatters/`.

You can optionally run formatters/linters:

```bash
ruff check .
black .
```

(Or whatever you add to `pyproject.toml`.)

### 5.2. Pull vs Push

* **Pull** should always go through:

  ```python
  from hrtech_etl.core.types import Resource, Cursor, CursorMode
  from hrtech_etl.core.pipeline import pull

  cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None)
  cursor = pull(
      resource=Resource.JOB,
      origin=origin_connector,
      target=target_connector,
      cursor=cursor,
      where=prefilters or None,
      having=postfilters or None,
      formatter=formatter or None,
  )
  ```

* **Push** should always go through:

  ```python
  from hrtech_etl.core.types import Resource, PushMode
  from hrtech_etl.core.pipeline import push

  result = push(
      resource=Resource.JOB,
      origin=origin_connector,
      target=target_connector,
      mode=PushMode.RESOURCES,  # or PushMode.EVENTS
      events=events_or_none,
      resources=resources_or_none,
      having=postfilters or None,
      formatter=formatter or None,
  )
  ```

Formatting logic:

* If `formatter` is **not** provided:

  * Use unified path (native → unified → native).
* If `formatter` **is** provided:

  * Accepts either:

    * A Pydantic model (native or unified)
    * Or a `dict` (e.g. from `build_mapping_formatter`), which is wrapped into the target native model.

---

## 6. Adding a New Connector

The most common contribution: **add a new connector** for a new ATS/CRM/Jobboard/HCM.

Example: `src/hrtech_etl/connectors/my_system/`

1. **Create folder**:

   ```bash
   src/hrtech_etl/connectors/my_system/
   ├─ __init__.py
   ├─ models.py
   ├─ requests.py
   └─ test.py
   ```

2. **Define models** (`models.py`)

   * Pydantic models for jobs & profiles, with cursor & prefilter metadata.
   * Example:

   ```python
   from datetime import datetime
   from typing import Any, Dict
   from pydantic import BaseModel, Field

   class MySystemJob(BaseModel):
       job_id: str = Field(
           ...,
           json_schema_extra={"cursor": ["id"], "prefilter": {"operators": ["eq", "in"]}},
       )
       title: str = Field(
           ...,
           json_schema_extra={"prefilter": {"operators": ["eq", "contains"]}},
       )
       updated_at: datetime = Field(
           ...,
           json_schema_extra={"cursor": ["updated_at"], "prefilter": {"operators": ["gte", "lte"]}},
       )
       created_at: datetime = Field(
           ...,
           json_schema_extra={"cursor": ["created_at"]},
       )
       payload: Dict[str, Any] = {}
   ```

   Same pattern for `MySystemProfile`.

3. **Implement low-level client / requests** (`requests.py`)

   * Handle HTTP / DB calls.
   * Provide methods like `read_jobs_batch`, `read_profiles_batch`, possibly `fetch_jobs_by_events`, `fetch_profiles_by_events`.

4. **Implement connector** (`__init__.py`)

   * Subclass `BaseConnector`.

   * Implement:

     * `to_unified_job`, `from_unified_job`
     * `to_unified_profile`, `from_unified_profile`
     * `read_resources_batch(...)`
     * `write_resources_batch(...)`
     * `get_cursor_from_native_resource(...)`
     * `get_resource_id(...)`
     * `parse_resource_event(...)` / `fetch_resources_by_events(...)` if events are supported.

   * Register it via `register_connector(...)` in `core/registry.py`:

   ```python
   from hrtech_etl.core.registry import register_connector, ConnectorMeta
   from hrtech_etl.core.types import WarehouseType

   register_connector(
       ConnectorMeta(
           name="my_system",
           label="My System",
           warehouse_type=WarehouseType.ATS,
           job_model="hrtech_etl.connectors.my_system.models.MySystemJob",
           profile_model="hrtech_etl.connectors.my_system.models.MySystemProfile",
       )
   )
   ```

5. **Add tests** (`test.py`)

   * Test:

     * cursor extraction
     * reading batches
     * unified conversions
     * basic pull/push scenario using a fake client.

---

## 7. Extending the Playground / API

If you want to add new UI capabilities (e.g., new operators, new push modes, extra metadata):

* **API layer**:

  * Update `app/api.py`:

    * Add/extend endpoints for new operations (`run/...`, `formatters/...`).
* **Playground**:

  * Update `app/playground.py` to parse new form fields or support new modes.
  * Update `app/templates/playground.html` to render the UI controls (inputs, dropdowns, textareas).

Keep the playground “dumb”: it should call the core primitives (`pull`, `push`, etc.) and not reimplement business logic.

---

## 8. Submitting a Pull Request

1. **Fork** the repository.

2. Create a feature branch:

   ```bash
   git checkout -b feature/my-awesome-change
   ```

3. Make your changes.

4. Run tests:

   ```bash
   pytest
   ```

5. Commit with a clear message:

   ```bash
   git commit -am "Add connector for MySystem ATS"
   ```

6. Push your branch and open a Pull Request with:

   * A short summary of the change.
   * Any relevant screenshots (for playground changes).
   * How to test it (commands, sample config, sample JSON for playground).

---

## 9. Questions / Ideas

If you’re not sure where a change belongs (core vs connector vs API vs playground), or you want to propose a bigger refactor (new resource types, new cursor strategies, etc.), open an **issue** first and describe:

* The problem you’re solving.
* The HRTech use case (ATS/CRM/Jobboard/HCM).
* A rough sketch of the API / UX you have in mind.

We’ll discuss and converge on a design before you invest too much coding time.

Thanks again for contributing to **hrtech-etl** 🙌

```
```
