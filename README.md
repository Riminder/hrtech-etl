# HrTech ETL (wip)
Opensource ETL framework for HRTech data (jobs & profiles) across ATS, CRM, Jobboard, and HCM systems.

## Example

```python
from hrtech_etl.core.types import CursorMode
from hrtech_etl.core.pipeline import pull_jobs
from hrtech_etl.core.auth import ApiKeyAuth, BearerAuth
from hrtech_etl.connectors.warehouse_a import WarehouseAConnector, WarehouseAActions
from hrtech_etl.core.pipeline import pull_jobs, pull_profiles
from hrtech_etl.core.types import CursorMode
from hrtech_etl.core.auth import ApiKeyAuth, BearerAuth

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
    cursor_mode=CursorMode.UPDATED_AT,  # or CREATED_AT / ID
    format_fn=a_to_b.format_profile,    # standard profile formatter
    batch_size=5000,
)

# You can store last_job_cursor / last_profile_cursor to resume on next run.

```

Custom format function
```python
from hrtech_etl.formatters.base import JobFormatter, ProfileFormatter
from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob, WarehouseAProfile
from hrtech_etl.connectors.warehouse_b.models import WarehouseBJob, WarehouseBProfile

def format_job(job: WarehouseAJob) -> WarehouseBJob: ...
def format_profile(profile: WarehouseAProfile) -> WarehouseBProfile: ...
```

Where conditions for pre-filerting

```python
from hrtech_etl.core.expressions import field
where_jobs = [
    field(WarehouseAJob, "job_title").contains("engineer"),
    field(WarehouseAJob, "created_on").gte(my_date),
]
```

Run Pipeline using JSON
```python
from hrtech_etl.core.pipeline import pull_jobs
from hrtech_etl.core.types import CursorMode
from hrtech_etl.formatters.base import build_mapping_formatter
from app.main import FORMATTER_REGISTRY


def run_job_pull_with_formatter_id(origin, target, formatter_id: str):
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

Launch the app with API or PLAYGROUND Modes

```python
HRTECH_ETL_MODE=api uvicorn app.main:app --reload
HRTECH_ETL_MODE=playground uvicorn app.main:app --reload
HRTECH_ETL_MODE=both uvicorn app.main:app --reload



## Repository Structure

```bash
hrtech-etl/
├─ pyproject.toml
├─ README.md
│
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
│     │  ├─ types.py         # WarehouseType, CursorMode, FilterFn
│     │  ├─ models.py        # UnifiedJob, UnifiedProfile (Pydantic)
│     │  ├─ connector.py     # BaseConnector (jobs + profiles, Pydantic-native)
│     │  ├─ actions.py       # BaseActions (wraps low-level client, tracks _request_count)
│     │  ├─ utils.py         # single_request, get_cursor_value, shared helpers
│     │  └─ pipeline.py      # pull_jobs / pull_profiles (cursor_mode chosen here)
│     │
│     ├─ connectors/
│     │  ├─ __init__.py      # optional: re-export connectors
│     │  │
│     │  ├─ warehouse_a/
│     │  │  ├─ __init__.py   # WarehouseAConnector
│     │  │  ├─ models.py     # WarehouseAJob, WarehouseAProfile (Pydantic, cursor metadata)
│     │  │  ├─ actions.py    # WarehouseAActions
│     │  │  └─ test.py       # tests for this connector
│     │  │
│     │  └─ warehouse_b/
│     │     ├─ __init__.py   # WarehouseBConnector
│     │     ├─ models.py     # WarehouseBJob, WarehouseBProfile
│     │     ├─ actions.py    # WarehouseBActions
│     │     └─ test.py       # tests for this connector
│     │
│     └─ formatters/
│        ├─ __init__.py      # registry helpers, type aliases
│        ├─ base.py          # Protocols / type hints for format functions
│        ├─ a_to_b.py        # example: WarehouseA -> WarehouseB standard formatters
│        └─ unified.py       # example: generic unified<->unified / unified->report format
│
└─ tests/
   └─ test.py                # core framework tests (pipeline, utils, unified models, etc.)
```