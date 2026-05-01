#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

WATCH_CONDA_ENV="${CONDA_ENV:-rm8}"
WATCH_GPU_IDS="${GPU_IDS:-0}"
WATCH_MAX_JOBS="${MAX_JOBS:-1}"
WATCH_BREAK_STEP="${BREAK_STEP:-100000}"
WATCH_EVAL_TIMES="${EVAL_TIMES:-5}"
WATCH_EVAL_EPISODES="${EVAL_EPISODES:-100}"
WATCH_WATCH_INTERVAL="${WATCH_INTERVAL:-300}"
CMD="CONDA_ENV=$WATCH_CONDA_ENV GPU_IDS=$WATCH_GPU_IDS MAX_JOBS=$WATCH_MAX_JOBS BREAK_STEP=$WATCH_BREAK_STEP EVAL_TIMES=$WATCH_EVAL_TIMES EVAL_EPISODES=$WATCH_EVAL_EPISODES WATCH_INTERVAL=$WATCH_WATCH_INTERVAL bash scripts/experiment_watchdog.sh"
{
  printf '\n## %s\n' "$(date -Is)"
  printf -- '- path: %s\n' "$ROOT"
  printf -- '- command:\n```bash\n%s\n```\n' "$CMD"
} >> "$ROOT/command.md"

cd "$ROOT"
if command -v setsid >/dev/null 2>&1; then
  setsid -f env \
    CONDA_ENV="$WATCH_CONDA_ENV" \
    GPU_IDS="$WATCH_GPU_IDS" \
    MAX_JOBS="$WATCH_MAX_JOBS" \
    BREAK_STEP="$WATCH_BREAK_STEP" \
    EVAL_TIMES="$WATCH_EVAL_TIMES" \
    EVAL_EPISODES="$WATCH_EVAL_EPISODES" \
    WATCH_INTERVAL="$WATCH_WATCH_INTERVAL" \
    bash scripts/experiment_watchdog.sh >> "$LOG_DIR/experiment_watchdog.nohup.log" 2>&1
  pid="$(pgrep -f "bash scripts/experiment_watchdog.sh" | tail -n 1 || true)"
else
  nohup env \
    CONDA_ENV="$WATCH_CONDA_ENV" \
    GPU_IDS="$WATCH_GPU_IDS" \
    MAX_JOBS="$WATCH_MAX_JOBS" \
    BREAK_STEP="$WATCH_BREAK_STEP" \
    EVAL_TIMES="$WATCH_EVAL_TIMES" \
    EVAL_EPISODES="$WATCH_EVAL_EPISODES" \
    WATCH_INTERVAL="$WATCH_WATCH_INTERVAL" \
    bash scripts/experiment_watchdog.sh >> "$LOG_DIR/experiment_watchdog.nohup.log" 2>&1 &
  pid="$!"
fi
printf '%s\n' "$pid" > "$LOG_DIR/experiment_watchdog.pid"
printf 'watchdog pid: %s\n' "$pid"
printf 'watchdog log: %s\n' "$LOG_DIR/experiment_watchdog.log"
