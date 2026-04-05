#!/bin/bash
# vega-punk dependency installer
# Installs all required skills for vega-punk workflow

set -e

SKILLS=(
  "planning-with-json"
  "executing-plans"
  "subagent-driven-development"
  "systematic-debugging"
  "test-driven-development"
  "verification-before-completion"
  "requesting-code-review"
)

echo "[vega-punk] Checking dependencies..."

# Detect platform
if command -v openclaw &> /dev/null; then
  PLATFORM="openclaw"
  CMD="openclaw skills install"
elif command -v npx &> /dev/null; then
  PLATFORM="claude-code"
  CMD="npx skills install"
else
  echo "[vega-punk] ERROR: No supported platform found (openclaw or npx)"
  exit 1
fi

echo "[vega-punk] Platform: $PLATFORM"

for skill in "${SKILLS[@]}"; do
  echo "[vega-punk] Installing $skill..."
  $CMD "$skill" || echo "[vega-punk] Warning: Failed to install $skill (may already be installed)"
done

echo "[vega-punk] All dependencies installed."
