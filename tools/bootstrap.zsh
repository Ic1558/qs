#!/usr/bin/env zsh
# Universal QS Engine Production Bootstrap
# Logic: Cleanup -> Venv -> Test -> Start

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_DIR="$(cd "$REPO_ROOT/../.." && pwd)"
VENV_PATH="${VENV_PATH:-$ROOT_DIR/.venv_estimator}"
PYTHON_BIN="$VENV_PATH/bin/python3"
PORT="${PORT:-7084}"
NO_START="${NO_START:-0}"
SKIP_TESTS="${SKIP_TESTS:-0}"
LUKA_RUNTIME_ROOT="${LUKA_RUNTIME_ROOT:-$HOME/0luka_runtime}"

echo "--- [1/4] Cleaning environment ---"
mkdir -p "$REPO_ROOT/tmp" "$REPO_ROOT/outputs/projects" "$LUKA_RUNTIME_ROOT/logs"
find "$REPO_ROOT/tmp" -mindepth 1 -maxdepth 1 -type d -name 'job_*' -exec rm -rf {} +
rm -rf "$REPO_ROOT/tmp/jobs" 2>/dev/null || true
mkdir -p "$REPO_ROOT/tmp/jobs"

echo "--- [2/4] Ensuring Virtual Environment ---"
if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Creating new venv at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
fi

echo "Installing dependencies from pyproject.toml..."
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -e "${REPO_ROOT}[low_cost]"

export PYTHONPATH="$REPO_ROOT/src"
export LUKA_RUNTIME_ROOT

if [[ "$SKIP_TESTS" != "1" ]]; then
    echo "--- [3/4] Running Quality Gates ---"
    "$PYTHON_BIN" -m pytest -q "$REPO_ROOT/tests"
else
    echo "--- [3/4] Skipping Quality Gates (SKIP_TESTS=1) ---"
fi

echo "--- [4/4] Starting API Service ---"
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Error: Port $PORT is already in use."
    exit 1
fi

if [[ "$NO_START" == "1" ]]; then
    echo "Bootstrap complete. Service start skipped (NO_START=1)."
    exit 0
fi

echo "Service starting on http://127.0.0.1:$PORT"
# Launching in foreground for bootstrap verification.
# Production steady-state should be managed by launchd.
cd "$REPO_ROOT"
exec "$PYTHON_BIN" -m universal_qs_engine.cli serve-health --port "$PORT"
