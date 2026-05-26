#!/usr/bin/env python3
"""Parse common local data files without calling an LLM."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self.text: list[str] = []
        self._active_link: dict[str, str] | None = None
        self._active_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attr_map = {key: value or "" for key, value in attrs}
            if attr_map.get("href"):
                self._active_link = {"href": attr_map["href"], "text": ""}
                self._active_link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._active_link is not None:
            self._active_link["text"] = " ".join(self._active_link_text)
            self.links.append(self._active_link)
            self._active_link = None
            self._active_link_text = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self.text.append(cleaned)
            if self._active_link is not None:
                self._active_link_text.append(cleaned)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_json(path: Path) -> Any:
    return json.loads(read_text(path))


def parse_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        return list(csv.DictReader(handle, dialect=dialect))


def parse_html(path: Path) -> dict[str, Any]:
    parser = TextHTMLParser()
    parser.feed(read_text(path))
    return {
        "text": "\n".join(parser.text),
        "links": parser.links,
    }


def summarize_text(text: str) -> dict[str, Any]:
    words = re.findall(r"\b\w+\b", text.lower(), flags=re.UNICODE)
    lines = [line for line in text.splitlines() if line.strip()]
    return {
        "chars": len(text),
        "lines": len(lines),
        "words": len(words),
        "top_words": Counter(word for word in words if len(word) > 3).most_common(20),
    }


def flatten_json(value: Any, prefix: str = "") -> dict[str, Any]:
    rows: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            rows.update(flatten_json(item, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        rows[prefix or "items"] = f"list[{len(value)}]"
        for index, item in enumerate(value[:20]):
            rows.update(flatten_json(item, f"{prefix}[{index}]"))
    else:
        rows[prefix or "value"] = value
    return rows


def detect_format(path: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix in {".html", ".htm"}:
        return "html"
    return "text"


def build_output(path: Path, fmt: str) -> dict[str, Any]:
    if fmt == "json":
        data = parse_json(path)
        return {"format": "json", "summary": flatten_json(data), "data": data}
    if fmt == "csv":
        rows = parse_csv(path)
        fields = list(rows[0].keys()) if rows else []
        return {"format": "csv", "rows": len(rows), "fields": fields, "data": rows}
    if fmt == "html":
        data = parse_html(path)
        return {"format": "html", "summary": summarize_text(data["text"]), **data}
    text = read_text(path)
    return {"format": "text", "summary": summarize_text(text), "text": text}


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse JSON, CSV, HTML, or text into structured output.")
    parser.add_argument("file", help="file to parse")
    parser.add_argument("--format", choices=["auto", "json", "csv", "html", "text"], default="auto")
    parser.add_argument("--summary-only", action="store_true", help="omit full parsed content")
    parser.add_argument("--output", "-o", help="write JSON result to this file")
    args = parser.parse_args()

    path = Path(args.file).expanduser().resolve()
    fmt = detect_format(path, args.format)
    result = build_output(path, fmt)
    if args.summary_only:
        result = {key: result[key] for key in result if key in {"format", "summary", "rows", "fields"}}

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).expanduser().write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
