# Extra Offline Scripts

Eight additional helpers for tasks that are often delegated to an LLM but solve faster locally.

Install the package from the repo root first:

```bash
python3 -m pip install -e .
```

## codebase_map.py

Build a structured map of any codebase: languages, line counts, entry points, and largest files.

```bash
offline-codebase-map ~/Projects/my-app
offline-codebase-map ~/Projects/my-app --markdown > OVERVIEW.md
offline-codebase-map . --markdown
```

Output formats: JSON (default) or Markdown (`--markdown`).

## json2types.py

Convert JSON objects into type definitions for TypeScript, Python, or Go.

```bash
offline-json2types schema/user.json --lang ts --name User
offline-json2types config.json --lang python --name Config -o models.py
offline-json2types api-response.json --lang go --name Response
```

Supported languages: `ts` / `typescript`, `py` / `python`, `go` / `golang`.

## test_skeleton.py

Generate pytest skeletons from a Python source file by inspecting functions and classes via `ast`.

```bash
offline-test-skeleton src/utils.py
offline-test-skeleton src/utils.py --module myproject.utils -o tests/test_utils.py
```

Generated tests follow the Arrange-Act-Assert pattern with placeholder assertions.

## snippets.py

Local snippet manager for reusable commands, templates, and code blocks. No cloud, no sync — just a JSON file in `~/.snippets/`.

```bash
offline-snippets add docker-postgres "docker run -d -e POSTGRES_PASSWORD=pass postgres" --tags docker,database
offline-snippets add fastapi-dockerfile --file ./Dockerfile --tags docker,fastapi
offline-snippets list
offline-snippets list --tag docker
offline-snippets search postgres
offline-snippets get docker-postgres
offline-snippets remove docker-postgres
```

## csvsql.py

Run SQL queries directly against CSV files using an in-memory SQLite database.

```bash
offline-csvsql data.csv "SELECT * FROM data WHERE amount > 100 ORDER BY date DESC"
offline-csvsql report.csv "SELECT category, SUM(amount) FROM data GROUP BY category" --output csv
```

## logdoctor.py

Analyze log files: group similar lines into patterns, count severities, and extract top issues.

```bash
offline-logdoctor /var/log/nginx/error.log
offline-logdoctor app.log --severity ERROR --top 20
offline-logdoctor app.log --pattern "timeout"
```

## syncdir.py

Synchronize directories with dry-run, optional hash comparison, and detailed reporting.

```bash
offline-syncdir ~/Documents/backup /mnt/external/backup
offline-syncdir ./src ./deploy/src --hash --apply
offline-syncdir ./src ./deploy/src --json --delete
```

## extract_entities.py

Extract emails, URLs, IPs, UUIDs, dates, and phone numbers from text files or stdin.

```bash
offline-extract-entities contacts.txt
offline-extract-entities dump.log --type email --type ipv4 --output plain
cat page.html | offline-extract-entities --type url
```

## Why these exist

| Instead of asking an LLM... | Run this locally |
|---------------------------|------------------|
| "Analyze my project structure" | `offline-codebase-map` |
| "Generate TypeScript interfaces from JSON" | `offline-json2types` |
| "Write tests for this module" | `offline-test-skeleton` |
| "Remind me how to run Postgres in Docker" | `offline-snippets get docker-postgres` |
| "Analyze this CSV and group by category" | `offline-csvsql` |
| "Find top errors in these logs" | `offline-logdoctor` |
| "Sync these two folders" | `offline-syncdir` |
| "Extract all emails from this text" | `offline-extract-entities` |

All scripts use only the Python standard library (no pip install required).
