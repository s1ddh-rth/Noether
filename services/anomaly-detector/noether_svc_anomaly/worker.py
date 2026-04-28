"""The streaming AD worker: fit baseline, then score sliding windows."""

from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
from noether_anomaly import (
    AnomalyEnsemble,
    EWMADetector,
    IsolationForestDetector,
    MahalanobisDetector,
)
from noether_storage import StorageSettings, async_dsn, dsn, pivot
from sqlalchemy.ext.asyncio import create_async_engine
from structlog.stdlib import BoundLogger

from noether_svc_anomaly.config import AnomalySettings


async def _wait_for_warmup(
    engine, settings: AnomalySettings, log: BoundLogger
) -> datetime:
    """Block until tag_samples has `warmup_minutes` of recent data."""
    while True:
        async with engine.connect() as conn:
            from sqlalchemy import text

            row = (
                await conn.execute(
                    text(
                        "SELECT min(ts) AS min_ts, max(ts) AS max_ts, count(*) AS n FROM tag_samples"
                    )
                )
            ).mappings().first()
        if row and row["max_ts"] is not None:
            span_min = (row["max_ts"] - row["min_ts"]).total_seconds() / 60.0
            if span_min >= settings.warmup_minutes:
                log.info("anomaly.warmup_satisfied", span_min=round(span_min, 1))
                return row["max_ts"]
        await asyncio.sleep(5)


async def _fit_baseline(
    engine, settings: AnomalySettings, end_ts: datetime, log: BoundLogger
) -> AnomalyEnsemble:
    start_ts = end_ts - timedelta(minutes=settings.baseline_minutes)
    log.info(
        "anomaly.fit_baseline.start",
        start=start_ts.isoformat(),
        end=end_ts.isoformat(),
        tags=len(settings.tag_list),
    )
    df = await pivot(engine, settings.tag_list, start_ts, end_ts)
    if df.empty:
        raise RuntimeError("baseline window is empty — ingest may not be running")
    df = df[settings.tag_list].dropna()
    if len(df) < 100:
        raise RuntimeError(f"baseline too short after dropna: {len(df)} rows")
    ensemble = AnomalyEnsemble(
        detectors=[
            IsolationForestDetector(),
            MahalanobisDetector(),
            EWMADetector(),
        ],
        threshold=settings.threshold,
    )
    started = time.monotonic()
    ensemble.fit(df)
    settings.model_dir.mkdir(parents=True, exist_ok=True)
    ensemble.save(settings.ensemble_path)
    log.info(
        "anomaly.fit_baseline.ok",
        rows=len(df),
        latency_ms=int((time.monotonic() - started) * 1000),
        ensemble_path=str(settings.ensemble_path),
    )
    return ensemble


async def _score_loop(
    pool: asyncpg.Pool,
    engine,
    ensemble: AnomalyEnsemble,
    settings: AnomalySettings,
    log: BoundLogger,
) -> None:
    period_s = settings.stride_seconds
    deadline = time.monotonic()
    while True:
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(seconds=settings.window_seconds)
        df = await pivot(engine, settings.tag_list, start, end)
        if df.empty:
            log.warning("anomaly.empty_window", start=start.isoformat(), end=end.isoformat())
        else:
            df = df[settings.tag_list].dropna()
            if len(df) >= 5:
                started = time.monotonic()
                result = ensemble.score(df)
                latency_ms = int((time.monotonic() - started) * 1000)
                alert_id = uuid.uuid4()
                await pool.execute(
                    """
                    INSERT INTO tag_anomalies
                        (ts, alert_id, window_start, window_end, score,
                         iforest_score, mahalanobis_score, ewma_score, alert, tags)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    end,
                    alert_id,
                    start,
                    end,
                    result.score,
                    result.detectors.iforest,
                    result.detectors.mahalanobis,
                    result.detectors.ewma,
                    result.alert,
                    settings.tag_list,
                )
                log.info(
                    "anomaly.scored",
                    alert_id=str(alert_id),
                    score=round(result.score, 4),
                    alert=result.alert,
                    rows=len(df),
                    latency_ms=latency_ms,
                )

        deadline += period_s
        sleep_for = deadline - time.monotonic()
        if sleep_for > 0:
            await asyncio.sleep(sleep_for)
        else:
            log.warning("anomaly.behind_schedule", behind_s=-sleep_for)
            deadline = time.monotonic()


async def run(
    settings: AnomalySettings,
    storage_settings: StorageSettings,
    log: BoundLogger,
) -> None:
    engine = create_async_engine(async_dsn(storage_settings))
    pool = await asyncpg.create_pool(dsn(storage_settings), min_size=1, max_size=2)
    if pool is None:
        raise RuntimeError("failed to create asyncpg pool")
    try:
        last_ts = await _wait_for_warmup(engine, settings, log)
        ensemble = await _fit_baseline(engine, settings, last_ts, log)
        await _score_loop(pool, engine, ensemble, settings, log)
    finally:
        with contextlib.suppress(Exception):
            await engine.dispose()
        with contextlib.suppress(Exception):
            await pool.close()
