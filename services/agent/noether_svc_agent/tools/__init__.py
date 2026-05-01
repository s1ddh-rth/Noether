"""Sub-agent tools.

Every tool conforms to the `AgentTool` Protocol — `name`, `description`,
and an `async run(input) -> ToolResult` method. The synthesiser node
only sees `ToolResult` objects regardless of which tool produced them,
so adding a new tool only requires implementing the Protocol.

Lands in two waves to keep dep churn small:

- This commit: core types + the no-deps tool (`VizTool`) + HTTP-based
  tools (`ForecastTool`, `AnomalyTool`) that wrap services/inference.
- Next commit: data-access tools (`SqlTool`, `RagTool`,
  `MultimodalRagTool`) that pull in `noether-storage` and `noether-rag`.
"""

from noether_svc_agent.tools.anomaly import AnomalyTool, AnomalyToolInput
from noether_svc_agent.tools.forecast import ForecastTagPoint, ForecastTool, ForecastToolInput
from noether_svc_agent.tools.types import AgentTool, ToolResult
from noether_svc_agent.tools.viz import VizSeries, VizSeriesPoint, VizTool, VizToolInput

__all__ = [
    "AgentTool",
    "AnomalyTool",
    "AnomalyToolInput",
    "ForecastTagPoint",
    "ForecastTool",
    "ForecastToolInput",
    "ToolResult",
    "VizSeries",
    "VizSeriesPoint",
    "VizTool",
    "VizToolInput",
]
