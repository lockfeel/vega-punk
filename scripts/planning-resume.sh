#!/usr/bin/env bash
# planning-resume.sh — Report roadmap.json recovery status to session hook.
# Exit 0 always (hook should not block session startup).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROADMAP="$PROJECT_DIR/roadmap.json"

if [ ! -f "$ROADMAP" ]; then
  exit 0
fi

python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    project = d.get("project", "unknown")
    goal = d.get("goal", "not set")
    step = d.get("current_step", "none")
    rate = d.get("metadata", {}).get("completion_rate", "0%")
    print(f"[vega-punk/planning] RESUMING:")
    print(f"  Project: {project}")
    print(f"  Goal: {goal}")
    print(f"  Step: {step} ({rate})")
except Exception:
    pass
' "$ROADMAP" 2>/dev/null || true
