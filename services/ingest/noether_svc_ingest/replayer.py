"""Tag replayer: drives a Generator at a fixed rate and publishes to Kafka."""

from __future__ import annotations

import asyncio
import contextlib
import time
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer
from noether_ingest import Generator, SyntheticTEP, TagSample
from structlog.stdlib import BoundLogger

from noether_svc_ingest.config import IngestSettings


async def run(settings: IngestSettings, log: BoundLogger) -> None:
    gen: Generator = SyntheticTEP(
        seed=settings.sim_seed,
        fault_profile=settings.fault_profile,
        fault_start_s=settings.fault_start_s,
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap,
        # Compression dropped for v0.1 — lz4/snappy bindings would be a
        # separate dep proposal. 50 tags * 1 Hz fits comfortably uncompressed.
        linger_ms=20,
        acks="all",
        enable_idempotence=True,
    )
    await producer.start()
    log.info(
        "ingest.started",
        bootstrap=settings.kafka_bootstrap,
        topic=settings.kafka_topic_plant_tags,
        replay_hz=settings.replay_hz,
        fault_profile=settings.fault_profile,
    )

    period_s = 1.0 / settings.replay_hz
    deadline = time.monotonic()
    published = 0
    try:
        while True:
            ts = datetime.now(tz=timezone.utc)
            sample_dict = gen.step()

            for tag, value in sample_dict.items():
                try:
                    sample = TagSample(tag=tag, value=value, ts=ts)
                except ValueError as exc:
                    log.warning("ingest.invalid_sample", tag=tag, value=value, err=str(exc))
                    continue

                await producer.send_and_wait(
                    settings.kafka_topic_plant_tags,
                    value=sample.to_kafka_payload(),
                    key=tag.encode("utf-8"),
                )
                published += 1

            if published % (len(sample_dict) * 60) == 0:
                log.info("ingest.progress", published=published)

            deadline += period_s
            sleep_for = deadline - time.monotonic()
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            else:
                # Fell behind — log and reset deadline rather than spiraling.
                log.warning("ingest.behind_schedule", behind_s=-sleep_for)
                deadline = time.monotonic()
    finally:
        with contextlib.suppress(Exception):
            await producer.stop()
        log.info("ingest.stopped", published=published)
