"""Regulator pack: one ZIP with program, registers, audit trail and training records, plus a manifest."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime


def build_zip(files: dict[str, bytes], firm_name: str, generated_by: str) -> bytes:
    manifest = {
        "firm": firm_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": generated_by,
        "files": [
            {"name": n, "sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d)} for n, d in sorted(files.items())
        ],
        "notice": "Prepared from ComplyMate records. General information, not legal advice.",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in sorted(files.items()):
            zf.writestr(name, data)
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
    return buf.getvalue()
