#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ENV="${CONDA_ENV:-rm8}"
MAX_JOBS="${MAX_JOBS:-1}"
GPU_IDS="${GPU_IDS:-0}"
BREAK_STEP="${BREAK_STEP:-}"
TARGET_STEP="${TARGET_STEP:-}"
BATCH_SIZE="${BATCH_SIZE:-}"
EVAL_TIMES="${EVAL_TIMES:-}"
EVAL_GAP="${EVAL_GAP:-}"
NUM_ENVS="${NUM_ENVS:-}"
SEEDS="${SEEDS:-0 1 2 3 4 5 6 7 8 9}"

IFS=',' read -r -a GPU_ARRAY <<< "$GPU_IDS"

RUNS=(
  "framework_ablation SERPPO"
  "framework_ablation SERPPO-noPD"
  "framework_ablation SERPPO-noAM"
  "framework_ablation SERPPO-noBO"
  "obstacle_representation SERPPO-M"
  "actor_critic_parameterization partially_shared_actor_critic"
  "recurrent_actor SERPPO-LSTM"
  "recurrent_actor SERPPO-GRU"
  "future_observing_critic HFO-SERPPO"
)

log_command() {
  local command="$1"
  {
    printf '\n## %s\n' "$(date -Is)"
    printf -- '- path: %s\n' "$ROOT"
    printf -- '- command:\n```bash\n%s\n```\n' "$command"
  } >> "$ROOT/command.md"
}

wait_for_slot() {
  while [ "$(jobs -rp | wc -l)" -ge "$MAX_JOBS" ]; do
    sleep 5
  done
}

is_completed_run() {
  local group="$1"
  local variant="$2"
  local seed="$3"
  local run_dir="$ROOT/runs_multi_seed/$group/$variant/seed_$seed"
  local status_file="$run_dir/status.json"
  local expected_step="${BREAK_STEP:-100000000}"
  local final_step=""
  if [ -f "$status_file" ]; then
    final_step="$(grep -m1 '"final_step"' "$status_file" | sed -E 's/.*: ([0-9]+|null).*/\1/; s/null/0/' || printf '0')"
  fi

  if [ -f "$status_file" ] &&
     grep -q '"status": "completed"' "$status_file" &&
     [ "${final_step:-0}" -ge "$expected_step" ] &&
     [ -s "$run_dir/train_log.jsonl" ] &&
     compgen -G "$run_dir/checkpoints/*.pth" > /dev/null; then
    return 0
  fi
  return 1
}

run_one() {
  local group="$1"
  local variant="$2"
  local seed="$3"
  local gpu="$4"
  local run_dir="$ROOT/runs_multi_seed/$group/$variant/seed_$seed"

  if is_completed_run "$group" "$variant" "$seed"; then
    printf 'skip completed %s/%s seed_%s\n' "$group" "$variant" "$seed"
    return 0
  fi

  mkdir -p "$run_dir"
  local cmd="CUDA_VISIBLE_DEVICES=$gpu conda run -n $CONDA_ENV python scripts/rm_experiment.py --experiment-group '$group' --variant '$variant' --seed '$seed'"
  [ -n "$BREAK_STEP" ] && cmd="$cmd --break-step '$BREAK_STEP'"
  [ -n "$TARGET_STEP" ] && cmd="$cmd --target-step '$TARGET_STEP'"
  [ -n "$BATCH_SIZE" ] && cmd="$cmd --batch-size '$BATCH_SIZE'"
  [ -n "$EVAL_TIMES" ] && cmd="$cmd --eval-times '$EVAL_TIMES'"
  [ -n "$EVAL_GAP" ] && cmd="$cmd --eval-gap '$EVAL_GAP'"
  [ -n "$NUM_ENVS" ] && cmd="$cmd --num-envs '$NUM_ENVS'"

  log_command "$cmd"
  printf 'start %s/%s seed_%s on GPU %s\n' "$group" "$variant" "$seed" "$gpu"
  (
    cd "$ROOT" &&
    eval "$cmd" > "$run_dir/stdout.log" 2> "$run_dir/stderr.log"
  )
  local code=$?
  if [ "$code" -ne 0 ]; then
    printf 'failed %s/%s seed_%s exit=%s\n' "$group" "$variant" "$seed" "$code" >&2
  else
    printf 'done %s/%s seed_%s\n' "$group" "$variant" "$seed"
  fi
  return 0
}

job_index=0
for item in "${RUNS[@]}"; do
  group="${item%% *}"
  variant="${item#* }"
  for seed in $SEEDS; do
    if is_completed_run "$group" "$variant" "$seed"; then
      printf 'skip completed %s/%s seed_%s\n' "$group" "$variant" "$seed"
      continue
    fi
    wait_for_slot
    gpu="${GPU_ARRAY[$((job_index % ${#GPU_ARRAY[@]}))]}"
    run_one "$group" "$variant" "$seed" "$gpu" &
    job_index=$((job_index + 1))
  done
done

wait
printf 'all scheduled runs finished\n'
