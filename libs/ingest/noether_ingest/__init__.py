"""Schema + synthetic generators for plant tag streams.

Public API:
    - TagSample: pydantic model for a single sensor sample on the wire.
    - Generator: protocol for tag-stream sources.
    - SyntheticTEP: Tennessee-Eastman-style synthetic generator (default for v0.1).
    - TAG_NAMES: ordered list of XMEAS_1..41, XMV_1..11.
"""

from noether_ingest.generator import Generator, SyntheticTEP, TAG_NAMES
from noether_ingest.schema import Quality, TagSample

__all__ = ["Generator", "Quality", "SyntheticTEP", "TAG_NAMES", "TagSample"]
