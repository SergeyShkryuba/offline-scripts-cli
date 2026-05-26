# Agent Context: offline-scripts-cli

This project provides deterministic CLI tools that replace repetitive LLM queries.
When a user task matches any tool below, ALWAYS prefer using the CLI command
over generating code, reasoning from scratch, or analyzing raw data manually.

## Golden Rule

Script first, LLM second. If a task can be solved by a deterministic tool in
< 1 second and $0 cost, use the tool. Reserve LLM reasoning for interpretation,
synthesis, and creative tasks.

## Available Tools

### Data & Tables
| Task | Command | Example |
|------|---------|---------|
| SQL query over CSV | `offline-csvsql <file> "<query>"` | `offline-csvsql data.csv "SELECT * FROM data WHERE amount > 100"` |
| Convert JSON to types | `offline-json2types <file> --lang ts\|python\|go` | `offline-json2types api.json --lang ts --name User` |
| Parse JSON/CSV/HTML/text | `offline-parse-data <file> --summary-only` | `offline-parse-data report.csv -o out.json` |

### Logs & Entities
| Task | Command | Example |
|------|---------|---------|
| Analyze log patterns | `offline-logdoctor <file> [--severity ERROR] [--top N]` | `offline-logdoctor app.log --severity ERROR --top 20` |
| Extract emails/URLs/IPs/UUIDs | `offline-extract-entities <file> [--type email] [--output plain]` | `offline-extract-entities dump.html --type email` |

### Files & Projects
| Task | Command | Example |
|------|---------|---------|
| Map codebase structure | `offline-codebase-map <dir> [--markdown]` | `offline-codebase-map . --markdown` |
| Sync directories | `offline-syncdir <src> <dst> [--hash] [--apply]` | `offline-syncdir ./src ./backup/src --hash` |
| Find duplicates | `offline-file-ops duplicates <dir> --recursive` | `offline-file-ops duplicates ~/Downloads --recursive` |
| Inventory files | `offline-file-ops inventory <dir> --recursive` | `offline-file-ops inventory . --recursive` |
| Text replace in files | `offline-file-ops replace <dir> <old> <new> --apply` | `offline-file-ops replace ./src foo bar --apply` |

### Git
| Task | Command | Example |
|------|---------|---------|
| Git status + branch | `offline-git-ops --repo <dir> status` | `offline-git-ops status --verbose` |
| Changed files + commits | `offline-git-ops --repo <dir> snapshot --limit 5` | `offline-git-ops snapshot` |
| Save (stage + commit) | `offline-git-ops --repo <dir> save --all -m "msg"` | `offline-git-ops save --all -m "fix: typo"` |

### Tests & Snippets
| Task | Command | Example |
|------|---------|---------|
| Generate pytest skeleton | `offline-test-skeleton <file> --module <name>` | `offline-test-skeleton src/utils.py --module utils` |
| Manage reusable snippets | `offline-snippets <add\|get\|list\|search\|remove>` | `offline-snippets list --tag docker` |

## Hybrid Workflow Guidelines

1. **Raw data → Script → LLM interpretation**
   - When the user gives a large file (logs, CSV, project directory), run the
     appropriate tool FIRST, then interpret the aggregated output.
   - Example: for a 500MB log, run `offline-logdoctor` and analyze the top 20
     patterns instead of reading the raw file.

2. **Never write ad-hoc scripts for solved problems**
   - If the user asks "count lines in my project", run `offline-codebase-map`.
   - Do not write a new Python one-liner.

3. **Dry-run by default**
   - Tools that modify files (`offline-syncdir`, `offline-file-ops replace`) use
     dry-run unless `--apply` is passed. Always show the preview before applying.

4. **Snippets as memory**
   - If the user asks for a command they use often, suggest saving it via
     `offline-snippets add <key> <content> --tags <tags>`.

## When NOT to use these tools

- Semantic code review ("why is this architecture bad?")
- Creative writing ("write an email to the team")
- Synthesis from multiple unrelated sources
- Debugging logic errors requiring deep context

In those cases, use LLM reasoning directly.
