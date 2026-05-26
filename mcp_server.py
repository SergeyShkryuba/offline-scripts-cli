#!/usr/bin/env python3
"""MCP (Model Context Protocol) server concept for offline-scripts-cli.

This is a proof-of-concept showing how an AI client (Claude Desktop,
Cursor, etc.) can discover and execute offline-scripts-cli tools automatically.

To use:
    1. Install the MCP SDK: pip install mcp
    2. Configure your AI client to point to this script
    3. The AI will decide which tool to call based on user queries

Example Claude Desktop config (claude_desktop_config.json):
    {
        "mcpServers": {
            "offline-scripts": {
                "command": "python3",
                "args": ["/path/to/mcp_server.py"]
            }
        }
    }
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

# Minimal MCP implementation without external deps for demonstration.
# For production, install: pip install mcp


def run_tool(name: str, args: list[str]) -> dict[str, Any]:
    """Execute an offline-scripts-cli command and return structured output."""
    cmd = [f"offline-{name.replace('_', '-')}"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {
            "command": " ".join(cmd),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except FileNotFoundError:
        return {"error": f"Command not found: {cmd[0]}. Is offline-scripts-cli installed?"}
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out: {' '.join(cmd)}"}


TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "csvsql",
        "description": "Run SQL queries against CSV files using SQLite in-memory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to CSV file"},
                "query": {"type": "string", "description": "SQL query string"},
            },
            "required": ["file", "query"],
        },
    },
    {
        "name": "logdoctor",
        "description": "Analyze log files: group patterns, count severities, find top errors.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to log file"},
                "severity": {"type": "string", "description": "Filter by severity (ERROR, WARN, etc.)"},
                "top": {"type": "integer", "description": "Number of top patterns to return"},
            },
            "required": ["file"],
        },
    },
    {
        "name": "codebase_map",
        "description": "Generate a structured map of a codebase with languages, lines, and entry points.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Project root directory"},
                "markdown": {"type": "boolean", "description": "Output markdown instead of JSON"},
            },
            "required": ["root"],
        },
    },
    {
        "name": "json2types",
        "description": "Convert JSON to TypeScript, Python, or Go type definitions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to JSON file"},
                "lang": {"type": "string", "enum": ["ts", "python", "go"], "description": "Target language"},
                "name": {"type": "string", "description": "Root type name"},
            },
            "required": ["file", "lang"],
        },
    },
    {
        "name": "test_skeleton",
        "description": "Generate pytest skeletons from a Python source file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to Python file"},
                "module": {"type": "string", "description": "Import module name"},
            },
            "required": ["file"],
        },
    },
    {
        "name": "syncdir",
        "description": "Synchronize two directories with dry-run and hash verification.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source directory"},
                "target": {"type": "string", "description": "Target directory"},
                "hash": {"type": "boolean", "description": "Compare by SHA256"},
            },
            "required": ["source", "target"],
        },
    },
    {
        "name": "extract_entities",
        "description": "Extract emails, URLs, IPs, UUIDs, dates from text files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to text file"},
                "type": {"type": "string", "description": "Entity type filter (email, url, ipv4, etc.)"},
            },
            "required": ["file"],
        },
    },
]


def handle_list_tools() -> dict[str, Any]:
    return {"tools": TOOLS_SCHEMA}


def handle_call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "csvsql":
        args = [arguments["file"], arguments["query"]]
        return {"content": [{"type": "text", "text": json.dumps(run_tool("csvsql", args), indent=2)}]}
    if name == "logdoctor":
        args = [arguments["file"]]
        if arguments.get("severity"):
            args += ["--severity", arguments["severity"]]
        if arguments.get("top"):
            args += ["--top", str(arguments["top"])]
        return {"content": [{"type": "text", "text": json.dumps(run_tool("logdoctor", args), indent=2)}]}
    if name == "codebase_map":
        args = [arguments["root"]]
        if arguments.get("markdown"):
            args.append("--markdown")
        return {"content": [{"type": "text", "text": json.dumps(run_tool("codebase_map", args), indent=2)}]}
    if name == "json2types":
        args = [arguments["file"], "--lang", arguments["lang"]]
        if arguments.get("name"):
            args += ["--name", arguments["name"]]
        return {"content": [{"type": "text", "text": json.dumps(run_tool("json2types", args), indent=2)}]}
    if name == "test_skeleton":
        args = [arguments["file"]]
        if arguments.get("module"):
            args += ["--module", arguments["module"]]
        return {"content": [{"type": "text", "text": json.dumps(run_tool("test_skeleton", args), indent=2)}]}
    if name == "syncdir":
        args = [arguments["source"], arguments["target"]]
        if arguments.get("hash"):
            args.append("--hash")
        return {"content": [{"type": "text", "text": json.dumps(run_tool("syncdir", args), indent=2)}]}
    if name == "extract_entities":
        args = [arguments["file"]]
        if arguments.get("type"):
            args += ["--type", arguments["type"]]
        return {"content": [{"type": "text", "text": json.dumps(run_tool("extract_entities", args), indent=2)}]}
    return {"content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {name}"})}]}


def main() -> None:
    """Minimal stdio MCP server loop."""
    import sys

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            msg = json.loads(line)
            method = msg.get("method")
            msg_id = msg.get("id")
            result: dict[str, Any] = {}

            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "serverInfo": {"name": "offline-scripts-cli-mcp", "version": "0.1.0"},
                }
            elif method == "tools/list":
                result = handle_list_tools()
            elif method == "tools/call":
                params = msg.get("params", {})
                result = handle_call_tool(params.get("name", ""), params.get("arguments", {}))
            else:
                result = {"error": {"code": -32601, "message": f"Method not found: {method}"}}

            response = json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result})
            print(response, flush=True)
        except Exception as error:
            err = json.dumps({"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32603, "message": str(error)}})
            print(err, flush=True)


if __name__ == "__main__":
    main()
