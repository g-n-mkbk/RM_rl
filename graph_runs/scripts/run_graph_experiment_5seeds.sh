#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="${CONFIG_FILE:-$ROOT/graph_runs/configs/kbs_three_graphs_5seeds.env}"

if [ -f "$CONFIG_FILE" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$CONFIG_FILE"
  set +a
fi

if [ "$#" -lt 2 ]; then
  cat <<'USAGE'
Usage:
  bash graph_runs/scripts/run_graph_experiment_5seeds.sh <experiment_group> <variant>

Common overrides:
  BREAK_STEP=15000000 TARGET_STEP=16384 GPU_ID=0 SEEDS="0 1 2 3 4" WANDB=1

Example:
  BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO
USAGE
  exit 2
fi

GROUP="$1"
VARIANT="$2"
BREAK_STEP="${BREAK_STEP:-${SHORT_BREAK_STEP:-15000000}}"
TARGET_STEP="${TARGET_STEP:-${SHORT_TARGET_STEP:-16384}}"
EVAL_GAP="${EVAL_GAP:-0}"
EVAL_TIMES="${EVAL_TIMES:-20}"
SEEDS="${SEEDS:-0 1 2 3 4}"
GPU_ID="${GPU_ID:-0}"
CONDA_ENV="${CONDA_ENV:-rm8}"
WANDB="${WANDB:-1}"
NUM_ENVS="${NUM_ENVS:-}"
BATCH_SIZE="${BATCH_SIZE:-}"
FORCE="${FORCE:-0}"
RUNS_ROOT="${RUNS_ROOT:-}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

export WANDB_PROJECT="${WANDB_PROJECT:-exbody_test}"
export WANDB_ENTITY="${WANDB_ENTITY:-goodnight-mkbk-northeastern-university}"
export WANDB_GROUP="${WANDB_GROUP:-$GROUP/$VARIANT}"
export WANDB_NOTES="${WANDB_NOTES:-KBS three graph 5-seed rerun}"

mkdir -p "$ROOT/graph_runs/logs" "$ROOT/graph_runs/reports"

cmd="CONDA_ENV=$CONDA_ENV GPU_ID=$GPU_ID SEEDS=\"$SEEDS\" BREAK_STEP=$BREAK_STEP TARGET_STEP=$TARGET_STEP EVAL_GAP=$EVAL_GAP EVAL_TIMES=$EVAL_TIMES WANDB=$WANDB FORCE=$FORCE"
[ -n "$NUM_ENVS" ] && cmd="$cmd NUM_ENVS=$NUM_ENVS"
[ -n "$BATCH_SIZE" ] && cmd="$cmd BATCH_SIZE=$BATCH_SIZE"
[ -n "$RUNS_ROOT" ] && cmd="$cmd RUNS_ROOT='$RUNS_ROOT'"
[ -n "$EXTRA_ARGS" ] && cmd="$cmd EXTRA_ARGS='$EXTRA_ARGS'"
cmd="$cmd bash run_one_experiment_5seeds.sh '$GROUP' '$VARIANT'"
{
  printf '\n## %s\n' "$(date -Is)"
  printf -- '- path: %s\n' "$ROOT"
  printf -- '- command:\n```bash\n%s\n```\n' "$cmd"
} >> "$ROOT/command.md"

printf '[%s] graph experiment start: %s/%s\n' "$(date -Is)" "$GROUP" "$VARIANT"
(
  cd "$ROOT" &&
  eval "$cmd"
) 2>&1 | tee "$ROOT/graph_runs/logs/${GROUP}__${VARIANT}__5seeds.log"
status="${PIPESTATUS[0]}"
printf '[%s] graph experiment done: %s/%s exit=%s\n' "$(date -Is)" "$GROUP" "$VARIANT" "$status"
exit "$status"
