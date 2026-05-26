#!/usr/bin/env python3
"""Run SQL queries against CSV files using an in-memory SQLite database."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


def sanitize_column(name: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name).strip("_") or "col"


def unique_columns(names: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    result: list[str] = []
    for name in names:
        base = sanitize_column(name)
        counts[base] = counts.get(base, 0) + 1
        result.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
    return result


def load_csv(cursor: sqlite3.Cursor, path: Path, table_name: str) -> None:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        reader = csv.reader(handle, dialect=dialect)
        headers = next(reader, None)
        if not headers:
            print("error: no headers found in CSV", file=sys.stderr)
            sys.exit(2)
        columns = unique_columns([str(field) for field in headers])
        col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
        cursor.execute(f'CREATE TABLE "{table_name}" ({col_defs})')
        placeholders = ", ".join("?" for _ in columns)
        insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'
        for row in reader:
            values = list(row[: len(columns)])
            if len(values) < len(columns):
                values.extend([""] * (len(columns) - len(values)))
            cursor.execute(insert_sql, values)


def rows_to_json(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    names = [desc[0] for desc in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def rows_to_csv(cursor: sqlite3.Cursor) -> str:
    names = [desc[0] for desc in cursor.description]
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(names)
    writer.writerows(cursor.fetchall())
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Query CSV files with SQL.")
    parser.add_argument("file", help="CSV file to load")
    parser.add_argument("query", nargs="?", default="SELECT * FROM data LIMIT 10", help="SQL query (default: SELECT * FROM data LIMIT 10)")
    parser.add_argument("--table", "-t", default="data", help="table name in SQL")
    parser.add_argument("--output", "-o", choices=["json", "csv"], default="json", help="output format")
    args = parser.parse_args()

    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    load_csv(cursor, path, args.table)

    try:
        cursor.execute(args.query)
    except sqlite3.Error as error:
        print(f"sql error: {error}", file=sys.stderr)
        conn.close()
        return 2

    if cursor.description is None:
        conn.commit()
        conn.close()
        return 0

    if args.output == "json":
        result = rows_to_json(cursor)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(rows_to_csv(cursor), end="")

    conn.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.exit(0)
