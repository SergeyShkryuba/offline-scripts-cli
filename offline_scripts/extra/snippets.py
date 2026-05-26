#!/usr/bin/env python3
"""Local snippet manager for reusable code and command templates."""

from __future__ import annotations

import argparse
import json
import sys
from json import JSONDecodeError
from pathlib import Path
from typing import Any

SNIPPETS_DIR = Path.home() / ".snippets"
INDEX_FILE = SNIPPETS_DIR / "index.json"


def ensure_storage() -> None:
    SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("{}", encoding="utf-8")


def load_index() -> dict[str, Any]:
    ensure_storage()
    try:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except JSONDecodeError as error:
        print(f"error: invalid snippet index {INDEX_FILE}: {error}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict):
        print(f"error: snippet index must contain a JSON object: {INDEX_FILE}", file=sys.stderr)
        sys.exit(2)
    return data


def save_index(index: dict[str, Any]) -> None:
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_add(args: argparse.Namespace) -> int:
    index = load_index()
    key = args.key.lower().strip()
    if not key:
        print("error: key cannot be empty", file=sys.stderr)
        return 2
    content = args.content
    if args.file:
        content = Path(args.file).expanduser().read_text(encoding="utf-8")
    if not content:
        print("error: content cannot be empty", file=sys.stderr)
        return 2
    tags = [t.strip().lower() for t in args.tags.split(",") if t.strip()] if args.tags else []
    index[key] = {
        "content": content,
        "tags": tags,
        "description": args.description or "",
    }
    save_index(index)
    print(f"saved snippet: {key}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    index = load_index()
    key = args.key.lower().strip()
    snippet = index.get(key)
    if not snippet:
        print(f"snippet not found: {key}", file=sys.stderr)
        return 1
    print(snippet["content"])
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    index = load_index()
    if not index:
        print("no snippets yet")
        return 0
    tag_filter = args.tag.lower().strip() if args.tag else None
    items: list[tuple[str, dict]] = []
    for key, data in sorted(index.items()):
        if tag_filter and tag_filter not in data.get("tags", []):
            continue
        items.append((key, data))
    if not items:
        print(f"no snippets with tag: {tag_filter}")
        return 0
    for key, data in items:
        tags = ", ".join(data.get("tags", []))
        desc = data.get("description", "")
        preview = data["content"].replace("\n", " ")[:60]
        extra = f" [{tags}]" if tags else ""
        extra += f" — {desc}" if desc else ""
        print(f"- {key}{extra}")
        print(f"  {preview}...")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    index = load_index()
    query = args.query.lower()
    matches: list[tuple[str, dict]] = []
    for key, data in index.items():
        haystack = f"{key} {data.get('description', '')} {data['content']}".lower()
        if query in haystack:
            matches.append((key, data))
    if not matches:
        print(f"no matches for: {query}")
        return 0
    for key, data in sorted(matches):
        desc = data.get("description", "")
        print(f"- {key}" + (f" — {desc}" if desc else ""))
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    index = load_index()
    key = args.key.lower().strip()
    if key not in index:
        print(f"snippet not found: {key}", file=sys.stderr)
        return 1
    del index[key]
    save_index(index)
    print(f"removed: {key}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage reusable snippets.")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add a snippet")
    add.add_argument("key")
    add.add_argument("content", nargs="?", default="")
    add.add_argument("--file", "-f", help="read content from file")
    add.add_argument("--tags", "-t", default="", help="comma-separated tags")
    add.add_argument("--description", "-d", default="")
    add.set_defaults(func=cmd_add)

    get = sub.add_parser("get", help="print a snippet")
    get.add_argument("key")
    get.set_defaults(func=cmd_get)

    list_ = sub.add_parser("list", help="list snippets")
    list_.add_argument("--tag", help="filter by tag")
    list_.set_defaults(func=cmd_list)

    search = sub.add_parser("search", help="search snippets")
    search.add_argument("query")
    search.set_defaults(func=cmd_search)

    remove = sub.add_parser("remove", help="remove a snippet")
    remove.add_argument("key")
    remove.set_defaults(func=cmd_remove)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
