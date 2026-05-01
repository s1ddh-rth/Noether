"""DDL string sanity checks. Real round-trip lives in integration tests."""

from noether_storage.schema import (
    ALL_DDL_NO_RETENTION,
    CREATE_ANOMALIES_TABLE,
    CREATE_CHAT_SESSIONS_TABLE,
    CREATE_HYPERTABLE,
    CREATE_TABLE,
    add_anomalies_retention_policy_sql,
    add_retention_policy_sql,
)


def test_schema_includes_required_tables() -> None:
    joined = "\n".join(ALL_DDL_NO_RETENTION)
    assert "tag_samples" in joined
    assert "tag_anomalies" in joined
    assert "chat_sessions" in joined
    assert "create_hypertable" in joined.lower() or "create_hypertable" in joined


def test_chat_sessions_table_has_required_columns() -> None:
    cols = ["session_id", "created_at", "last_active_at"]
    for c in cols:
        assert c in CREATE_CHAT_SESSIONS_TABLE
    assert "PRIMARY KEY" in CREATE_CHAT_SESSIONS_TABLE


def test_tag_samples_has_required_columns() -> None:
    assert "ts" in CREATE_TABLE
    assert "tag" in CREATE_TABLE
    assert "value" in CREATE_TABLE
    assert "quality" in CREATE_TABLE


def test_tag_anomalies_has_required_columns() -> None:
    cols = ["alert_id", "score", "iforest_score", "mahalanobis_score", "ewma_score", "alert"]
    for c in cols:
        assert c in CREATE_ANOMALIES_TABLE


def test_retention_policies_render_with_days() -> None:
    sql = add_retention_policy_sql(30)
    assert "INTERVAL '30 days'" in sql
    sql = add_anomalies_retention_policy_sql(7)
    assert "INTERVAL '7 days'" in sql
    assert "tag_anomalies" in sql


def test_hypertable_uses_one_day_chunks() -> None:
    assert "INTERVAL '1 day'" in CREATE_HYPERTABLE
