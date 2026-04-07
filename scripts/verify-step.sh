#!/bin/bash
# Verify a single step's result against its verify configuration
# Usage: ./verify-step.sh <step_id> [roadmap.json]
#
# Exit codes:
#   0 - Verification passed
#   1 - Verification failed
#   2 - Step not found or invalid config

STEP_ID="${1:?Usage: verify-step.sh <step_id> [roadmap.json]}"
PLAN_FILE="${2:-roadmap.json}"

if [ ! -f "$PLAN_FILE" ]; then
    echo "[verify-step] Error: $PLAN_FILE not found"
    exit 2
fi

python3 - "$STEP_ID" "$PLAN_FILE" << 'PYEOF'
import json
import sys
import os
import subprocess

step_id = sys.argv[1]
plan_file = sys.argv[2]

with open(plan_file, 'r') as f:
    data = json.load(f)

# Find the step by ID
step = None
for phase in data.get('phases', []):
    for s in phase.get('steps', []):
        if s.get('id') == step_id:
            step = s
            break
    if step:
        break

if not step:
    print(f"[verify-step] Step '{step_id}' not found in {plan_file}")
    sys.exit(2)

verify = step.get('verify')
if not verify:
    print(f"[verify-step] Step '{step_id}' has no verify configuration — skipping")
    sys.exit(0)

verify_type = verify.get('type', '')
expected = verify.get('expected', '')
target = step.get('target', '')

print(f"[verify-step] Verifying step {step_id}: {step.get('action', '')}")
print(f"[verify-step] Type: {verify_type}")

def check_file_exists():
    if os.path.exists(target):
        print(f"[verify-step] PASS: File exists: {target}")
        return True
    else:
        print(f"[verify-step] FAIL: File not found: {target}")
        return False

def check_content_contains():
    if not os.path.exists(target):
        print(f"[verify-step] FAIL: Target file not found: {target}")
        return False
    try:
        with open(target, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        if expected in content:
            print(f"[verify-step] PASS: Found '{expected[:50]}...' in {target}")
            return True
        else:
            print(f"[verify-step] FAIL: '{expected[:50]}...' not found in {target}")
            return False
    except Exception as e:
        print(f"[verify-step] FAIL: Error reading {target}: {e}")
        return False

def check_content_not_contains():
    if not os.path.exists(target):
        print(f"[verify-step] PASS: File doesn't exist, so '{expected[:50]}...' cannot be present")
        return True
    try:
        with open(target, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        if expected not in content:
            print(f"[verify-step] PASS: '{expected[:50]}...' not found (as expected)")
            return True
        else:
            print(f"[verify-step] FAIL: '{expected[:50]}...' still present in {target}")
            return False
    except Exception as e:
        print(f"[verify-step] FAIL: Error reading {target}: {e}")
        return False

def check_command_success():
    try:
        result = subprocess.run(
            target, shell=True, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print(f"[verify-step] PASS: Command succeeded")
            return True
        else:
            print(f"[verify-step] FAIL: Command exited with code {result.returncode}")
            print(f"[verify-step] stderr: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[verify-step] FAIL: Command timed out")
        return False
    except Exception as e:
        print(f"[verify-step] FAIL: Command error: {e}")
        return False

verifiers = {
    'file_exists': check_file_exists,
    'content_contains': check_content_contains,
    'content_not_contains': check_content_not_contains,
    'command_success': check_command_success,
}

verifier = verifiers.get(verify_type)
if not verifier:
    print(f"[verify-step] FAIL: Unknown verify type: {verify_type}")
    sys.exit(2)

success = verifier()
sys.exit(0 if success else 1)
PYEOF
