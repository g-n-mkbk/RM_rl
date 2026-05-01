#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/codex_autoresume_monitor.log"
PID_FILE="$LOG_DIR/codex_autoresume_monitor.pid"
RESUME_SH="$LOG_DIR/codex_resume_command.sh"
LOCK_FILE="$ROOT/.codex_autoresume_monitor.lock"

CONDA_ENV="${CONDA_ENV:-rm8}"
GPU_IDS="${GPU_IDS:-0}"
MAX_JOBS="${MAX_JOBS:-1}"
BREAK_STEP="${BREAK_STEP:-100000}"
EVAL_TIMES="${EVAL_TIMES:-5}"
EVAL_EPISODES="${EVAL_EPISODES:-100}"
WATCH_INTERVAL="${WATCH_INTERVAL:-300}"
AUTORUN_CODEX="${AUTORUN_CODEX:-0}"
CODEX_PROMPT_FILE="${CODEX_PROMPT_FILE:-$ROOT/docs/codex_resume_prompt.md}"

mkdir -p "$LOG_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf '[%s] another codex autoresume monitor is already running\n' "$(date -Is)" | tee -a "$LOG_FILE"
  exit 0
fi

printf '%s\n' "$$" > "$PID_FILE"

log() {
  printf '[%s] %s\n' "$(date -Is)" "$*" | tee -a "$LOG_FILE"
}

append_command_log() {
  local command="$1"
  {
    printf '\n## %s\n' "$(date -Is)"
    printf -- '- path: %s\n' "$ROOT"
    printf -- '- command:\n```bash\n%s\n```\n' "$command"
  } >> "$ROOT/command.md"
}

write_resume_command() {
  cat > "$RESUME_SH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
export CODEX_HOME="\${CODEX_HOME:-$HOME/.codex_dh}"
codex-dh run "\$(cat "$CODEX_PROMPT_FILE")"
EOF
  chmod +x "$RESUME_SH"
}

watchdog_active() {
  pgrep -f "bash scripts/experiment_watchdog.sh" >/dev/null 2>&1
}

task_complete() {
  [ -s "$ROOT/data_quality_report.md" ] &&
  [ -s "$ROOT/run_inventory.csv" ] &&
  [ -s "$ROOT/eval_inventory.csv" ] &&
  [ -s "$ROOT/plots_draft/training_curves/manifest.txt" ]
}

start_watchdog() {
  local cmd="CONDA_ENV=$CONDA_ENV GPU_IDS=$GPU_IDS MAX_JOBS=$MAX_JOBS BREAK_STEP=$BREAK_STEP EVAL_TIMES=$EVAL_TIMES EVAL_EPISODES=$EVAL_EPISODES WATCH_INTERVAL=$WATCH_INTERVAL bash scripts/start_experiment_watchdog.sh"
  log "watchdog missing; starting: $cmd"
  append_command_log "$cmd"
  (cd "$ROOT" && eval "$cmd" >> "$LOG_FILE" 2>&1)
}

maybe_run_codex_resume() {
  if [ "$AUTORUN_CODEX" != "1" ]; then
    return 0
  fi
  if pgrep -f "codex-dh run .*codex_resume_prompt" >/dev/null 2>&1; then
    return 0
  fi
  local cmd="CODEX_HOME=$HOME/.codex_dh codex-dh run \"\$(cat $CODEX_PROMPT_FILE)\""
  log "AUTORUN_CODEX=1; launching resume command"
  append_command_log "$cmd"
  (cd "$ROOT" && CODEX_HOME="$HOME/.codex_dh" codex-dh run "$(cat "$CODEX_PROMPT_FILE")" >> "$LOG_DIR/codex_autorun.log" 2>&1 &)
}

write_resume_command
log "autoresume monitor started; interval=$WATCH_INTERVAL break_step=$BREAK_STEP autorun_codex=$AUTORUN_CODEX"
log "manual resume command written to $RESUME_SH"

while true; do
  if task_complete; then
    log "deliverables detected; monitor exiting"
    exit 0
  fi
  if watchdog_active; then
    log "experiment watchdog is active"
  else
    start_watchdog
    maybe_run_codex_resume
  fi
  sleep "$WATCH_INTERVAL"
done
