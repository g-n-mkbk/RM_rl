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

run_short() {
  local group="$1"
  local variant="$2"
  BREAK_STEP="${SHORT_BREAK_STEP:-15000000}" \
  TARGET_STEP="${SHORT_TARGET_STEP:-16384}" \
  bash "$ROOT/graph_runs/scripts/run_graph_experiment_5seeds.sh" "$group" "$variant"
}

run_full() {
  local group="$1"
  local variant="$2"
  BREAK_STEP="${FULL_BREAK_STEP:-100000000}" \
  TARGET_STEP="${FULL_TARGET_STEP:-65536}" \
  bash "$ROOT/graph_runs/scripts/run_graph_experiment_5seeds.sh" "$group" "$variant"
}

run_short framework_ablation SERPPO || exit $?
run_short framework_ablation SERPPO-noPD || exit $?
run_short framework_ablation SERPPO-noAM || exit $?
run_short framework_ablation SERPPO-noBO || exit $?

# yb3_15 reuses framework_ablation/SERPPO and SERPPO-noPD for critic_loss/value_loss.

run_full future_observing_critic HO-SERPPO || exit $?
run_full future_observing_critic HFO-SERPPO || exit $?

conda run -n "${CONDA_ENV:-rm8}" python "$ROOT/scripts/quality_report.py"
conda run -n "${CONDA_ENV:-rm8}" python "$ROOT/scripts/plot_training_curves.py" --no-title --shade ci95 --min-seeds 3

printf '[%s] all KBS graph experiments finished\n' "$(date -Is)"


