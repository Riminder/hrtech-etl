# hrtech_etl/core/pipeline.py
from asyncio import events
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

# -------- PULL: JOBS --------

def pull_jobs(
    origin: BaseConnector,
    target: BaseConnector,
    cursor: Cursor,
    where: list[Condition] | None = None,  # prefilters (Prefilter)
    having: list[Condition] | None = None, #  postfilters on native
    formatter: Callable[[BaseModel], BaseModel] | None = None,
    batch_size: int = 1000,
    dry_run: bool = False,
) -> Cursor:
    """
    Incremental pull of jobs: origin → target.

    - `where`: prefilters (pushed down to origin)
    - `having`: postfilters on native origin jobs (core)
    - `formatter`: explicit job formatter; if None, use unified default
    """

    current = cursor.start
    last_cursor : str | None = None

    while True:
        # 1) Read native jobs from origin (with prefilters translated to query)
        native_jobs, current = origin.read_jobs_batch(
            where=where,
            cursor_start=current,
            cursor_mode=cursor.mode,
            batch_size=batch_size,
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
        last_cursor = origin.get_cursor_from_native_job(native_jobs[-1], cursor.mode)

        formatted_jobs = safe_format_jobs(origin, target, formatter, native_jobs)

        if not dry_run:
            target.write_jobs_batch(formatted_jobs)

        if current is None:
            break

    return Cursor(mode=cursor.mode, start=cursor.start, end=last_cursor)

# -------- PULL: PROFILES --------

def pull_profiles(
    origin: BaseConnector,
    target: BaseConnector,
    cursor: Cursor,
    where: list[Condition] | None = None,
    having: list[Condition] | None = None,
    formatter: Callable[[BaseModel], BaseModel] | None = None,
    batch_size: int = 1000,
    dry_run: bool = False,
) -> Cursor:
    """
    Incremental pull of profiles: origin → target.
    """
    current = cursor.start
    last_cursor : str | None = None

    while True:
        native_profiles, current = origin.read_profiles_batch(
            where=where,
            cursor_start=current,
            cursor_mode=cursor.mode,
            batch_size=batch_size,
        )
        if not native_profiles:
            break

        native_profiles = apply_postfilters(native_profiles, having)
        if not native_profiles:
            if current is None:
                break
            last_cursor = current
            continue

        last_cursor = origin.get_cursor_from_native_profile(native_profiles[-1], cursor.mode)

        formatted_profiles = safe_format_profiles(
            origin, target, formatter, native_profiles
        )

        if not dry_run:
            target.write_profiles_batch(formatted_profiles)

        if current is None:
            break

    return Cursor(mode=cursor.mode, start=cursor.start, end=last_cursor)

# -------- PUSH: JOBS --------

def push_jobs(
    origin: BaseConnector,
    target: BaseConnector,
    mode: PushMode,
    events: Iterable[UnifiedJobEvent] | None = None,
    jobs: Iterable[BaseModel] | None = None,
    having: list[Condition] | None = None,
    formatter: JobFormatter | None = None,
    batch_size: int = 1000,
    ignore_missing: bool = True,
    dry_run: bool = False,
) -> PushResult:
    """
    Push jobs from origin → target.

    Two modes:
    - EVENTS: use `events` + origin.fetch_jobs_by_events(...) to get native jobs.
    - RESOURCES: use `jobs` directly as native origin jobs.

    Push mode:
    - `events`: unified JobEvent objects (created by connectors from raw payloads)
    - For each batch of events:
      - fetch native jobs from origin via `fetch_jobs_for_events`
      - apply HAVING conditions on native origin jobs
      - format (or origin-native -> UnifiedJob -> target-native)
      - write to target
    """
    total_events = 0
    total_jobs_fetched = 0
    total_jobs_pushed = 0
    skipped_missing = 0
    skipped_having = 0
    errors: list[str] = []

    if mode == PushMode.EVENTS:
        if events is None:
            raise ValueError("push_jobs(mode='events') requires `events`")
        events = list(events)
        total_events = len(events)

        for i in range(0, total_events, batch_size):
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
                filtered = apply_postfilters([job], having)
                if not filtered:
                    skipped_having += 1
                    continue

                batch_to_push.append(job)

            if not batch_to_push:
                continue

            formatted_jobs = safe_format_jobs(origin, target, formatter, batch_to_push)
            if not dry_run:
                target.write_jobs_batch(formatted_jobs)

            total_jobs_pushed += len(batch_to_push)

    elif mode == PushMode.RESOURCES:
        if jobs is None:
            raise ValueError("push_jobs(mode='resources') requires `jobs`")
        jobs = list(jobs)
        total_jobs_fetched = len(jobs)

        for i in range(0, total_jobs_fetched, batch_size):
            batch_jobs = jobs[i : i + batch_size]
            if  batch_jobs:
                # HAVING: postfilters on native origin job
                filtered_jobs = apply_postfilters(batch_jobs, having)
                skipped_having += len(batch_jobs) - len(filtered_jobs)
                if filtered_jobs:
                    formatted_jobs = safe_format_jobs(
                        origin, target, formatter, filtered_jobs
                    )
                    if not dry_run:
                        target.write_jobs_batch(formatted_jobs)

                    total_jobs_pushed += len(filtered_jobs)

    else:
        raise ValueError(f"Unknown PushMode: {mode}")
    
    return PushResult(
        total_events=total_events,
        total_resources_fetched=total_jobs_fetched,
        total_resources_pushed=total_jobs_pushed,
        skipped_missing=skipped_missing,
        skipped_having=skipped_having,
        errors=errors,
    )


# -------- PUSH: PROFILES --------

def push_profiles(
    origin: BaseConnector,
    target: BaseConnector,
    mode: PushMode,
    events: Iterable[UnifiedProfileEvent] | None = None,
    profiles: Iterable[BaseModel] | None = None,
    having: list[Condition] | None = None,
    formatter: ProfileFormatter | None = None,
    batch_size: int = 1000,
    ignore_missing: bool = True,
    dry_run: bool = False,
) -> PushResult:
    """
    Push profiles from origin → target.
    """
    total_events = 0
    total_profiles_fetched = 0
    total_profiles_pushed = 0
    skipped_missing = 0
    skipped_having = 0
    errors: list[str] = []
    
    if mode == PushMode.EVENTS:
        if events is None:
            raise ValueError("push_profiles(mode='events') requires `events`")
        events = list(events)
        total_events = len(events)

        for i in range(0, total_events, batch_size):
            batch_events = events[i : i + batch_size]

            try:
                native_profiles = origin.fetch_profiles_by_events(batch_events)
            except Exception as exc:
                errors.append(str(exc))
                continue

            total_profiles_fetched += len(native_profiles)

            profiles_by_id = {origin.get_profile_id(p): p for p in native_profiles}

            batch_to_push: list[BaseModel] = []

            for event in batch_events:
                profile = profiles_by_id.get(event.profile_id)
                if profile is None:
                    skipped_missing += 1
                    if not ignore_missing:
                        errors.append(
                            f"Missing profile for event {event.event_id} (profile_id={event.profile_id})"
                        )
                    continue

                filtered = apply_postfilters([profile], having)
                if not filtered:
                    skipped_having += 1
                    continue

                batch_to_push.append(profile)

            if not batch_to_push:
                continue

            formatted_profiles = safe_format_profiles(origin, target, formatter, batch_to_push)
            if not dry_run:
                target.write_profiles_batch(formatted_profiles)

            total_profiles_pushed += len(batch_to_push)
    
    elif mode == PushMode.RESOURCES:
        if profiles is None:
            raise ValueError("push_profiles(mode='resources') requires `profiles`")
        profiles = list(profiles)
        total_profiles_fetched = len(profiles)

        for i in range(0, total_profiles_fetched, batch_size):
            batch_profiles = profiles[i : i + batch_size]
            if  batch_profiles:
                filtered_profiles = apply_postfilters(batch_profiles, having)
                skipped_having += len(batch_profiles) - len(filtered_profiles)
                if filtered_profiles:
                    formatted_profiles = safe_format_profiles(
                        origin, target, formatter, filtered_profiles
                    )
                    if not dry_run:
                        target.write_profiles_batch(formatted_profiles)

                    total_profiles_pushed += len(filtered_profiles)
    else:
        raise ValueError(f"Unknown PushMode: {mode}")
    
    return PushResult(
        total_events=total_events,
        total_resources_fetched=total_profiles_fetched,
        total_resources_pushed=total_profiles_pushed,
        skipped_missing=skipped_missing,
        skipped_having=skipped_having,
        errors=errors,
    )
