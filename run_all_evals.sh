#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ENV="${CONDA_ENV:-rm8}"
MAX_JOBS="${MAX_JOBS:-1}"
GPU_IDS="${GPU_IDS:-0}"
EVAL_EPISODES="${EVAL_EPISODES:-100}"
NUM_ENVS="${NUM_ENVS:-10}"
SEEDS="${SEEDS:-0 1 2 3 4 5 6 7 8 9}"

IFS=',' read -r -a GPU_ARRAY <<< "$GPU_IDS"

TABLE2_OPPONENTS=(aggressive_bt defensive_bt stationary random_action random_neural HFO-SERPPO)

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

run_eval() {
  local eval_name="$1"
  local policy="$2"
  local opponent="$3"
  local seed="$4"
  local gpu="$5"
  local out_dir="$ROOT/eval_results/$eval_name/$policy/$opponent/seed_$seed"
  mkdir -p "$out_dir"
  if [ -f "$out_dir/status.json" ] && grep -q '"status": "completed"' "$out_dir/status.json"; then
    printf 'skip completed eval %s %s vs %s seed_%s\n' "$eval_name" "$policy" "$opponent" "$seed"
    return 0
  fi
  local cmd="CUDA_VISIBLE_DEVICES=$gpu conda run -n $CONDA_ENV python scripts/rm_evaluate.py --eval-name '$eval_name' --policy '$policy' --opponent '$opponent' --seed '$seed' --eval-episodes '$EVAL_EPISODES' --num-envs '$NUM_ENVS'"
  log_command "$cmd"
  (
    cd "$ROOT" &&
    eval "$cmd" > "$out_dir/stdout.log" 2> "$out_dir/stderr.log"
  )
  local code=$?
  if [ "$code" -ne 0 ]; then
    printf 'failed eval %s %s vs %s seed_%s exit=%s\n' "$eval_name" "$policy" "$opponent" "$seed" "$code" >&2
  fi
  return 0
}

job_index=0
for seed in $SEEDS; do
  for opponent in "${TABLE2_OPPONENTS[@]}"; do
    wait_for_slot
    gpu="${GPU_ARRAY[$((job_index % ${#GPU_ARRAY[@]}))]}"
    run_eval table2_opponent_policy HFO-SERPPO "$opponent" "$seed" "$gpu" &
    job_index=$((job_index + 1))
  done
done

printf 'table3_team_size and table4_arena_layout are intentionally not launched yet: exact disabled-robot and Arena 1/2/3 switches are still marked missing in experiment_registry.yaml.\n'
printf 'MAPPO policy/opponent cells are also not launched until a real RoboMaster MAPPO runner exists.\n'

wait
printf 'all scheduled evaluations finished\n'
