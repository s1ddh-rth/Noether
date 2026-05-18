"""One-shot drift run.

Scheduling is external by design: a Helm CronJob in prod, a tiny
`while/sleep` loop in the compose `cron` profile. Keeping the job
one-shot means the same entrypoint is testable and cron-native.
"""

from __future__ import annotations

import asyncio
import sys

import structlog

from noether_drift.runner import compute_drift


def main() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    summary = asyncio.run(compute_drift())
    # Exit non-zero on insufficient data so a CronJob surfaces it as a
    # failed run rather than silently "succeeding" with no verdict.
    if summary.status != "ok":
        print(f"drift run status={summary.status}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
