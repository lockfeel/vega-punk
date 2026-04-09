#!/bin/bash
# Check if all steps in roadmap.json are complete
# Always exits 0 — uses stdout for status reporting
# Usage: ./check-complete.sh [roadmap.json]

PLAN_FILE="${1:-$HOME/.vega-punk/roadmap.json}"

if [ ! -f "$PLAN_FILE" ]; then
    echo "[planning-with-json] No roadmap.json found — no active planning session."
    exit 0
fi

# Pass PLAN_FILE to Python via sys.argv
python3 - "$PLAN_FILE" << 'PYEOF'
import json
import sys
import os

plan_file = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.vega-punk/roadmap.json")

if not os.path.exists(plan_file):
    print("[planning-with-json] No roadmap.json found.")
    sys.exit(0)

try:
    with open(plan_file, 'r') as f:
        data = json.load(f)

    total = 0
    complete = 0
    in_progress = 0
    pending = 0
    failed = 0

    for phase in data.get('phases', []):
        for step in phase.get('steps', []):
            total += 1
            status = step.get('status', 'pending')
            if status == 'complete':
                complete += 1
            elif status == 'in_progress':
                in_progress += 1
            elif status == 'failed':
                failed += 1
            else:
                pending += 1

    current_step = data.get('current_step', 'N/A')
    completion_rate = data.get('metadata', {}).get('completion_rate', '0%')

    print(f"[planning-with-json] Progress: {complete}/{total} steps complete ({completion_rate})")
    print(f"[planning-with-json] Current step: {current_step}")

    if failed > 0:
        print(f"[planning-with-json] {failed} step(s) failed — needs attention")

    if complete == total and total > 0:
        print("[planning-with-json] ALL STEPS COMPLETE!")
    elif in_progress > 0:
        print("[planning-with-json] Task in progress...")
    else:
        print("[planning-with-json] Task pending")

except (json.JSONDecodeError, KeyError) as e:
    print(f"[planning-with-json] Error parsing roadmap.json: {e}")
    sys.exit(0)
PYEOF
