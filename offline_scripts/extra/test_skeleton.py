#!/usr/bin/env python3
"""Generate pytest skeletons from Python source files."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Any


def get_functions_and_classes(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    items: dict[str, Any] = {"functions": [], "classes": []}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            args = [arg.arg for arg in node.args.args if arg.arg != "self"]
            items["functions"].append({"name": node.name, "args": args})
        elif isinstance(node, ast.ClassDef):
            methods: list[dict] = []
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("_"):
                    args = [arg.arg for arg in child.args.args if arg.arg != "self"]
                    methods.append({"name": child.name, "args": args})
            items["classes"].append({"name": node.name, "methods": methods})
    return items


def build_test(module_name: str, items: dict[str, Any]) -> str:
    imports = sorted([item["name"] for item in items["functions"]] + [item["name"] for item in items["classes"]])
    lines: list[str] = [
        "import pytest",
        f"from {module_name} import {', '.join(imports)}" if imports else f"import {module_name}",
        "",
    ]

    for func in items["functions"]:
        args = ", ".join(func["args"])
        args_comment = f"  # parameters: {args}" if args else ""
        lines.append(f"def test_{func['name']}():{args_comment}")
        lines.append("    # Arrange")
        lines.append("    pass")
        lines.append("")
        lines.append("    # Act")
        lines.append("    result = None")
        lines.append("")
        lines.append("    # Assert")
        lines.append("    assert result is not None")
        lines.append("")

    for cls in items["classes"]:
        lines.append(f"class Test{cls['name']}:")
        if not cls["methods"]:
            lines.append("    pass")
            lines.append("")
            continue
        for method in cls["methods"]:
            args = ", ".join(method["args"])
            args_comment = f"  # parameters: {args}" if args else ""
            lines.append(f"    def test_{method['name']}(self):{args_comment}")
            lines.append("        # Arrange")
            lines.append("        pass")
            lines.append("")
            lines.append("        # Act")
            lines.append("        instance = None")
            lines.append("        result = None")
            lines.append("")
            lines.append("        # Assert")
            lines.append("        assert result is not None")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate pytest skeletons.")
    parser.add_argument("file", help="python source file")
    parser.add_argument("--module", "-m", help="import module name (default: filename stem)")
    parser.add_argument("--output", "-o", help="write to file")
    args = parser.parse_args()

    path = Path(args.file).expanduser().resolve()
    source = path.read_text(encoding="utf-8")
    items = get_functions_and_classes(source)

    module = args.module or path.stem.replace("test_", "").replace("_test", "")
    result = build_test(module, items)

    if args.output:
        Path(args.output).expanduser().write_text(result, encoding="utf-8")
        print(f"written: {args.output}")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
