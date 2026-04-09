#!/bin/bash
# Initialize planning files for a new session
# Usage: ./init-session.sh <project-name> "<goal>"

set -e

PROJECT_NAME="${1:-project}"
GOAL="${2:-}"
DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "Initializing planning files for: $PROJECT_NAME"

# Use Python to safely generate JSON with proper escaping
python3 - "$PROJECT_NAME" "$GOAL" "$DATE" << 'PYEOF'
import json, sys

name = sys.argv[1]
goal = sys.argv[2]
date = sys.argv[3]

roadmap = {
    "version": "2.0",
    "project": name,
    "goal": goal,
    "created": date,
    "updated": date,
    "phases": [],
    "current_phase": 0,
    "current_step": "",
    "milestones": [],
    "risks": [],
    "metadata": {"total_steps": 0, "completed_steps": 0, "completion_rate": "0%"}
}

findings = {
    "version": "1.0",
    "project": name,
    "created": date,
    "updated": date,
    "findings": [],
    "research_notes": [],
    "decisions": [],
    "metadata": {"total_findings": 0, "high_priority": 0, "medium_priority": 0, "low_priority": 0}
}

progress = {
    "version": "1.0",
    "project": name,
    "updated": date,
    "entries": [],
    "summary": {"total_tasks": 0, "completed": 0, "in_progress": 0, "pending": 0, "completion_rate": "0%"},
    "blockers": [],
    "completed_milestones": [],
    "next_actions": []
}

vega_punk_dir = os.path.expanduser("~/.vega-punk")
os.makedirs(vega_punk_dir, exist_ok=True)
for fname, data in [("roadmap.json", roadmap), ("findings.json", findings), ("progress.json", progress)]:
    fpath = os.path.join(vega_punk_dir, fname)
    if not os.path.exists(fpath):
        with open(fpath, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        print(f"Created {fname}")
    else:
        print(f"{fname} already exists, skipping")
PYEOF

echo ""
echo "Planning files initialized!"
echo "Files: ~/.vega-punk/roadmap.json (v2.0), ~/.vega-punk/findings.json, ~/.vega-punk/progress.json"
