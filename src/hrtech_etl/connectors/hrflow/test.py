import argparse

from hrtech_etl.connectors.hrflow import (
    WarehouseHrflowActions,
    WarehouseHrflowConnector,
)
from hrtech_etl.core.auth import ApiKeyAuth
from hrtech_etl.core.pipeline import pull
from hrtech_etl.core.types import Cursor, CursorMode, Resource


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
        "--batch-size",
        type=int,
        default=10,
        help="Maximum number of jobs to transfer (default: 10).",
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

    origin = WarehouseHrflowConnector(
        auth=ApiKeyAuth("X-API-Key", args.api_key),
        actions=WarehouseHrflowActions(
            base_url="https://api.hrflow.ai/v1",
            api_key=args.api_key,
            api_user_email=args.user_email,
            provider_key=args.origin_provider_key,
        ),
    )

    target = WarehouseHrflowConnector(
        auth=ApiKeyAuth("X-API-Key", args.api_key),
        actions=WarehouseHrflowActions(
            base_url="https://api.hrflow.ai/v1",
            api_key=args.api_key,
            api_user_email=args.user_email,
            provider_key=args.target_provider_key,
        ),
    )

    # start from scratch (no cursor yet)
    cursor = Cursor(mode=CursorMode.UPDATED_AT, start=None, sort_by="asc")

    # --- PULL JOBS: HrFlow.ai -> HrFlow.ai ---
    cursor_jobs = pull(
        resource=Resource.JOB,
        origin=origin,
        target=target,
        cursor=cursor,
        batch_size=args.batch_size,
    )

    print("jobs cursor_start:", cursor_jobs.start)
    print("jobs cursor_end:", cursor_jobs.end)

    # # --- PULL PROFILES: HrFlow.ai -> HrFlow.ai ---
    # cursor_profiles = pull(
    #     resource=Resource.PROFILE,
    #     origin=origin,
    #     target=target,
    #     cursor=cursor,
    #     batch_size=5000,
    # )
    # print("profiles cursor_start:", cursor_profiles.start)
    # print("profiles cursor_end:", cursor_profiles.end)


if __name__ == "__main__":
    main()
