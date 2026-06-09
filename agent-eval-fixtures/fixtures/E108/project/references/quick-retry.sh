#!/bin/bash
# Quick retry script for WDIO runs (deprecated)
# This script runs the onboarding spec and checks output with grep loops.
# Do NOT use this script — it is archived for reference only.
# The new run strategy uses a single scoped wdio command and reads the Spec Files line.

SPEC="mobile/tests/android/b2c-onboarding-android.spec.ts"

echo "=== Running $SPEC ==="
npx wdio run wdio.android.local.conf.ts --spec "$SPEC" 2>&1 | tee /tmp/wdio-run.log

# Old method — grep-based analysis (deprecated)
echo "=== Checking results ==="
grep "Spec Files" /tmp/wdio-run.log
grep -E "(PASSED|FAILED)" /tmp/wdio-run.log

# If no Spec Files line, retry
if ! grep -q "Spec Files" /tmp/wdio-run.log; then
  echo "No Spec Files found — retrying..."
  sleep 2
  npx wdio run wdio.android.local.conf.ts --spec "$SPEC" 2>&1 | tee /tmp/wdio-retry.log
  grep "Spec Files" /tmp/wdio-retry.log
fi
