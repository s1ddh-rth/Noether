"""Consume `plant.tags`, validate, COPY into Timescale, commit offsets."""

from __future__ import annotations

import asyncio
import contextlib
import time

import asyncpg
from aiokafka import AIOKafkaConsumer
from noether_ingest import TagSample
from noether_storage import StorageSettings, dsn
from pydantic import ValidationError
from structlog.stdlib import BoundLogger

from noether_svc_storage.config import ConsumerSettings


async def _flush(
    pool: asyncpg.Pool,
    rows: list[tuple],
    log: BoundLogger,
) -> None:
    if not rows:
        return
    started = time.monotonic()
    async with pool.acquire() as conn:
        await conn.copy_records_to_table(
            "tag_samples",
            records=rows,
            columns=["ts", "tag", "value", "quality"],
        )
    log.info(
        "storage.flushed",
        rows=len(rows),
        latency_ms=int((time.monotonic() - started) * 1000),
    )


async def run(
    consumer_settings: ConsumerSettings,
    storage_settings: StorageSettings,
    log: BoundLogger,
) -> None:
    pool = await asyncpg.create_pool(dsn(storage_settings), min_size=1, max_size=4)
    if pool is None:
        raise RuntimeError("failed to create asyncpg pool")

    consumer = AIOKafkaConsumer(
        consumer_settings.kafka_topic_plant_tags,
        bootstrap_servers=consumer_settings.kafka_bootstrap,
        group_id=consumer_settings.kafka_group_id,
        # Manual commit only after a successful flush — at-least-once.
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    log.info(
        "storage_consumer.started",
        bootstrap=consumer_settings.kafka_bootstrap,
        topic=consumer_settings.kafka_topic_plant_tags,
    )

    buffer: list[tuple] = []
    last_flush = time.monotonic()
    invalid = 0
    try:
        while True:
            wait_ms = max(
                10,
                consumer_settings.batch_max_wait_ms
                - int((time.monotonic() - last_flush) * 1000),
            )
            batch = await consumer.getmany(timeout_ms=wait_ms, max_records=consumer_settings.batch_size)
            for _tp, msgs in batch.items():
                for msg in msgs:
                    try:
                        sample = TagSample.from_kafka_payload(msg.value)
                    except (ValidationError, ValueError) as exc:
                        invalid += 1
                        log.warning(
                            "storage_consumer.invalid_message",
                            err=str(exc),
                            offset=msg.offset,
                        )
                        continue
                    buffer.append((sample.ts, sample.tag, sample.value, sample.quality.value))

            should_flush = (
                len(buffer) >= consumer_settings.batch_size
                or (buffer and (time.monotonic() - last_flush) * 1000 >= consumer_settings.batch_max_wait_ms)
            )
            if should_flush:
                await _flush(pool, buffer, log)
                buffer.clear()
                await consumer.commit()
                last_flush = time.monotonic()
    finally:
        with contextlib.suppress(Exception):
            await consumer.stop()
        await pool.close()
        log.info("storage_consumer.stopped", invalid=invalid, residual=len(buffer))
        # Best-effort flush of anything left in the buffer.
        if buffer:
            try:
                pool2 = await asyncpg.create_pool(dsn(storage_settings), min_size=1, max_size=1)
                if pool2 is not None:
                    await _flush(pool2, buffer, log)
                    await pool2.close()
            except (asyncpg.PostgresError, OSError) as exc:
                log.error("storage_consumer.shutdown_flush_failed", err=str(exc))


# Quiet "unused import" lint when asyncio is referenced indirectly via getmany.
_ = asyncio
