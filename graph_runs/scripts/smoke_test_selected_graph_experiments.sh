#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAMP="${STAMP:-$(date '+%Y%m%d_%H%M%S')}"
SMOKE_ROOT="${SMOKE_ROOT:-$ROOT/graph_runs/smoke_matrix_$STAMP}"
SUMMARY="$SMOKE_ROOT/summary.tsv"

SEED="${SEED:-0}"
BREAK_STEP="${BREAK_STEP:-1024}"
TARGET_STEP="${TARGET_STEP:-1024}"
BATCH_SIZE="${BATCH_SIZE:-512}"
EVAL_GAP="${EVAL_GAP:-0}"
EVAL_TIMES="${EVAL_TIMES:-1}"
NUM_ENVS="${NUM_ENVS:-1}"
GPU_ID="${GPU_ID:-0}"
CONDA_ENV="${CONDA_ENV:-rm8}"
WANDB="${WANDB:-0}"

EXPERIMENTS=(
  "framework_ablation SERPPO"
  "framework_ablation SERPPO-noPD"
  "framework_ablation SERPPO-noAM"
  "framework_ablation SERPPO-noBO"
  "framework_ablation MAPPO"
  "framework_ablation SERPPO-1DActionSpace"
  "future_observing_critic HO-SERPPO"
  "future_observing_critic HFO-SERPPO"
)

mkdir -p "$SMOKE_ROOT"
printf 'experiment_group\tvariant\tstatus\texit_code\tfinal_step\thas_train_log\thas_checkpoint\trun_dir\n' > "$SUMMARY"

run_one() {
  local group="$1"
  local variant="$2"
  local run_dir="$SMOKE_ROOT/$group/$variant/seed_$SEED"
  local status_file="$run_dir/status.json"
  local exit_code=0

  printf '\n[%s] smoke start %s/%s\n' "$(date -Is)" "$group" "$variant"
  (
    cd "$ROOT" &&
    RUNS_ROOT="$SMOKE_ROOT" \
    CONDA_ENV="$CONDA_ENV" \
    GPU_ID="$GPU_ID" \
    SEEDS="$SEED" \
    BREAK_STEP="$BREAK_STEP" \
    TARGET_STEP="$TARGET_STEP" \
    BATCH_SIZE="$BATCH_SIZE" \
    EVAL_GAP="$EVAL_GAP" \
    EVAL_TIMES="$EVAL_TIMES" \
    NUM_ENVS="$NUM_ENVS" \
    WANDB="$WANDB" \
    FORCE=1 \
    bash run_one_experiment_5seeds.sh "$group" "$variant"
  )
  exit_code=$?

  local status="failed"
  local final_step=""
  local has_train_log="no"
  local has_checkpoint="no"
  if [ -s "$run_dir/train_log.jsonl" ]; then
    has_train_log="yes"
  fi
  if find "$run_dir/checkpoints" -maxdepth 1 -type f -name '*.pth' 2>/dev/null | grep -q .; then
    has_checkpoint="yes"
  fi
  if [ -f "$status_file" ]; then
    status="$(python - "$status_file" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)
print(data.get("status", "unknown"))
PY
)"
    final_step="$(python - "$status_file" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)
print(data.get("final_step", ""))
PY
)"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$group" "$variant" "$status" "$exit_code" "$final_step" "$has_train_log" "$has_checkpoint" "$run_dir" \
    | tee -a "$SUMMARY"
  printf '[%s] smoke done %s/%s status=%s exit=%s\n' "$(date -Is)" "$group" "$variant" "$status" "$exit_code"
  return "$exit_code"
}

overall=0
for item in "${EXPERIMENTS[@]}"; do
  # shellcheck disable=SC2086
  set -- $item
  if ! run_one "$1" "$2"; then
    overall=1
  fi
done

printf '\nSmoke summary: %s\n' "$SUMMARY"
cat "$SUMMARY"
exit "$overall"
