# hrtech_etl/core/pipeline.py
from typing import Any, Callable, List, Optional, Iterable
from pydantic import BaseModel

from .connector import BaseConnector
from .registry import get_connector_instance
from .types import (
    Cursor,
    CursorMode,
    Condition,
    PushMode,
    PushResult,
)
from .models import UnifiedJobEvent, UnifiedProfileEvent
from .utils import safe_format_jobs, safe_format_profiles, apply_postfilters
from hrtech_etl.formatters.base import JobFormatter, ProfileFormatter

from importlib import import_module



class JobPullConfig(BaseModel):
    origin: str              # connector name, e.g. "warehouse_a"
    target: str              # connector name, e.g. "warehouse_b"
    cursor: Cursor
    where: List[Condition] = []  # prefilters
    having: List[Condition] = [] # NEW: postfilters on native
    formatter: Optional[str] = None    # dotted path, e.g. "hrtech_etl.formatters.a_to_b.format_job"
    formatter_id: Optional[str] | None = None
    batch_size: int = 1000
    dry_run: bool = False


def _load_callable(path: str) -> Callable[..., Any]:
    module_name, _, attr = path.rpartition(".")
    module = import_module(module_name)
    return getattr(module, attr)


def run_job_pull_from_config(cfg: JobPullConfig) -> Any:
    origin: BaseConnector = get_connector_instance(cfg.origin)
    target: BaseConnector = get_connector_instance(cfg.target)
    formatter = _load_callable(cfg.formatter) if cfg.formatter else None

    return pull_jobs(
        origin=origin,
        target=target,
        cursor=cfg.cursor,
        where=cfg.where,
        having=cfg.having,
        formatter=formatter,
        batch_size=cfg.batch_size,
        dry_run=cfg.dry_run,
    )


def safe_formatter_job(
    origin: BaseConnector,
    target: BaseConnector,
    formatter: JobFormatter | None,
    native_job: List[BaseModel],
) -> List[BaseModel]:
    if formatter is None:
        unified_job = origin.to_unified_job(native_job)
        return target.from_unified_job(unified_job)
    else:
        return formatter(native_job)


def pull_jobs(
    origin: BaseConnector,
    target: BaseConnector,
    cursor: Cursor,
    where: list[Condition] | None = None,  # prefilters (Prefilter)
    having: list[Condition] | None = None, # NEW: postfilters on native
    formatter: Callable[[BaseModel], BaseModel] | None = None,
    batch_size: int = 1000,
    dry_run: bool = False,
) -> Any | None:
    """
    Returns the last cursor value (datetime or id),
    so you can store it and resume later.
    """

    current = Cursor.start
    cursor_end = None

    while True:
        # 1) Read native jobs from origin (with prefilters translated to query)
        native_jobs, current = origin.read_jobs_batch(
            cursor_start=current,
            batch_size=batch_size,
            where=where,
            cursor_mode=cursor.mode,
        )
        if not native_jobs:
            break
        
        # 2) Apply postfilters IN MEMORY on native objects
        native_jobs = apply_postfilters(native_jobs, having)
        if not native_jobs:
            # no jobs left after postfiltering, but we still advance cursor
            if current is None:
                break
            last_cursor = current
            continue

        # 3) Compute last_cursor from the *last* native job in this batch
        last_cursor = origin.get_cursor_value(native_jobs[-1], cursor.mode)

        formatted = [safe_formatter_job(origin, target, formatter, j) for j in native_jobs]

        if not dry_run:
            target.write_jobs_batch(formatted)

        if current is None:
            break

    return Cursor(mode=cursor.mode, start=cursor.start, end=last_cursor)


def push_jobs(
    origin: BaseConnector,
    target: BaseConnector,
    events: Iterable[UnifiedJobEvent],
    having: list[Condition] | None = None,
    formatter: JobFormatter | None = None,
    batch_size: int = 1000,
    ignore_missing: bool = True,
    dry_run: bool = False,
) -> PushResult:
    """
    Push mode:
    - `events`: unified JobEvent objects (created by connectors from raw payloads)
    - For each batch of events:
      - fetch native jobs from origin via `fetch_jobs_for_events`
      - apply HAVING conditions on native origin jobs
      - format (or origin-native -> UnifiedJob -> target-native)
      - write to target
    """
    events = list(events)
    total_events = len(events)

    total_jobs_fetched = 0
    total_jobs_pushed = 0
    skipped_missing = 0
    skipped_having = 0
    errors: list[str] = []

    for i in range(0, len(events), batch_size):
        batch_events = events[i : i + batch_size]

        try:
            native_jobs = origin.fetch_jobs_by_events(batch_events)
        except Exception as exc:
            errors.append(str(exc))
            continue

        total_jobs_fetched += len(native_jobs)

        # Map jobs by id using connector's get_job_id()
        jobs_by_id = {origin.get_job_id(j): j for j in native_jobs}

        batch_to_push: list[BaseModel] = []

        for event in batch_events:
            job = jobs_by_id.get(event.job_id)
            if job is None:
                skipped_missing += 1
                if not ignore_missing:
                    errors.append(
                        f"Missing job for event {event.event_id} (job_id={event.job_id})"
                    )
                continue

            # HAVING: postfilters on native origin job
            if having:
                filtered = apply_postfilters([job], having)
                if not filtered:
                    skipped_having += 1
                    continue

            batch_to_push.append(job)

        if not batch_to_push:
            continue

        formatted_jobs = [safe_formatter_job(
            origin, target, formatter, j
        ) for j in batch_to_push]

        if not dry_run:
            target.write_jobs_batch(formatted_jobs)

        total_jobs_pushed += len(batch_to_push)

    return PushResult(
        total_events=total_events,
        total_jobs_fetched=total_jobs_fetched,
        total_jobs_pushed=total_jobs_pushed,
        skipped_missing=skipped_missing,
        skipped_having=skipped_having,
        errors=errors,
    )
