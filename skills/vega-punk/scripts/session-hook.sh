#!/usr/bin/env bash
# vega-punk session state recovery hook.
# Reads .vega-punk-state.json and announces the current state.
# Safe against missing file, invalid JSON, and empty state.
set -euo pipefail

STATE_FILE=".vega-punk-state.json"

if [ ! -f "$STATE_FILE" ]; then
  echo "[vega-punk] Ready. What shall we build?"
  exit 0
fi

STATE=""
ERROR=""

# Try Node.js first (always available in Claude Code sessions)
if command -v node &>/dev/null; then
  ERROR=$(node -e "
    try {
      const fs = require('fs');
      const data = JSON.parse(fs.readFileSync('$STATE_FILE', 'utf8'));
      const state = data.state || '';
      if (state) { console.log(state); process.exit(0); }
      process.exit(1);
    } catch (e) {
      console.error('Error: ' + e.message);
      process.exit(1);
    }
  " 2>&1) && STATE="$ERROR" && ERROR=""
fi

# Fallback to python3 if node failed
if [ -z "$STATE" ] && command -v python3 &>/dev/null; then
  ERROR=$(python3 -c "
import json, sys
try:
    with open('$STATE_FILE') as f:
        data = json.load(f)
    state = data.get('state', '')
    if state:
        print(state, end='')
        sys.exit(0)
    sys.exit(1)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1) && STATE="$ERROR" && ERROR=""
fi

# If both parsers failed or state is empty
if [ -z "$STATE" ]; then
  echo "[vega-punk] Warning: could not read state file ($ERROR)"
  echo "[vega-punk] Starting fresh. What shall we build?"
  exit 0
fi

if [ "$STATE" = "DONE" ]; then
  echo "[vega-punk] Ready. What shall we build?"
else
  echo "[vega-punk] Resuming from $STATE. Continue working or say 'new task'."
fi

# Discover all registered skills on every session start
if [ -f "$(dirname "$0")/discover-skills.sh" ]; then
  skill_count=$(bash "$(dirname "$0")/discover-skills.sh" 2>/dev/null | grep -c '"name"' || echo "0")
  echo "[vega-punk] $skill_count skills discovered and available for routing."
fi
