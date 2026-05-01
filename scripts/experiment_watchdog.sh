#!/usr/bin/env bash
set +e
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONDA_ENV="${CONDA_ENV:-rm8}"
GPU_IDS="${GPU_IDS:-0}"
MAX_JOBS="${MAX_JOBS:-1}"
BREAK_STEP="${BREAK_STEP:-100000}"
EVAL_TIMES="${EVAL_TIMES:-5}"
EVAL_EPISODES="${EVAL_EPISODES:-100}"
WATCH_INTERVAL="${WATCH_INTERVAL:-300}"
LOG_DIR="$ROOT/logs"
WATCH_LOG="$LOG_DIR/experiment_watchdog.log"
TRAIN_LOG="$LOG_DIR/watchdog_train.log"
EVAL_LOG="$LOG_DIR/watchdog_eval.log"
REPORT_LOG="$LOG_DIR/watchdog_report_plot.log"
LOCK_FILE="$ROOT/.experiment_watchdog.lock"

mkdir -p "$LOG_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf '[%s] another watchdog is already running\n' "$(date -Is)" | tee -a "$WATCH_LOG"
  exit 0
fi

log() {
  printf '[%s] %s\n' "$(date -Is)" "$*" | tee -a "$WATCH_LOG"
}

trap 'code=$?; if [ "$code" -ne 0 ]; then printf "[%s] watchdog exiting unexpectedly with code %s at line %s\n" "$(date -Is)" "$code" "$LINENO" | tee -a "$WATCH_LOG"; fi' EXIT

append_command_log() {
  local command="$1"
  {
    printf '\n## %s\n' "$(date -Is)"
    printf -- '- path: %s\n' "$ROOT"
    printf -- '- command:\n```bash\n%s\n```\n' "$command"
  } >> "$ROOT/command.md"
}

training_active() {
  pgrep -f "bash run_all_10seeds\\.sh" >/dev/null 2>&1 ||
    pgrep -f "python scripts/rm_experiment\\.py" >/dev/null 2>&1
}

training_complete() {
  python3 - "$ROOT" "$BREAK_STEP" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
break_step = int(sys.argv[2])
runs = [
    ("framework_ablation", "SERPPO"),
    ("framework_ablation", "SERPPO-noPD"),
    ("framework_ablation", "SERPPO-noAM"),
    ("framework_ablation", "SERPPO-noBO"),
    ("obstacle_representation", "SERPPO-M"),
    ("actor_critic_parameterization", "partially_shared_actor_critic"),
    ("recurrent_actor", "SERPPO-LSTM"),
    ("recurrent_actor", "SERPPO-GRU"),
    ("future_observing_critic", "HFO-SERPPO"),
]
missing = []
for group, variant in runs:
    for seed in range(10):
        status_path = root / "runs_multi_seed" / group / variant / f"seed_{seed}" / "status.json"
        if not status_path.exists():
            missing.append(f"{group}/{variant}/seed_{seed}:missing")
            continue
        try:
            status = json.loads(status_path.read_text())
        except Exception:
            missing.append(f"{group}/{variant}/seed_{seed}:bad-status")
            continue
        if status.get("status") != "completed" or int(status.get("final_step") or 0) < break_step:
            missing.append(f"{group}/{variant}/seed_{seed}:{status.get('status')}")
if missing:
    print("\n".join(missing[:20]))
    raise SystemExit(1)
PY
}

eval_active() {
  pgrep -f "bash run_all_evals\\.sh" >/dev/null 2>&1 ||
    pgrep -f "python scripts/rm_evaluate\\.py" >/dev/null 2>&1
}

run_training_once() {
  local cmd="CONDA_ENV=$CONDA_ENV GPU_IDS=$GPU_IDS MAX_JOBS=$MAX_JOBS BREAK_STEP=$BREAK_STEP EVAL_TIMES=$EVAL_TIMES bash run_all_10seeds.sh"
  log "starting training batch: $cmd"
  append_command_log "$cmd"
  (cd "$ROOT" && eval "$cmd" >> "$TRAIN_LOG" 2>&1)
  log "training batch exited with code $?"
}

run_eval_once() {
  local cmd="CONDA_ENV=$CONDA_ENV GPU_IDS=$GPU_IDS MAX_JOBS=$MAX_JOBS EVAL_EPISODES=$EVAL_EPISODES bash run_all_evals.sh"
  log "starting evaluation batch: $cmd"
  append_command_log "$cmd"
  (cd "$ROOT" && eval "$cmd" >> "$EVAL_LOG" 2>&1)
  log "evaluation batch exited with code $?"
}

run_reports_and_plots() {
  local cmd1="conda run -n $CONDA_ENV python scripts/quality_report.py"
  local cmd2="conda run -n $CONDA_ENV python scripts/plot_training_curves.py"
  append_command_log "$cmd1"
  append_command_log "$cmd2"
  log "building quality report"
  (cd "$ROOT" && eval "$cmd1" >> "$REPORT_LOG" 2>&1)
  log "building training plots"
  (cd "$ROOT" && eval "$cmd2" >> "$REPORT_LOG" 2>&1)
}

log "watchdog started; break_step=$BREAK_STEP eval_times=$EVAL_TIMES eval_episodes=$EVAL_EPISODES"
while true; do
  if training_complete >> "$WATCH_LOG" 2>&1; then
    log "training complete"
    if ! eval_active; then
      run_eval_once
    fi
    run_reports_and_plots
    log "all stages launched/completed; watchdog exiting"
    exit 0
  fi

  if training_active; then
    log "training is active; sleeping $WATCH_INTERVAL seconds"
    sleep "$WATCH_INTERVAL"
  else
    log "training not active; resuming batch"
    run_training_once
    sleep 10
  fi
done
