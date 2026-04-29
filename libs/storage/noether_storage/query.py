"""Read helpers for the tag_samples hypertable.

The query layer is intentionally tiny — three functions cover the three
access patterns the rest of the system uses:

    - latest_value(tag)         → newest row for one tag
    - range_query(tag, t0, t1)  → all rows for one tag in a window
    - pivot(tags, t0, t1)       → wide DataFrame (one column per tag)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import pandas as pd
from noether_ingest import Quality, TagSample
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def latest_value(engine: AsyncEngine, tag: str) -> TagSample | None:
    sql = text("""
        SELECT ts, tag, value, quality
        FROM tag_samples
        WHERE tag = :tag
        ORDER BY ts DESC
        LIMIT 1
        """)
    async with engine.connect() as conn:
        row = (await conn.execute(sql, {"tag": tag})).mappings().first()
    if row is None:
        return None
    return TagSample(
        tag=row["tag"],
        value=row["value"],
        quality=Quality(row["quality"]),
        ts=row["ts"],
    )


async def range_query(
    engine: AsyncEngine,
    tag: str,
    start: datetime,
    end: datetime,
) -> list[TagSample]:
    sql = text("""
        SELECT ts, tag, value, quality
        FROM tag_samples
        WHERE tag = :tag AND ts >= :start AND ts < :end
        ORDER BY ts ASC
        """)
    async with engine.connect() as conn:
        rows = (await conn.execute(sql, {"tag": tag, "start": start, "end": end})).mappings().all()
    return [
        TagSample(tag=r["tag"], value=r["value"], quality=Quality(r["quality"]), ts=r["ts"])
        for r in rows
    ]


async def pivot(
    engine: AsyncEngine,
    tags: Sequence[str],
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    """Wide DataFrame: index=ts, columns=tags, values=value.

    Used by the forecasting service to build feature matrices in one round-trip.
    """
    sql = text("""
        SELECT ts, tag, value
        FROM tag_samples
        WHERE tag = ANY(:tags) AND ts >= :start AND ts < :end
        ORDER BY ts ASC
        """)
    async with engine.connect() as conn:
        rows = (
            (await conn.execute(sql, {"tags": list(tags), "start": start, "end": end}))
            .mappings()
            .all()
        )
    if not rows:
        return pd.DataFrame(columns=list(tags))
    df = pd.DataFrame(rows)
    return df.pivot_table(index="ts", columns="tag", values="value", aggfunc="last").sort_index()
