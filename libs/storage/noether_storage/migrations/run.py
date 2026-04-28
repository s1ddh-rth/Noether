"""Idempotent migration runner.

We use raw SQL (see noether_storage.schema) rather than Alembic for v0.1
because the schema is one table + a few Timescale policies. Alembic can
land later as a follow-up change once we have multi-table evolution.
"""

from __future__ import annotations

import asyncio
import sys

import asyncpg

from noether_storage.config import StorageSettings, dsn
from noether_storage.schema import (
    ALL_DDL_NO_RETENTION,
    add_anomalies_retention_policy_sql,
    add_retention_policy_sql,
)


async def _run(settings: StorageSettings) -> None:
    conn = await asyncpg.connect(dsn(settings))
    try:
        for stmt in ALL_DDL_NO_RETENTION:
            await conn.execute(stmt)
        await conn.execute(add_retention_policy_sql(settings.retention_days))
        await conn.execute(add_anomalies_retention_policy_sql(settings.retention_days))
    finally:
        await conn.close()


def main() -> None:
    settings = StorageSettings()
    asyncio.run(_run(settings))
    print(
        f"migrations applied to {settings.host}:{settings.port}/{settings.database}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
