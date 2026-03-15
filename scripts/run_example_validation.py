from __future__ import annotations

import argparse

from bi_validator.db.session import SessionLocal
from bi_validator.schemas.run import RunCreateRequest
from bi_validator.services.dashboard_validation import DashboardValidationCoordinator


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an example BI dashboard validation job.")
    parser.add_argument("--dashboard-url", required=True, help="Dashboard URL to validate.")
    parser.add_argument("--dashboard-name", default="Sales Overview")
    parser.add_argument("--platform", default="generic")
    parser.add_argument(
        "--prompt",
        default="Validate the Sales dashboard and verify that revenue drilldowns match totals.",
    )
    parser.add_argument("--rules-path", default="config/rules/default_rules.yaml")
    parser.add_argument("--dashboard-config-path", default="config/dashboards/sample_sales.yaml")
    parser.add_argument("--headless", action="store_true", default=False)
    args = parser.parse_args()

    request = RunCreateRequest(
        dashboard_name=args.dashboard_name,
        dashboard_url=args.dashboard_url,
        platform=args.platform,
        prompt=args.prompt,
        rules_path=args.rules_path,
        dashboard_config_path=args.dashboard_config_path,
        headless=args.headless,
    )

    db = SessionLocal()
    try:
        coordinator = DashboardValidationCoordinator()
        run = coordinator.create_run(db, request)
        run = coordinator.execute_run(db, run.id, request)
        print(f"Run ID: {run.id}")
        print(f"Status: {run.status.value}")
        print(f"Reports: {run.summary.get('reports', {})}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
