"""Writes audit batches to local JSONL files, read-only after write (stand-in for Object Lock)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class FileAuditSink:
    def __init__(self, directory: str) -> None:
        self.directory = Path(directory)

    async def write_batch(self, tenant_id: str, batch_key: str, events: list[dict[str, Any]]) -> str:
        path = self.directory / tenant_id / f"{batch_key}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(f"audit batch {batch_key} already archived")
        with path.open("w", encoding="utf-8") as fh:
            for event in events:
                fh.write(json.dumps(event, default=str, sort_keys=True) + "\n")
        os.chmod(path, 0o444)
        return str(path)
