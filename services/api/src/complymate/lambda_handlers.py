"""AWS Lambda entrypoints for the single container image (selected per function via image_config.command).

* api_handler    — API Gateway HTTP API → FastAPI (Mangum)
* worker_handler — SQS batches, EventBridge Scheduler messages and Step Functions tasks → workers.entry
* ws_handler     — API Gateway WebSocket chat streaming
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mangum import Mangum

from complymate.main import app

_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)
_api = Mangum(app, lifespan="off", api_gateway_base_path="/")


def api_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return _api(event, context)


def worker_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    from complymate.workers.entry import dispatch

    if "Records" in event:  # SQS: report partial failures so only failed messages are retried
        failures = []
        for record in event["Records"]:
            try:
                body = json.loads(record["body"])
                _loop.run_until_complete(dispatch(body["task"], body.get("payload", {})))
            except Exception:
                import structlog

                structlog.get_logger(__name__).exception("worker.record_failed", message_id=record.get("messageId"))
                failures.append({"itemIdentifier": record["messageId"]})
        return {"batchItemFailures": failures}
    # Direct invoke: Step Functions task or manual `aws lambda invoke` ({"task": "migrate"})
    result = _loop.run_until_complete(dispatch(event["task"], event.get("payload", {})))
    return result if isinstance(result, dict) else {"ok": True, "result": result}


def ws_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    from complymate.api.ws.chat import handle_apigw_event

    return _loop.run_until_complete(handle_apigw_event(event))
