#!/usr/bin/env python3
"""Small offline helper for routine git operations."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_git(repo: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def ensure_repo(path: Path) -> Path:
    repo = path.expanduser().resolve()
    result = run_git(repo, ["rev-parse", "--show-toplevel"], check=False)
    if result.returncode != 0:
        print(f"not a git repository: {repo}", file=sys.stderr)
        sys.exit(2)
    return Path(result.stdout.strip())


def cmd_status(repo: Path, args: argparse.Namespace) -> int:
    branch = run_git(repo, ["branch", "--show-current"], check=False).stdout.strip()
    print(f"repo: {repo}")
    print(f"branch: {branch or '(detached)'}")
    print()
    porcelain = run_git(repo, ["status", "--short"]).stdout.strip()
    if porcelain:
        print(porcelain)
    else:
        print("clean")
    if args.verbose:
        print()
        print(run_git(repo, ["status", "--branch"]).stdout.rstrip())
    return 0


def cmd_snapshot(repo: Path, args: argparse.Namespace) -> int:
    unstaged = run_git(repo, ["diff", "--name-only"]).stdout.splitlines()
    staged = run_git(repo, ["diff", "--cached", "--name-only"]).stdout.splitlines()
    untracked = run_git(repo, ["ls-files", "--others", "--exclude-standard"]).stdout.splitlines()
    print("changed files:")
    for name in sorted(set(staged + unstaged + untracked)):
        marker = []
        if name in staged:
            marker.append("staged")
        if name in unstaged:
            marker.append("modified")
        if name in untracked:
            marker.append("untracked")
        print(f"- {name} [{', '.join(marker)}]")
    if not (staged or unstaged or untracked):
        print("- none")
    print()
    print("recent commits:")
    print(run_git(repo, ["log", "--oneline", f"-{args.limit}"]).stdout.rstrip() or "none")
    return 0


def cmd_branch(repo: Path, args: argparse.Namespace) -> int:
    if args.create:
        run_git(repo, ["switch", "-c", args.create])
    elif args.switch:
        run_git(repo, ["switch", args.switch])
    print(run_git(repo, ["branch", "--all", "--verbose", "--no-abbrev"]).stdout.rstrip())
    return 0


def cmd_save(repo: Path, args: argparse.Namespace) -> int:
    if not args.message:
        print("--message is required for save", file=sys.stderr)
        return 2
    if not args.all and not args.paths:
        print("save requires --all or at least one path", file=sys.stderr)
        return 2
    if args.all:
        run_git(repo, ["add", "--all"])
    else:
        run_git(repo, ["add", *args.paths])
    staged = run_git(repo, ["diff", "--cached", "--name-only"]).stdout.strip()
    if not staged:
        print("nothing staged")
        return 0
    print("staged:")
    print(staged)
    if args.dry_run:
        print("dry-run: commit not created")
        return 0
    run_git(repo, ["commit", "-m", args.message])
    print(run_git(repo, ["log", "--oneline", "-1"]).stdout.rstrip())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline git helper.")
    parser.add_argument("--repo", default=".", help="repository path, default: current directory")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="show branch and concise status")
    status.add_argument("--verbose", action="store_true", help="include full git status output")
    status.set_defaults(func=cmd_status)

    snapshot = sub.add_parser("snapshot", help="show changed files and recent commits")
    snapshot.add_argument("--limit", type=int, default=8, help="number of commits to show")
    snapshot.set_defaults(func=cmd_snapshot)

    branch = sub.add_parser("branch", help="list, create, or switch branches")
    branch.add_argument("--create", help="create and switch to a new branch")
    branch.add_argument("--switch", help="switch to an existing branch")
    branch.set_defaults(func=cmd_branch)

    save = sub.add_parser("save", help="stage files and create a commit")
    save.add_argument("--message", "-m", help="commit message")
    save.add_argument("--all", action="store_true", help="stage all changes")
    save.add_argument("--dry-run", action="store_true", help="stage but do not commit")
    save.add_argument("paths", nargs="*", help="paths to stage when --all is not used")
    save.set_defaults(func=cmd_save)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo = ensure_repo(Path(args.repo))
    try:
        return args.func(repo, args)
    except subprocess.CalledProcessError as error:
        return error.returncode


if __name__ == "__main__":
    raise SystemExit(main())
