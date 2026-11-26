"""
app/core/monitoring.py
-----------------------
Tracks and logs agent metrics:
 - Tool calls per request
 - Response latency
 - Token usage
 - Estimated cost
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Approximate cost per 1M tokens (USD) — update as needed
COST_TABLE = {
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "default": {"input": 0.10, "output": 0.20},
}


@dataclass
class RequestMetrics:
    session_id: str
    query: str
    tool_calls: list[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = settings.llm_model
    success: bool = False
    error: Optional[str] = None

    @property
    def latency_ms(self) -> float:
        if self.end_time:
            return round((self.end_time - self.start_time) * 1000, 2)
        return 0.0

    @property
    def estimated_cost_usd(self) -> float:
        rates = COST_TABLE.get(self.model, COST_TABLE["default"])
        cost = (self.input_tokens / 1_000_000) * rates["input"]
        cost += (self.output_tokens / 1_000_000) * rates["output"]
        return round(cost, 8)

    def finish(self, success: bool = True, error: str = None):
        self.end_time = time.time()
        self.success = success
        self.error = error

    def add_tool_call(self, tool_name: str):
        self.tool_calls.append(tool_name)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["latency_ms"] = self.latency_ms
        d["estimated_cost_usd"] = self.estimated_cost_usd
        d["total_tokens"] = self.input_tokens + self.output_tokens
        return d


class MetricsLogger:
    """Writes metrics to a JSONL log file for analysis."""

    def __init__(self, log_path: str = None):
        self.log_path = Path(log_path or settings.logs_dir / "metrics.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, metrics: RequestMetrics) -> None:
        data = metrics.to_dict()
        logger.info(
            "request_complete",
            session=metrics.session_id,
            latency_ms=data["latency_ms"],
            tokens=data["total_tokens"],
            tools=metrics.tool_calls,
            cost_usd=data["estimated_cost_usd"],
            success=metrics.success,
        )
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")


# Global metrics logger instance
metrics_logger = MetricsLogger()
