#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNS_ROOT="${RUNS_ROOT:-$ROOT/runs_multi_seed}"

if [ "$#" -lt 2 ]; then
  cat <<'USAGE'
Usage:
  bash run_one_experiment_5seeds.sh <experiment_group> <variant>

Environment variables:
  CONDA_ENV=rm8                 Conda environment name
  GPU_ID=0                      GPU id for this experiment
  SEEDS="0 1 2 3 4"             Seeds to run sequentially
  BREAK_STEP=15000000           Training environment-step budget; omit to use registry default
  TARGET_STEP=16384             Rollout size per update; omit to use registry default
  BATCH_SIZE=4096               PPO batch size override; omit to use registry default
  EVAL_TIMES=20                 In-training eval episodes per eval point
  EVAL_GAP=0                    Seconds between evals; 0 means every PPO iteration
  NUM_ENVS=10                   Parallel env count override
  WANDB=0                       Set to 1 to pass --wandb
  DETERMINISTIC_TORCH=0         Set to 1 to pass --deterministic-torch
  FORCE=0                       Set to 1 to pass --force
  EXTRA_ARGS=""                 Extra args appended to scripts/rm_experiment.py

Examples:
  BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 bash run_one_experiment_5seeds.sh framework_ablation SERPPO
  BREAK_STEP=100000000 TARGET_STEP=65536 EVAL_GAP=0 bash run_one_experiment_5seeds.sh future_observing_critic HFO-SERPPO
USAGE
  exit 2
fi

GROUP="$1"
VARIANT="$2"
CONDA_ENV="${CONDA_ENV:-rm8}"
GPU_ID="${GPU_ID:-0}"
SEEDS="${SEEDS:-0 1 2 3 4}"
BREAK_STEP="${BREAK_STEP:-}"
TARGET_STEP="${TARGET_STEP:-}"
BATCH_SIZE="${BATCH_SIZE:-}"
EVAL_TIMES="${EVAL_TIMES:-}"
EVAL_GAP="${EVAL_GAP:-}"
NUM_ENVS="${NUM_ENVS:-}"
WANDB="${WANDB:-0}"
DETERMINISTIC_TORCH="${DETERMINISTIC_TORCH:-0}"
FORCE="${FORCE:-0}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

log_command() {
  local command="$1"
  {
    printf '\n## %s\n' "$(date -Is)"
    printf -- '- path: %s\n' "$ROOT"
    printf -- '- command:\n```bash\n%s\n```\n' "$command"
  } >> "$ROOT/command.md"
}

for seed in $SEEDS; do
  run_dir="$RUNS_ROOT/$GROUP/$VARIANT/seed_$seed"
  mkdir -p "$run_dir"
  cmd="CUDA_VISIBLE_DEVICES=$GPU_ID PYTHONUNBUFFERED=1 conda run --no-capture-output -n $CONDA_ENV python -u scripts/rm_experiment.py --experiment-group '$GROUP' --variant '$VARIANT' --seed '$seed'"
  [ -n "$BREAK_STEP" ] && cmd="$cmd --break-step '$BREAK_STEP'"
  [ -n "$TARGET_STEP" ] && cmd="$cmd --target-step '$TARGET_STEP'"
  [ -n "$BATCH_SIZE" ] && cmd="$cmd --batch-size '$BATCH_SIZE'"
  [ -n "$EVAL_TIMES" ] && cmd="$cmd --eval-times '$EVAL_TIMES'"
  [ -n "$EVAL_GAP" ] && cmd="$cmd --eval-gap '$EVAL_GAP'"
  [ -n "$NUM_ENVS" ] && cmd="$cmd --num-envs '$NUM_ENVS'"
  [ "$WANDB" = "1" ] && cmd="$cmd --wandb"
  [ "$DETERMINISTIC_TORCH" = "1" ] && cmd="$cmd --deterministic-torch"
  [ "$FORCE" = "1" ] && cmd="$cmd --force"
  [ -n "$EXTRA_ARGS" ] && cmd="$cmd $EXTRA_ARGS"

  log_command "$cmd"
  printf '[%s] start %s/%s seed_%s on GPU %s\n' "$(date -Is)" "$GROUP" "$VARIANT" "$seed" "$GPU_ID"
  (
    cd "$ROOT" &&
    eval "$cmd" > >(tee "$run_dir/stdout.log") 2> >(tee "$run_dir/stderr.log" >&2)
  )
  code=$?
  if [ "$code" -ne 0 ]; then
    printf '[%s] failed %s/%s seed_%s exit=%s; see %s\n' "$(date -Is)" "$GROUP" "$VARIANT" "$seed" "$code" "$run_dir/stderr.log" >&2
    exit "$code"
  fi
  printf '[%s] done %s/%s seed_%s\n' "$(date -Is)" "$GROUP" "$VARIANT" "$seed"
done

printf '[%s] all requested seeds finished for %s/%s\n' "$(date -Is)" "$GROUP" "$VARIANT"
