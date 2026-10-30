"""Structured JSON logs (structlog) with request_id, tenant_id, user_id. PII filter runs last."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

from complymate.observability.pii_filter import pii_processor

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def _context(_logger: Any, _method: str, event_dict: Any) -> Any:
    for key, var in (("request_id", request_id_var), ("tenant_id", tenant_id_var), ("user_id", user_id_var)):
        if (value := var.get()) is not None:
            event_dict.setdefault(key, value)
    try:
        from opentelemetry import trace

        span = trace.get_current_span().get_span_context()
        if span.is_valid:
            event_dict["trace_id"] = format(span.trace_id, "032x")
    except Exception:  # noqa: S110 - tracing is optional
        pass
    return event_dict


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    for noisy in ("botocore", "urllib3", "httpx", "azure"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    renderer = structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _context,
            structlog.processors.format_exc_info,
            pii_processor,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        cache_logger_on_first_use=True,
    )
