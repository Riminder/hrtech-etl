import argparse

from hrtech_etl.connectors.hrflow import (
    WarehouseHrflowConnector,
    WarehouseHrflowRequests,
)
from hrtech_etl.connectors.hrflow.auth import HrFlowAuth
from hrtech_etl.core.pipeline import pull
from hrtech_etl.core.types import Cursor, CursorMode, Resource


def build_hrflow_connector(
    api_key: str,
    user_email: str,
    board_key: str,
) -> WarehouseHrflowConnector:
    auth = HrFlowAuth(api_key=api_key, user_email=user_email)

    requests = WarehouseHrflowRequests(
        base_url="https://api.hrflow.ai/v1",
        auth=auth,
        board_key=board_key,
    )

    return WarehouseHrflowConnector(auth=auth, requests=requests)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy jobs from one HrFlow board to another using hrtech-etl."
    )

    parser.add_argument(
        "--api-key",
        required=True,
        help="HrFlow API key",
    )
    parser.add_argument(
        "--user-email",
        required=True,
        help="HrFlow user email",
    )
    parser.add_argument(
        "--origin-provider-key",
        required=True,
        help="Origin HrFlow board key (source of jobs).",
    )
    parser.add_argument(
        "--target-provider-key",
        required=True,
        help="Target HrFlow board key (destination of jobs).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of jobs to transfer (default: no limit).",
    )
    parser.add_argument(
        "--resource",
        choices=["job", "profile"],
        default="job",
        help="Resource type to transfer (job or profile).",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Origin: board A
    origin = build_hrflow_connector(
        api_key=args.api_key,
        user_email="origin-team@hrflow.ai",
        board_key=args.origin_provider_key,
    )

    # Target: board B (possibly another team)
    target = build_hrflow_connector(
        api_key=args.api_key,
        user_email="target-team@hrflow.ai",
        board_key=args.target_provider_key,
    )

    # start from scratch (no cursor yet)
    cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None)

    # --- PULL JOBS: HrFlow.ai -> HrFlow.ai ---
    cursor_jobs = pull(
        resource=Resource.JOB,
        origin=origin,
        target=target,
        cursor=cursor,
        where=None,  # you can add prefilters later
        having=None,  # postfilters later
        formatter=None,  # use unified fallback Hrflow -> Unified -> Hrflow
        batch_size=args.limit,
    )

    print("jobs cursor_start:", cursor_jobs.start)
    print("jobs cursor_end:", cursor_jobs.end)


if __name__ == "__main__":
    main()
