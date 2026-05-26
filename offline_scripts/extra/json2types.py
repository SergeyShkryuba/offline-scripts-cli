#!/usr/bin/env python3
"""Convert JSON or JSON Schema to type definitions."""

from __future__ import annotations

import argparse
import json
import keyword
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def to_valid_name(key: str, fallback: str = "value") -> str:
    """Turn a JSON key into a valid identifier."""
    key = re.sub(r"\W+", "_", key.strip())
    key = key.strip("_") or fallback
    if key[0].isdigit():
        key = "_" + key
    if keyword.iskeyword(key) or key.lower() in {"none", "true", "false"}:
        key += "_"
    return key


def to_type_name(name: str) -> str:
    parts = re.split(r"\W+|_", name.strip())
    value = "".join(part[:1].upper() + part[1:] for part in parts if part)
    return to_valid_name(value or "Root", fallback="Root")


def is_array(value: Any) -> bool:
    return isinstance(value, list)


def ts_key(key: str) -> str:
    safe = to_valid_name(key)
    return key if safe == key else json.dumps(key)


def merge_types(types: list[str]) -> str:
    unique = sorted(set(types))
    return unique[0] if len(unique) == 1 else " | ".join(unique)


def infer_ts(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, Mapping):
        return "object"
    if is_array(value):
        return "array"
    return "any"


def infer_python(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, Mapping):
        return "dict"
    if is_array(value):
        return "list"
    return "Any"


def infer_go(value: Any) -> str:
    if value is None:
        return "interface{}"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float64"
    if isinstance(value, str):
        return "string"
    if isinstance(value, Mapping):
        return "map[string]interface{}"
    if is_array(value):
        return "[]interface{}"
    return "interface{}"


INFER = {
    "ts": infer_ts,
    "typescript": infer_ts,
    "py": infer_python,
    "python": infer_python,
    "go": infer_go,
    "golang": infer_go,
}


def infer_ts_array(value: list[Any]) -> str:
    if not value:
        return "unknown[]"
    return f"({merge_types([infer_ts(item) for item in value])})[]"


def infer_python_array(value: list[Any]) -> str:
    if not value:
        return "List[Any]"
    types = {infer_python(item) for item in value}
    if len(types) == 1:
        return f"List[{types.pop()}]"
    return "List[Any]"


def infer_go_array(value: list[Any]) -> str:
    if not value:
        return "[]interface{}"
    types = {infer_go(item) for item in value}
    if len(types) == 1:
        return f"[]{types.pop()}"
    return "[]interface{}"


def collect_ts_interfaces(name: str, obj: Mapping[str, Any], seen: set[str] | None = None) -> list[str]:
    seen = seen or set()
    interface_name = to_type_name(name)
    nested_defs: list[str] = []
    lines: list[str] = []
    lines.append(f"interface {interface_name} {{")
    for key, value in obj.items():
        safe_key = to_type_name(key)
        field = ts_key(key)
        if isinstance(value, Mapping) and value:
            lines.append(f"  {field}: {safe_key};")
            nested_defs.extend(collect_ts_interfaces(safe_key, value, seen))
        elif is_array(value) and value and isinstance(value[0], Mapping):
            lines.append(f"  {field}: {safe_key}[];")
            nested_defs.extend(collect_ts_interfaces(safe_key, value[0], seen))
        else:
            type_name = infer_ts_array(value) if is_array(value) else infer_ts(value)
            lines.append(f"  {field}: {type_name};")
    lines.append("}")
    if interface_name in seen:
        return nested_defs
    seen.add(interface_name)
    return ["\n".join(lines)] + nested_defs


def build_ts_interface(name: str, obj: Mapping[str, Any]) -> str:
    return "\n\n".join(collect_ts_interfaces(name, obj))


def collect_python_dataclasses(name: str, obj: Mapping[str, Any], seen: set[str] | None = None) -> list[str]:
    seen = seen or set()
    class_name = to_type_name(name)
    nested_defs: list[str] = []
    fields: list[str] = []

    for key, value in obj.items():
        safe_key = to_valid_name(key)
        nested_name = to_type_name(key)
        if isinstance(value, Mapping) and value:
            fields.append(f"    {safe_key}: {nested_name}")
            nested_defs.extend(collect_python_dataclasses(nested_name, value, seen))
        elif is_array(value) and value and isinstance(value[0], Mapping):
            fields.append(f"    {safe_key}: List[{nested_name}]")
            nested_defs.extend(collect_python_dataclasses(nested_name, value[0], seen))
        else:
            type_name = infer_python_array(value) if is_array(value) else infer_python(value)
            if value is None:
                type_name = "Optional[Any]"
            fields.append(f"    {safe_key}: {type_name}")

    if class_name in seen:
        return nested_defs
    seen.add(class_name)
    lines: list[str] = []
    lines.append(f"@dataclass")
    lines.append(f"class {class_name}:")
    lines.extend(fields or ["    pass"])
    return nested_defs + ["\n".join(lines)]


def build_python_dataclass(name: str, obj: Mapping[str, Any]) -> str:
    lines = [
        "from __future__ import annotations",
        "from dataclasses import dataclass",
        "from typing import Any, List, Optional",
    ]
    lines.extend(collect_python_dataclasses(name, obj))
    return "\n\n".join(lines)


def to_go_field_name(key: str) -> str:
    name = to_type_name(key)
    if not name[0].isalpha():
        name = "Field" + name
    return name


def collect_go_structs(name: str, obj: Mapping[str, Any], seen: set[str] | None = None) -> list[str]:
    seen = seen or set()
    struct_name = to_type_name(name)
    nested_defs: list[str] = []
    lines: list[str] = []
    lines.append(f"type {struct_name} struct {{")
    for key, value in obj.items():
        safe_key = to_type_name(key)
        field_name = to_go_field_name(key)
        tag = f'`json:"{key}"`'
        if isinstance(value, Mapping) and value:
            lines.append(f"\t{field_name} {safe_key} {tag}")
            nested_defs.extend(collect_go_structs(safe_key, value, seen))
        elif is_array(value) and value and isinstance(value[0], Mapping):
            lines.append(f"\t{field_name} []{safe_key} {tag}")
            nested_defs.extend(collect_go_structs(safe_key, value[0], seen))
        else:
            type_name = infer_go_array(value) if is_array(value) else infer_go(value)
            lines.append(f"\t{field_name} {type_name} {tag}")
    lines.append("}")
    if struct_name in seen:
        return nested_defs
    seen.add(struct_name)
    return ["\n".join(lines)] + nested_defs


def build_go_struct(name: str, obj: Mapping[str, Any]) -> str:
    return "\n\n".join(collect_go_structs(name, obj))


def generate(name: str, data: Any, lang: str) -> str:
    if not isinstance(data, Mapping):
        print("error: top-level value must be an object", file=sys.stderr)
        sys.exit(2)
    if lang in ("ts", "typescript"):
        return build_ts_interface(name, data)
    if lang in ("py", "python"):
        return build_python_dataclass(name, data)
    if lang in ("go", "golang"):
        return build_go_struct(name, data)
    print(f"error: unsupported language: {lang}", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert JSON to type definitions.")
    parser.add_argument("file", help="JSON file")
    parser.add_argument("--name", "-n", default="Root", help="root type name")
    parser.add_argument("--lang", "-l", choices=["ts", "typescript", "py", "python", "go", "golang"], default="ts", help="target language")
    parser.add_argument("--output", "-o", help="write to file")
    args = parser.parse_args()

    path = Path(args.file).expanduser().resolve()
    data = json.loads(path.read_text(encoding="utf-8"))

    result = generate(args.name, data, args.lang)

    if args.output:
        Path(args.output).expanduser().write_text(result + "\n", encoding="utf-8")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
