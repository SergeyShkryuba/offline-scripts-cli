# Offline Toolkit Workflow Guide

How to use offline-scripts-cli effectively as a replacement for repetitive LLM queries.

---

## 1. The Golden Rule: Script First, LLM Second

Before asking an LLM, ask yourself:

> "If I write a script in 15 minutes but would ask an LLM 3+ times, which is cheaper?"

| Task | Solution | Break-even threshold |
|------|----------|---------------------|
| Analyze CSV | `offline-csvsql` | 2 LLM queries |
| Sync folders | `offline-syncdir` | Once per month |
| Generate types from JSON | `offline-json2types` | 3 API endpoints |
| Search logs | `offline-logdoctor` | 1 incident |

**Rule of thumb:** 80% of tasks you paste into ChatGPT are solved faster and more accurately by a script.

---

## 2. Shell Aliases

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
alias cbm='offline-codebase-map . --markdown'
alias j2t='offline-json2types'
alias skel='offline-test-skeleton'
alias snippets='offline-snippets'
alias sq='offline-csvsql'
alias logs='offline-logdoctor'
alias ents='offline-extract-entities'
alias syncd='offline-syncdir'
alias gstat='offline-git-ops status'
alias gsave='offline-git-ops save'
alias gsnap='offline-git-ops snapshot'
```

---

## 3. Role-Based Playbooks

### Backend Developer

```bash
# Onboard a new teammate
cbm > ONBOARDING.md

# New API endpoint -> frontend types
curl -s http://localhost:8000/api/user/1 | jq '.' > /tmp/user.json
j2t /tmp/user.json --lang ts --name User > frontend/src/types.ts

# Write tests for a new module
skel src/payments.py -o tests/test_payments.py

# Pre-release inventory
offline-file-ops inventory . | jq '.files | map(.extension) | unique'
```

### DevOps / SRE

```bash
# Incident response: analyze production logs
ssh server "tail -n 10000 /var/log/app/error.log" | logs --severity ERROR --top 20

# Backup configs before deploy
syncd /etc/nginx ./backup/nginx-$(date +%Y%m%d) --hash --apply

# Extract IPs from firewall logs for blocklist
ents /var/log/ufw.log --type ipv4 --output plain | sort -u > blocklist.txt

# Compare two releases
offline-syncdir ./release-v1.2 ./release-v1.3 --json | jq '.actions | length'
```

### Data Analyst

```bash
# Marketing CSV summary
sq leads.csv "SELECT source, COUNT(*), AVG(deal_size) FROM data GROUP BY source" --output csv

# Extract emails from HTML dump
ents dump.html --type email > emails.txt

# Validate data integrity between extracts
syncd ./extract-2024-01 ./extract-2024-02 --hash --json | \
  jq '.actions[] | select(.reason == "hash mismatch")'
```

---

## 4. Snippets as Personal Knowledge Base

Do not use snippets as simple copy-paste. Use them as an **offline Stack Overflow replacement**.

```bash
# Add only commands you have personally verified
offline-snippets add k8s-debug \
  "kubectl run debug --rm -it --image=busybox --restart=Never -- sh" \
  --tags k8s,debug

offline-snippets add psql-docker \
  "docker exec -it postgres psql -U admin -d mydb" \
  --tags docker,postgres

# Search later
offline-snippets search docker
```

**Principle:** a snippet lives as long as it works. Does not work — delete it.

---

## 5. Offline-First Mentality

On a machine without internet (airplane, closed network, VPN down), verify:

```bash
for cmd in offline-git-ops offline-csvsql offline-logdoctor offline-syncdir; do
  which $cmd >/dev/null 2>&1 || echo "MISSING: $cmd"
done
```

Document incidents in snippets, not in your head:

```bash
offline-snippets add incident-2024-05-26 \
  "Memory leak: check /var/log/app for OOM, then run: offline-logdoctor /var/log/app/error.log --pattern 'Killed process'" \
  --tags incident,memory,playbook
```

---

## 6. Extending the Toolkit

When a new task appears, run through this checklist:

1. **Does it repeat 3+ times?** -> Write a script
2. **Is it one-time?** -> Use `ipython` or `python3 -c`
3. **Does it require semantic analysis?** -> Use LLM
4. **Can existing scripts be composed?** -> Pipe them:

```bash
offline-file-ops inventory ~/Downloads --pattern "*.csv" --recursive | \
  jq -r '.files[].path' | \
  while read f; do
    echo "=== $f ==="
    offline-csvsql "$f" "SELECT COUNT(*) FROM data"
  done
```

---

## 7. Token Savings Estimate

Track what you save:

| Action | Equivalent tokens | Money saved |
|--------|-------------------|-------------|
| `offline-codebase-map` | ~500 tokens | $0.005 |
| `offline-json2types` | ~300 tokens | $0.003 |
| `offline-logdoctor` | ~2000 tokens | $0.02 |
| `offline-csvsql` | ~800 tokens | $0.008 |

**Daily:** 10 queries x $0.005 = $0.05  
**Monthly:** ~$1.50  
**Yearly:** ~$18 + hundreds of hours of waiting

---

## 8. Decision Checklist

```
[ ] Need to convert formats?           -> json2types, parse_data, csvsql
[ ] Need to analyze files?             -> file_ops, codebase_map, syncdir
[ ] Need to understand logs?           -> logdoctor
[ ] Need to find/replace/sync?         -> file_ops, syncdir
[ ] Need to generate a template?       -> test_skeleton, json2types, snippets
[ ] Need to explain WHY code is bad?   -> LLM
[ ] Need to write human text?          -> LLM
[ ] Need to synthesize 5 sources?      -> LLM
```

Use the checklist until it becomes automatic.

---

## Weekly Challenge

This week, try to:

1. Replace **5 LLM queries** with offline commands
2. Add **3 snippets** for commands you google most often
3. Configure **1 alias** in your shell for the most frequent command
4. Generate **one README** for a project using `cbm > OVERVIEW.md`

After one week, you will not remember how you worked without this toolkit.
