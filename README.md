# Offline Scripts

> **Note:** Although my primary focus is Frontend Web Development (JS/TS, React, Vue), I built this Python CLI utility to automate my local offline workflows. It's a collection of tools I use to parse data, manage files, and streamline my development process when I'm away from a network connection.

Eleven small CLI tools for common local tasks when an LLM or network connection is not available.

## Install

### Option A: install.sh (recommended for offline/legacy systems)

```bash
git clone https://github.com/SergeyShkryuba/offline-scripts-cli.git
cd offline-scripts-cli
./install.sh
```

This installs the package in user mode and adds the user Python bin directory to `PATH` in `~/.zshrc`.
The shell RC file is auto-detected from your login shell, with `--rc-file` available as an override.

### Option B: pipx (isolated, clean)

```bash
brew install pipx && pipx ensurepath
pipx install git+https://github.com/SergeyShkryuba/offline-scripts-cli.git
```

`pipx` creates an isolated virtual environment for the tool and manages `PATH` automatically.
Upgrade later with `pipx upgrade offline-scripts-cli`.

### Option C: pip (editable, manual)

```bash
git clone https://github.com/SergeyShkryuba/offline-scripts-cli.git
cd offline-scripts-cli
python3 -m pip install -e . --user --no-build-isolation
```

This installs console commands with the `offline-` prefix.

## Core commands

```bash
offline-git-ops --repo /path/to/repo status
offline-git-ops --repo /path/to/repo snapshot --limit 5
offline-git-ops --repo /path/to/repo save --all -m "Describe change" --dry-run

offline-parse-data data.json --summary-only
offline-parse-data table.csv -o parsed.json
offline-parse-data page.html --summary-only

offline-file-ops inventory ~/Downloads --recursive
offline-file-ops organize ~/Downloads --target ~/Downloads/sorted --copy --apply
offline-file-ops replace ./src old_text new_text --pattern "*.txt" --recursive
offline-file-ops duplicates ~/Downloads --recursive
```

## Extra commands

```bash
offline-codebase-map . --markdown
offline-json2types api-response.json --lang go --name Response
offline-test-skeleton src/utils.py --module myproject.utils -o tests/test_utils.py
offline-snippets list --tag docker
offline-csvsql data.csv "SELECT * FROM data LIMIT 10"
offline-logdoctor app.log --severity ERROR --top 20
offline-syncdir ./src ./deploy/src --hash --apply
offline-extract-entities contacts.txt --output plain
```

Supports only the Python standard library. Commands that modify files use dry-run output unless `--apply` is provided.
