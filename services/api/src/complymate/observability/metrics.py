"""Business and ops metrics. Emitted as CloudWatch Embedded Metric Format logs on AWS (no SDK needed);
Azure Monitor picks the same JSON up via a log-based metric. Alarms are defined in Terraform."""

from __future__ import annotations

import json
import sys
import time
from typing import Any

NAMESPACE = "ComplyMate"


def emit(metric: str, value: float, unit: str = "Count", **dimensions: str) -> None:
    payload: dict[str, Any] = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": NAMESPACE,
                    "Dimensions": [list(dimensions.keys())] if dimensions else [[]],
                    "Metrics": [{"Name": metric, "Unit": unit}],
                }
            ],
        },
        metric: value,
        **dimensions,
    }
    sys.stdout.write(json.dumps(payload) + "\n")


def llm_usage(tenant_id: str, purpose: str, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
    emit("LLMCostUSD", cost_usd, "None", Purpose=purpose)
    emit("LLMTokens", input_tokens + output_tokens, "Count", Purpose=purpose)


def audit_chain_break(tenant_id: str) -> None:
    emit("AuditChainBreak", 1, "Count")


def screening_job_failed(job: str) -> None:
    emit("ScreeningJobFailed", 1, "Count", Job=job)


def security_event(category: str) -> None:
    emit("SecurityEvent", 1, "Count", Category=category)
