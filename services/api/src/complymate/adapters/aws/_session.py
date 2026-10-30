from __future__ import annotations

from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config

_CONFIG = Config(retries={"max_attempts": 5, "mode": "adaptive"}, connect_timeout=5, read_timeout=60)


@lru_cache(maxsize=32)
def client(service: str, region: str, endpoint_url: str | None = None, **kwargs: Any) -> Any:
    return boto3.client(service, region_name=region, endpoint_url=endpoint_url, config=_CONFIG, **kwargs)  # type: ignore[call-overload]
