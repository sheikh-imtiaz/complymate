"""Writes the OpenAPI schema (used to generate packages/api-types).

uv run python scripts/export_openapi.py ../../docs/api/openapi.json
"""

from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("CLOUD_PROVIDER", "local")

from complymate.main import app


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(app.openapi(), fh, indent=2, sort_keys=False)
        fh.write("\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
