#!/usr/bin/env python3
"""CI gate: require a change record covering every changed repository path."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base, head = sys.argv[1:3]

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).splitlines()

changed = set(git("diff", "--name-only", f"{base}...{head}"))
if not changed:
    changed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", head))
record_prefix = "data/36os/change-records/"
record_paths = {p for p in changed if p.startswith(record_prefix) and p.endswith(".json")}
records = []
for path in sorted(record_paths):
    records.append(json.loads((ROOT/path).read_text(encoding="utf-8")))

if not records:
    print("ERROR: No Change Record found. Add data/36os/change-records/CHG-*.json.")
    sys.exit(1)

goals = {x["id"] for x in json.loads((ROOT/"data/36os/goals.json").read_text())["goals"]}
decisions = {x["id"] for x in json.loads((ROOT/"data/36os/decisions.json").read_text())["decisions"]}
covered = set()
for record in records:
    required = ["change_id","summary","actor","goal_ids","decision_ids","touched_files","risk","approval_status"]
    missing = [key for key in required if key not in record]
    if missing:
        raise SystemExit(f"ERROR: {record.get('change_id','unknown')} missing fields: {missing}")
    if not record["goal_ids"] or not set(record["goal_ids"]).issubset(goals):
        raise SystemExit(f"ERROR: {record['change_id']} references missing/empty goal IDs")
    if not record["decision_ids"] or not set(record["decision_ids"]).issubset(decisions):
        raise SystemExit(f"ERROR: {record['change_id']} references missing/empty decision IDs")
    covered.update(record["touched_files"])

non_record_changes = changed - record_paths
uncovered = non_record_changes - covered
stale = covered - non_record_changes
if uncovered:
    raise SystemExit("ERROR: Changed paths without traceability: " + ", ".join(sorted(uncovered)))
if stale:
    raise SystemExit("ERROR: Change Record lists paths not changed in this PR/push: " + ", ".join(sorted(stale)))
print(f"36OS governance passed: {len(non_record_changes)} changed paths covered by {len(records)} change record(s).")
