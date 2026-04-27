"""SQL DDL for the tag_samples hypertable.

We keep DDL as raw SQL (rather than ORM models) because Timescale-specific
operations like `create_hypertable`, compression, and retention policies
aren't expressible in vanilla SQLAlchemy.
"""

from __future__ import annotations

CREATE_EXTENSION = "CREATE EXTENSION IF NOT EXISTS timescaledb;"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tag_samples (
    ts       TIMESTAMPTZ NOT NULL,
    tag      TEXT        NOT NULL,
    value    DOUBLE PRECISION NOT NULL,
    quality  TEXT        NOT NULL DEFAULT 'good'
);
"""

CREATE_HYPERTABLE = """
SELECT create_hypertable(
    'tag_samples',
    'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_tag_samples_tag_ts
    ON tag_samples (tag, ts DESC);
"""

ENABLE_COMPRESSION = """
ALTER TABLE tag_samples SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'tag',
    timescaledb.compress_orderby = 'ts DESC'
);
"""

ADD_COMPRESSION_POLICY = """
SELECT add_compression_policy('tag_samples', INTERVAL '7 days', if_not_exists => TRUE);
"""


def add_retention_policy_sql(retention_days: int) -> str:
    return (
        "SELECT add_retention_policy("
        f"'tag_samples', INTERVAL '{retention_days} days', if_not_exists => TRUE);"
    )


ALL_DDL_NO_RETENTION = [
    CREATE_EXTENSION,
    CREATE_TABLE,
    CREATE_HYPERTABLE,
    CREATE_INDEX,
    ENABLE_COMPRESSION,
    ADD_COMPRESSION_POLICY,
]
