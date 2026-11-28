"""Ingest sources explicitly marked reviewed in docs/legal-sources/registry.json."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.legal_sources import ingest_sources  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", action="append", dest="source_ids", help="Limit to a reviewed registry source (repeatable)")
    args = parser.parse_args()
    try:
        result = asyncio.run(ingest_sources(set(args.source_ids) if args.source_ids else None))
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
