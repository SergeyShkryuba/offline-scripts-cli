#!/usr/bin/env python3
"""Synchronize directories with dry-run, hash verification, and detailed reporting."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan(root: Path) -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            continue
        stat = path.stat()
        files[rel] = {
            "path": path,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }
    return files


def compare(src_files: dict, dst_files: dict, use_hash: bool) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    all_keys = sorted(set(src_files) | set(dst_files))

    for key in all_keys:
        src = src_files.get(key)
        dst = dst_files.get(key)

        if not src:
            actions.append({"action": "delete", "path": key, "reason": "not in source"})
            continue
        if not dst:
            actions.append({"action": "copy", "path": key, "reason": "new"})
            continue

        if src["size"] != dst["size"]:
            actions.append({"action": "copy", "path": key, "reason": "size mismatch"})
            continue

        if use_hash:
            if file_hash(src["path"]) != file_hash(dst["path"]):
                actions.append({"action": "copy", "path": key, "reason": "hash mismatch"})
            continue

        if abs(src["mtime"] - dst["mtime"]) > 1:
            actions.append({"action": "copy", "path": key, "reason": "time mismatch"})

    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize source directory to target.")
    parser.add_argument("source", help="source directory")
    parser.add_argument("target", help="target directory")
    parser.add_argument("--hash", action="store_true", help="compare by sha256 instead of mtime")
    parser.add_argument("--delete", action="store_true", help="delete files in target not present in source")
    parser.add_argument("--apply", action="store_true", help="actually perform file operations")
    parser.add_argument("--json", action="store_true", help="output actions as JSON")
    args = parser.parse_args()

    src_root = Path(args.source).expanduser().resolve()
    dst_root = Path(args.target).expanduser().resolve()

    if not src_root.is_dir():
        print(f"error: not a directory: {src_root}", file=sys.stderr)
        return 2
    if src_root == dst_root:
        print("error: source and target must be different directories", file=sys.stderr)
        return 2
    if dst_root.exists() and not dst_root.is_dir():
        print(f"error: target is not a directory: {dst_root}", file=sys.stderr)
        return 2
    if src_root in dst_root.parents or dst_root in src_root.parents:
        print("error: source and target must not contain each other", file=sys.stderr)
        return 2

    src_files = scan(src_root)
    dst_files = scan(dst_root) if dst_root.exists() else {}

    actions = compare(src_files, dst_files, args.hash)
    if not args.delete:
        actions = [a for a in actions if a["action"] != "delete"]

    if args.json:
        print(json.dumps({
            "source": str(src_root),
            "target": str(dst_root),
            "actions": actions,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"source: {src_root}")
        print(f"target: {dst_root}")
        print(f"actions: {len(actions)}")
        for action in actions:
            mark = "[-]" if action["action"] == "delete" else "[+]"
            print(f"  {mark} {action['path']} ({action['reason']})")
        if not args.apply:
            print("dry-run: pass --apply to execute")

    if not args.apply:
        return 0

    for action in actions:
        rel = action["path"]
        if action["action"] == "delete":
            (dst_root / rel).unlink()
            print(f"deleted: {rel}")
        elif action["action"] == "copy":
            src_path = src_root / rel
            dst_path = dst_root / rel
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            print(f"copied: {rel}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
