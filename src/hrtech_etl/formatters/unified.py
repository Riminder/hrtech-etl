# src/hrtech_etl/formatters/unified.py

from hrtech_etl.core.models import UnifiedJob, UnifiedProfile


def format_job_to_report_row(job: UnifiedJob) -> dict: ...


def format_profile_to_report_row(profile: UnifiedProfile) -> dict: ...
