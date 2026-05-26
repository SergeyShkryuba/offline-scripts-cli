#!/usr/bin/env python3
"""Offline file processing helper with safe defaults."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


def iter_files(root: Path, pattern: str, recursive: bool) -> list[Path]:
    globber = root.rglob if recursive else root.glob
    return sorted(path for path in globber(pattern) if path.is_file())


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cmd_inventory(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    files = iter_files(root, args.pattern, args.recursive)
    rows = []
    for path in files:
        stat = path.stat()
        rows.append(
            {
                "path": str(path.relative_to(root)),
                "bytes": stat.st_size,
                "extension": path.suffix.lower() or "(none)",
                "modified": int(stat.st_mtime),
            }
        )
    print(json.dumps({"root": str(root), "files": rows}, ensure_ascii=False, indent=2))
    return 0


def cmd_organize(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    target = Path(args.target).expanduser().resolve() if args.target else root
    files = iter_files(root, args.pattern, recursive=False)
    for path in files:
        folder = path.suffix.lower().lstrip(".") or "no-extension"
        destination_dir = target / folder
        destination = destination_dir / path.name
        if destination == path:
            print(f"skip self move: {path}", file=sys.stderr)
            continue
        print(f"{path} -> {destination}")
        if args.apply:
            destination_dir.mkdir(parents=True, exist_ok=True)
            if args.copy:
                shutil.copy2(path, destination)
            else:
                shutil.move(str(path), str(destination))
    if not args.apply:
        print("dry-run: pass --apply to change files")
    return 0


def cmd_replace(args: argparse.Namespace) -> int:
    if not args.old:
        print("error: old text cannot be empty", file=sys.stderr)
        return 2
    root = Path(args.root).expanduser().resolve()
    files = iter_files(root, args.pattern, args.recursive)
    changed = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        updated = text.replace(args.old, args.new)
        if updated != text:
            changed += 1
            print(path)
            if args.apply:
                path.write_text(updated, encoding="utf-8")
    if not args.apply:
        print(f"dry-run: {changed} file(s) would change; pass --apply to write")
    return 0


def cmd_duplicates(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    by_size: dict[int, list[Path]] = {}
    for path in iter_files(root, args.pattern, args.recursive):
        by_size.setdefault(path.stat().st_size, []).append(path)
    duplicates = []
    for same_size in by_size.values():
        if len(same_size) < 2:
            continue
        by_hash: dict[str, list[str]] = {}
        for path in same_size:
            by_hash.setdefault(file_digest(path), []).append(str(path.relative_to(root)))
        duplicates.extend(group for group in by_hash.values() if len(group) > 1)
    print(json.dumps({"root": str(root), "duplicates": duplicates}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inventory, organize, replace text, and find duplicates.")
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("inventory", help="list files as JSON")
    inventory.add_argument("root")
    inventory.add_argument("--pattern", default="*")
    inventory.add_argument("--recursive", action="store_true")
    inventory.set_defaults(func=cmd_inventory)

    organize = sub.add_parser("organize", help="group files into extension folders")
    organize.add_argument("root")
    organize.add_argument("--target", help="target folder, default: root")
    organize.add_argument("--pattern", default="*")
    organize.add_argument("--copy", action="store_true", help="copy instead of move")
    organize.add_argument("--apply", action="store_true", help="actually write changes")
    organize.set_defaults(func=cmd_organize)

    replace = sub.add_parser("replace", help="replace text in files")
    replace.add_argument("root")
    replace.add_argument("old")
    replace.add_argument("new")
    replace.add_argument("--pattern", default="*")
    replace.add_argument("--recursive", action="store_true")
    replace.add_argument("--apply", action="store_true", help="actually write changes")
    replace.set_defaults(func=cmd_replace)

    duplicates = sub.add_parser("duplicates", help="find duplicate files by sha256")
    duplicates.add_argument("root")
    duplicates.add_argument("--pattern", default="*")
    duplicates.add_argument("--recursive", action="store_true")
    duplicates.set_defaults(func=cmd_duplicates)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
