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
WATCH_INTERVAL_VALUE="${WATCH_INTERVAL:-300}"
WATCH_AUTORUN_CODEX="${AUTORUN_CODEX:-0}"

CMD="CONDA_ENV=$WATCH_CONDA_ENV GPU_IDS=$WATCH_GPU_IDS MAX_JOBS=$WATCH_MAX_JOBS BREAK_STEP=$WATCH_BREAK_STEP EVAL_TIMES=$WATCH_EVAL_TIMES EVAL_EPISODES=$WATCH_EVAL_EPISODES WATCH_INTERVAL=$WATCH_INTERVAL_VALUE AUTORUN_CODEX=$WATCH_AUTORUN_CODEX bash scripts/codex_autoresume_monitor.sh"
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
    WATCH_INTERVAL="$WATCH_INTERVAL_VALUE" \
    AUTORUN_CODEX="$WATCH_AUTORUN_CODEX" \
    bash scripts/codex_autoresume_monitor.sh >> "$LOG_DIR/codex_autoresume_monitor.nohup.log" 2>&1
  pid="$(pgrep -f "bash scripts/codex_autoresume_monitor.sh" | tail -n 1 || true)"
else
  nohup env \
    CONDA_ENV="$WATCH_CONDA_ENV" \
    GPU_IDS="$WATCH_GPU_IDS" \
    MAX_JOBS="$WATCH_MAX_JOBS" \
    BREAK_STEP="$WATCH_BREAK_STEP" \
    EVAL_TIMES="$WATCH_EVAL_TIMES" \
    EVAL_EPISODES="$WATCH_EVAL_EPISODES" \
    WATCH_INTERVAL="$WATCH_INTERVAL_VALUE" \
    AUTORUN_CODEX="$WATCH_AUTORUN_CODEX" \
    bash scripts/codex_autoresume_monitor.sh >> "$LOG_DIR/codex_autoresume_monitor.nohup.log" 2>&1 &
  pid="$!"
fi
printf '%s\n' "$pid" > "$LOG_DIR/codex_autoresume_monitor.pid"
printf 'autoresume monitor pid: %s\n' "$pid"
printf 'autoresume log: %s\n' "$LOG_DIR/codex_autoresume_monitor.log"
