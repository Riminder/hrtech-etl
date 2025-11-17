# src/hrtech_etl/formatters/a_to_b.py

from typing import Any

from hrtech_etl.connectors.warehouse_a.models import WarehouseAJob, WarehouseAProfile
from hrtech_etl.connectors.warehouse_b.models import WarehouseBJob, WarehouseBProfile


# Job formatter: A -> B
def format_job(a_job: WarehouseAJob) -> WarehouseBJob: ...


# Profile formatter: A -> B
def format_profile(a_profile: WarehouseAProfile) -> WarehouseBProfile: ...
