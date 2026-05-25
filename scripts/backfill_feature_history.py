#!/usr/bin/env python3
"""CLI: backfill persisted sentiment/breadth feature history."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from flask_services.feature_history_backfill import feature_history_backfill_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill feature history store")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--news-limit", type=int, default=300)
    parser.add_argument("--no-sentiment", action="store_true")
    parser.add_argument("--no-breadth", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    result = feature_history_backfill_service.run(
        days=args.days,
        news_limit=args.news_limit,
        fill_sentiment=not args.no_sentiment,
        fill_breadth=not args.no_breadth,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
