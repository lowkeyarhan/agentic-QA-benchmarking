#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RUN_PREFIX="${BENCHMARK_COMPARE_PREFIX:-compare-local-prod-$(date +%Y%m%d-%H%M%S)}"
LOCAL_BINARY="${BENCHMARK_LOCAL_BINARY:-/Users/lowkeyarhan/Documents/supatest/cli/dist/index.js}"
PROD_BINARY="${BENCHMARK_PROD_BINARY:-/opt/homebrew/lib/node_modules/@supatest/cli/dist/index.js}"
EVAL_IDS="${BENCHMARK_EVAL_IDS:-E1,E2,E12,E4,E70}"

echo "Cleaning benchmark results and runs..."
rm -rf "$ROOT/results"/* "$ROOT/runs"/*

echo "Local binary:  $LOCAL_BINARY"
echo "Prod binary:   $PROD_BINARY"
echo "Eval suites:   $EVAL_IDS"
echo "Run prefix:    $RUN_PREFIX"
echo

common_env=(
  BENCHMARK_ENV_FILE_OVERRIDE=0
  BENCHMARK_AGENTS=supatest:premium
  BENCHMARK_DISABLE_JUDGE_PREFLIGHT=1
  DEEPEVAL_GEMINI_MODEL=gemini-3.1-flash-lite
  BENCHMARK_EVAL_IDS="$EVAL_IDS"
  BENCHMARK_EVAL_LIMIT=all
  BENCHMARK_EVAL_OFFSET=0
  BENCHMARK_PARALLELISM=4
  BENCHMARK_DISABLE_PREFLIGHT=1
)

run_one() {
  local label="$1"
  local binary="$2"
  local run_id="${RUN_PREFIX}-${label}"

  echo "=== Starting ${label} run (${run_id}) ==="
  env \
    "${common_env[@]}" \
    BENCHMARK_RUN_ID="$run_id" \
    BENCHMARK_SUPATEST_BINARY="$binary" \
    ./run_benchmark.py
  echo "=== Finished ${label} run ==="
  echo
}

run_one local "$LOCAL_BINARY"
run_one prod "$PROD_BINARY"

python3 "$ROOT/scripts/compare-local-prod-results.py" \
  "$ROOT/results/${RUN_PREFIX}-local" \
  "$ROOT/results/${RUN_PREFIX}-prod"
