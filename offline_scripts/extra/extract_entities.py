#!/usr/bin/env python3
"""Extract emails, URLs, IPs, UUIDs, dates and phone numbers from text files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "url": re.compile(r"https?://[^\s\"'<>]+"),
    "ipv4": re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
    "ipv6": re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"),
    "uuid": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    "date_iso": re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?\b"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"),
}


def extract(text: str) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for name, pattern in PATTERNS.items():
        matches = sorted(set(pattern.findall(text)))
        if matches:
            results[name] = matches
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract structured entities from text.")
    parser.add_argument("file", nargs="?", help="text file (default: stdin)")
    parser.add_argument("--type", "-t", action="append", choices=list(PATTERNS), help="extract only specific types")
    parser.add_argument("--output", "-o", choices=["json", "plain"], default="json", help="output format")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file).expanduser().resolve()
        if not path.is_file():
            print(f"error: file not found: {path}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        text = sys.stdin.read()

    results = extract(text)
    if args.type:
        results = {k: v for k, v in results.items() if k in args.type}

    if args.output == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for entity_type, values in results.items():
            print(f"[{entity_type}]")
            for value in values:
                print(f"  {value}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
