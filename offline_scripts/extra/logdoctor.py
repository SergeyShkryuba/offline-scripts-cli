#!/usr/bin/env python3
"""Analyze log files: group similar lines, find top errors, build timelines."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


NORMALIZE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"), "{TIMESTAMP}"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?\b"), "{IPV4}"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "{UUID}"),
    (re.compile(r"\b0x[0-9a-f]+\b", re.I), "{HEX}"),
    (re.compile(r"\b\d+\.\d+\b"), "{FLOAT}"),
    (re.compile(r"\b\d+\b"), "{INT}"),
    (re.compile(r"'[^']*'"), "'{STR}'"),
    (re.compile(r'"[^"]*"'), '"{STR}"'),
]

SEVERITY_PATTERN = re.compile(r"\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|TRACE)\b", re.I)


def normalize(line: str) -> str:
    result = line
    for pattern, repl in NORMALIZE_PATTERNS:
        result = pattern.sub(repl, result)
    return result


def detect_severity(line: str) -> str:
    match = SEVERITY_PATTERN.search(line)
    return match.group(1).upper() if match else "UNKNOWN"


def parse_log(path: Path) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        print(f"error reading file: {error}", file=sys.stderr)
        sys.exit(2)
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        lines.append({
            "number": number,
            "raw": raw,
            "norm": normalize(raw),
            "severity": detect_severity(raw),
        })
    return lines


def analyze(lines: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    pattern_counter: Counter[str] = Counter()
    severity_counter: Counter[str] = Counter()
    examples: dict[str, dict] = {}

    for line in lines:
        pattern_counter[line["norm"]] += 1
        severity_counter[line["severity"]] += 1
        if line["norm"] not in examples:
            examples[line["norm"]] = line

    top_patterns = pattern_counter.most_common(top_n)
    groups = []
    for pattern, count in top_patterns:
        ex = examples[pattern]
        groups.append({
            "pattern": pattern,
            "count": count,
            "severity": ex["severity"],
            "example_line": ex["number"],
            "example_raw": ex["raw"][:200],
        })

    return {
        "total_lines": len(lines),
        "unique_patterns": len(pattern_counter),
        "severity": dict(severity_counter.most_common()),
        "top_patterns": groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze and summarize log files.")
    parser.add_argument("file", help="log file")
    parser.add_argument("--top", "-n", type=int, default=10, help="top N patterns")
    parser.add_argument("--severity", "-s", help="filter by severity (ERROR, WARN, etc.)")
    parser.add_argument("--pattern", "-p", help="filter lines matching regex")
    args = parser.parse_args()

    path = Path(args.file).expanduser().resolve()
    lines = parse_log(path)

    if args.severity:
        target = args.severity.upper()
        lines = [ln for ln in lines if ln["severity"] == target]
    if args.pattern:
        try:
            regex = re.compile(args.pattern)
        except re.error as error:
            print(f"invalid regex: {error}", file=sys.stderr)
            return 2
        lines = [ln for ln in lines if regex.search(ln["raw"])]

    result = analyze(lines, args.top)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
