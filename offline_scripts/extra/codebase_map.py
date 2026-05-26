#!/usr/bin/env python3
"""Build a structured map of a codebase."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from collections import Counter
from pathlib import Path


LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++",
    ".hpp": "C++",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".fish": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".xml": "XML",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".dockerfile": "Dockerfile",
    ".tf": "Terraform",
    ".ipynb": "Jupyter",
}

SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "venv",
        "node_modules",
        ".idea",
        ".vscode",
        "target",
        "build",
        "dist",
        ".eggs",
        "*.egg-info",
    }
)

SKIP_EXTS: frozenset[str] = frozenset({".pyc", ".pyo", ".so", ".dylib", ".dll", ".class", ".o", ".a"})


def iter_sources(root: Path) -> list[Path]:
    files: list[Path] = []
    if not root.exists():
        print(f"error: root does not exist: {root}", file=sys.stderr)
        sys.exit(2)
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        sys.exit(2)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(any(fnmatch.fnmatch(part, pattern) for pattern in SKIP_DIRS) for part in rel.parts):
            continue
        if path.suffix.lower() in SKIP_EXTS:
            continue
        files.append(path)
    return files


def count_lines(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return 0
    return len(text.splitlines())


def detect_language(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix:
        return LANGUAGE_MAP.get(suffix, suffix.lstrip(".").upper())
    name = path.name.lower()
    if name == "dockerfile":
        return "Dockerfile"
    if name == "makefile":
        return "Makefile"
    return "(unknown)"


def guess_entry_points(root: Path, files: list[Path]) -> list[str]:
    entries: list[str] = []
    for name in ("main.py", "app.py", "server.py", "index.js", "index.ts", "main.go", "main.rs"):
        candidate = root / name
        if candidate.is_file():
            entries.append(str(candidate.relative_to(root)))
    for path in files:
        if path.name == "__main__.py":
            entries.append(str(path.relative_to(root)))
    return sorted(set(entries))


def build_map(root: Path) -> dict:
    files = iter_sources(root)
    total_size = 0
    total_lines = 0
    lang_counter: Counter[str] = Counter()
    file_data: list[dict] = []

    for path in files:
        lang = detect_language(path)
        size = path.stat().st_size
        lines = count_lines(path)
        total_size += size
        total_lines += lines
        lang_counter[lang] += lines
        file_data.append(
            {
                "path": str(path.relative_to(root)),
                "language": lang,
                "lines": lines,
                "bytes": size,
            }
        )

    top_files = sorted(file_data, key=lambda x: x["lines"], reverse=True)[:10]

    return {
        "root": str(root),
        "summary": {
            "total_files": len(files),
            "total_lines": total_lines,
            "total_bytes": total_size,
            "languages": dict(lang_counter.most_common()),
            "entry_points": guess_entry_points(root, files),
        },
        "top_files": [{"path": f["path"], "lines": f["lines"]} for f in top_files],
    }


def build_markdown(data: dict) -> str:
    s = data["summary"]
    lines: list[str] = [
        f"# Codebase Map: {data['root']}",
        "",
        "## Summary",
        "",
        f"- **Files:** {s['total_files']}",
        f"- **Lines of code:** {s['total_lines']:,}",
        f"- **Size:** {s['total_bytes']:,} bytes",
        "",
        "## Languages",
        "",
        "| Language | Lines |",
        "|----------|-------|",
    ]
    for lang, count in s["languages"].items():
        lines.append(f"| {lang} | {count:,} |")
    lines.append("")
    if s["entry_points"]:
        lines.append("## Probable Entry Points")
        lines.append("")
        for ep in s["entry_points"]:
            lines.append(f"- `{ep}`")
        lines.append("")
    lines.append("## Largest Files")
    lines.append("")
    lines.append("| File | Lines |")
    lines.append("|------|-------|")
    for f in data["top_files"]:
        lines.append(f"| `{f['path']}` | {f['lines']:,} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Map a codebase.")
    parser.add_argument("root", nargs="?", default=".", help="project root")
    parser.add_argument("--markdown", "-m", action="store_true", help="output markdown")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    data = build_map(root)

    if args.markdown:
        print(build_markdown(data))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
