from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from fraud_v2.evaluation.load_benchmark import run_load_benchmark


@dataclass(frozen=True)
class CapacityProfile:
    name: str
    users: int
    score_users: int
    min_load_events_per_second: float
    min_score_decisions_per_second: float
    notes: str


CAPACITY_PROFILES: dict[str, CapacityProfile] = {
    "smoke": CapacityProfile(
        name="smoke",
        users=1_000,
        score_users=50,
        min_load_events_per_second=50.0,
        min_score_decisions_per_second=0.5,
        notes="Fast laptop receipt for normal local verification.",
    ),
    "laptop": CapacityProfile(
        name="laptop",
        users=10_000,
        score_users=200,
        min_load_events_per_second=50.0,
        min_score_decisions_per_second=0.25,
        notes="Heavier Ryzen-class laptop receipt without requiring a GPU.",
    ),
    "stress": CapacityProfile(
        name="stress",
        users=100_000,
        score_users=500,
        min_load_events_per_second=25.0,
        min_score_decisions_per_second=0.1,
        notes="Optional long-running synthetic stress receipt.",
    ),
}


def resolve_capacity_profile(
    name: str,
    *,
    users: int | None = None,
    score_users: int | None = None,
    min_load_events_per_second: float | None = None,
    min_score_decisions_per_second: float | None = None,
) -> CapacityProfile:
    try:
        profile = CAPACITY_PROFILES[name]
    except KeyError as error:
        valid = ", ".join(sorted(CAPACITY_PROFILES))
        raise ValueError(f"unknown capacity profile '{name}'. Valid profiles: {valid}") from error
    return replace(
        profile,
        users=users or profile.users,
        score_users=score_users or profile.score_users,
        min_load_events_per_second=(
            min_load_events_per_second
            if min_load_events_per_second is not None
            else profile.min_load_events_per_second
        ),
        min_score_decisions_per_second=(
            min_score_decisions_per_second
            if min_score_decisions_per_second is not None
            else profile.min_score_decisions_per_second
        ),
    )


def run_capacity_profile(
    *,
    profile: CapacityProfile,
    output_dir: Path,
    seed: int = 20260541,
    overwrite: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / f"{profile.name}-capacity.sqlite"
    benchmark_path = output_dir / f"{profile.name}-load-benchmark.json"
    json_path = output_dir / f"{profile.name}-capacity-report.json"
    html_path = output_dir / f"{profile.name}-capacity-report.html"

    benchmark = run_load_benchmark(
        users=profile.users,
        score_users=profile.score_users,
        db_path=db_path,
        output_path=benchmark_path,
        seed=seed,
        overwrite=overwrite,
    )
    checks = [
        _check_minimum(
            name="load_events_per_second",
            observed=float(benchmark["load_events_per_second"]),
            minimum=profile.min_load_events_per_second,
        ),
        _check_minimum(
            name="score_decisions_per_second",
            observed=float(benchmark["score_decisions_per_second"]),
            minimum=profile.min_score_decisions_per_second,
        ),
    ]
    status = "pass" if all(check["passed"] for check in checks) else "warn"
    report: dict[str, Any] = {
        "schema_version": "capacity-profile-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "profile": asdict(profile),
        "status": status,
        "local_only": True,
        "production_capacity_claim": False,
        "seed": seed,
        "checks": checks,
        "artifacts": {
            "database": str(db_path),
            "benchmark_report": str(benchmark_path),
            "json_report": str(json_path),
            "html_report": str(html_path),
        },
        "benchmark": benchmark,
        "recommendation": _recommendation(status),
    }
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    html_path.write_text(_render_capacity_html(report), encoding="utf-8")
    return report


def _check_minimum(*, name: str, observed: float, minimum: float) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "minimum": minimum,
        "passed": observed >= minimum,
    }


def _recommendation(status: str) -> str:
    if status == "pass":
        return "Local profile met the configured laptop targets. This is still synthetic evidence."
    return (
        "Local profile missed one or more targets. Inspect the bottleneck before increasing "
        "traffic assumptions."
    )


def _render_capacity_html(report: dict[str, Any]) -> str:
    profile = report["profile"]
    benchmark = report["benchmark"]
    status = escape(str(report["status"]))
    status_label = escape(str(report["status"]).upper())
    checks = "\n".join(_render_check(check) for check in report["checks"])
    risk_rows = "\n".join(
        f"<tr><td>{escape(str(tier))}</td><td>{count}</td></tr>"
        for tier, count in sorted(benchmark["risk_tiers"].items())
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Fraud V2 Capacity Profile</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    h1, h2 {{ margin-bottom: 8px; }}
    .status {{ display: inline-block; padding: 4px 8px; border-radius: 6px; background: #e5e7eb; }}
    .pass {{ color: #166534; }}
    .warn {{ color: #9a3412; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0 28px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
    code {{ background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Fraud V2 Capacity Profile</h1>
  <p><span class="status {status}">{status_label}</span></p>
  <p>{escape(str(report["recommendation"]))}</p>
  <h2>Profile</h2>
  <table>
    <tr><th>Name</th><td>{escape(str(profile["name"]))}</td></tr>
    <tr><th>Users</th><td>{profile["users"]}</td></tr>
    <tr><th>Scored Users</th><td>{profile["score_users"]}</td></tr>
    <tr><th>Notes</th><td>{escape(str(profile["notes"]))}</td></tr>
  </table>
  <h2>Throughput</h2>
  <table>
    <tr><th>Metric</th><th>Observed</th><th>Minimum</th><th>Status</th></tr>
    {checks}
  </table>
  <h2>Run Metrics</h2>
  <table>
    <tr><th>Events</th><td>{benchmark["events"]}</td></tr>
    <tr><th>Inserted Events</th><td>{benchmark["inserted_events"]}</td></tr>
    <tr><th>Generation Seconds</th><td>{benchmark["generation_seconds"]}</td></tr>
    <tr><th>Load Seconds</th><td>{benchmark["load_seconds"]}</td></tr>
    <tr><th>Score Seconds</th><td>{benchmark["score_seconds"]}</td></tr>
  </table>
  <h2>Risk Tiers</h2>
  <table>
    <tr><th>Tier</th><th>Count</th></tr>
    {risk_rows}
  </table>
  <p>Local-only synthetic receipt. This is not a production capacity claim.</p>
</body>
</html>
"""


def _render_check(check: dict[str, Any]) -> str:
    status = "pass" if check["passed"] else "warn"
    return (
        "<tr>"
        f"<td><code>{escape(str(check['name']))}</code></td>"
        f"<td>{check['observed']}</td>"
        f"<td>{check['minimum']}</td>"
        f'<td class="{status}">{status.upper()}</td>'
        "</tr>"
    )
