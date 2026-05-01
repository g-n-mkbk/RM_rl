# Experiment Readiness Report

## Scope

This report covers the current code-to-paper experiment mapping for the HFO-SERPPO paper experiments. No full training, evaluation sweep, final plotting, image beautification, or LaTeX body edits were performed.

Update note for the current KBS three-graph rerun: the selected graph experiments have since been wired into `graph_runs/` and smoke-tested. For server execution, use `docs/kbs_server_migration_and_graph_runs.md` and `graph_runs/configs/experiments.tsv` as the active source of truth.

## Project Structure And Entrypoints

### Training Entrypoints

- `scripts/demo.py`: current RoboMaster PPO-style training demo. It builds `Arguments`, `MultiEnvDiscretePPO`, `VecEnvironments`, then calls `elegantrl_dq.train.run.train_and_evaluate`.
- `elegantrl_dq/train/run.py`: main current training loop for the RoboMaster multi-env PPO path.
- `scripts/demo_dq.py` and `elegantrl/train/demo_old.py`: older/legacy examples around `elegantrl`, DQN, and generic ElegantRL flows.
- `scripts/rm_experiment.py`: new single-run CLI for paper experiment runs.

### Evaluation Entrypoints

- `elegantrl_dq/agents/AgentPPO.py::MultiEnvDiscretePPO.evaluate`: current in-training evaluation implementation.
- `elegantrl_dq/train/evaluator.py`: older evaluator class used by alternate evaluation paths.
- `scripts/rm_evaluate.py`: new single-evaluation CLI for trained HFO/SERPPO-style checkpoints.

### Current Known Commands

- README documents environment installation via `pip install -e .` under `robomaster2D`.
- Existing `command.md` shows prior project use of `conda run -n rm8 ...`, including editable installs for `.` and `./robomaster2D`, plus `conda run -n rm8 python scripts/demo.py` style exploration.
- The active virtual environment was confirmed as `rm8`. Python checks, smoke training, smoke evaluation, and quality-report generation were run through `conda run -n rm8`.

### Checkpoints

- Existing code saves checkpoints under `./results/models/{cwd}` relative to the launch directory.
- Existing checkpoint filenames include `actor.pth`, `actor_best.pth`, `actor_step:{step}.pth`, `actor_step:{step}_best.pth`, `critic.pth`, `critic_step:{step}.pth`, and optimizer `.pth` files.
- Existing repository data contains old checkpoints under `scripts/results/models/2023-01-04_10-22-01/`.
- New runs are configured to save under `runs_multi_seed/{group}/{variant}/seed_{seed}/checkpoints/`.

### Logs

- Historical/demo code logs mainly through stdout and optional Weights & Biases under `./results/wandb_logs`; no TensorBoard event file is used by the current paper runner.
- The paper run layout writes `config.yaml`, `train_log.jsonl`, `eval_log.jsonl`, `stdout.log`, `stderr.log`, `git_commit.txt`, and `status.json`; local JSONL is the canonical plotting source.

### Environment

- Gym registration: `robomaster2D/robomaster2D/__init__.py` registers `Robomaster-v0`.
- Environment class: `robomaster2D/robomaster2D/envs/RMUA_Env_for_RL.py::RMUA_Multi_agent_Env`.
- Default environment config: `robomaster2D/robomaster2D/envs/options.py::Parameters`.
- Simulator core: `kernel_game.py`, `kernel_engine.py`, `kernel_map.py`, `kernel_referee.py`, `kernel_objects.py`.

### Opponent Policies

- Policy allocator: `robomaster2D/robomaster2D/envs/src/kernel_agents.py::AgentsAllocator`.
- Aggressive behavior tree: `src/agents/handcrafted_enemy.py`.
- Defensive behavior tree: `src/agents/retreat_enemy.py`.
- Mixed behavior tree: default `blue_agents_path` has both aggressive and defensive agents; `AgentsAllocator.get_agents()` samples one per reset, so it is fixed within one episode.
- Stationary: `src/agents/static_enemy.py`.
- Random action: added as `src/agents/random_enemy.py`.
- Neural opponent shell: `src/agents/nn_enemy.py`.

### Action Mask

- The action mask is implemented as a legality gate on `shoot`: `rl_trainer.py` and `nn_enemy.py` only apply the shoot action when `aimed_enemy is not None`.
- A new config switch `use_action_mask` was added. `SERPPO-noAM` maps to `use_action_mask=False`.

### PPO / MAPPO / SERPPO / HFO Code

- PPO update and pseudo-termination-aware return handling: `elegantrl_dq/agents/AgentPPO.py`.
- Multi-env replay buffer with `mask` and `pseudo_mask`: `elegantrl_dq/train/replay_buffer.py`.
- Multi-discrete actor, independent critic, shared actor-critic, LSTM/GRU actor, and critic extra-state path: `elegantrl_dq/agents/net.py`.
- Future-observing critic in current code maps to `use_extra_state_for_critic=True` and `use_action_prediction=True`; the encoded cue is other-agent one-hot action information with current horizon effectively one step.
- Full upstream MAPPO infrastructure still lives separately in `elegantrl/agents/AgentMAPPO.py`. For the current three-graph rerun, `framework_ablation/MAPPO` is wired as a shared-reward MAPPO-style baseline through the RoboMaster PPO runner and has passed smoke testing.

### Batch Seed Scripts

- No previous multi-seed batch runner was found.
- Added `run_all_10seeds.sh`, `run_all_evals.sh`, and `scripts/quality_report.py`.

## Paper Experiment Switch Mapping

| Paper switch | Current mapping | Status |
| --- | --- | --- |
| SERPPO | independent actor-critic, lidar, multi-discrete, mask on, pseudo termination on, no RNN, no future critic | implemented in new registry |
| HFO-SERPPO | SERPPO + LSTM actor + future-observing critic | implemented in new registry |
| HO-SERPPO | SERPPO + LSTM actor + no future critic | reuse `recurrent_actor/SERPPO-LSTM` |
| SERPPO-LSTM | `if_use_rnn=True`, `LSTM_or_GRU=True` | implemented |
| SERPPO-GRU | `if_use_rnn=True`, `LSTM_or_GRU=False` | implemented |
| SERPPO-noPD | `if_per_or_gae=False` | implemented |
| SERPPO-noAM | `use_action_mask=False` | implemented |
| SERPPO-L | `use_lidar=True` | equivalent to default SERPPO |
| SERPPO-M | `use_obstacle_map=True`, `use_lidar=False` | implemented |
| SERPPO-noBO | `use_lidar=False`, `use_obstacle_map=False`, obstacles still enabled | implemented |
| independent actor-critic | `if_share_network=False` | default SERPPO |
| partially shared actor-critic | `if_share_network=True` | implemented |
| factorized multi-discrete action | `action_type='MultiDiscrete'` | implemented |
| 1D action-combination output | `SERPPO-1DActionSpace` uses a joint-discrete single-head policy and decodes the selected combination back to the environment multi-discrete action | implemented for current graph rerun |
| MAPPO | shared-reward MAPPO-style baseline through the current RoboMaster runner | implemented for current graph rerun |
| Arena 1/2/3 | no exact obstacle-layout switches found | missing |
| team-size variation | no disabled-robot-at-reset switch found | missing |
| replay/screenshot export | render exists, replay/screenshot export not found | missing |

## Reuse Decisions

- `SERPPO-L` can reuse default `SERPPO`, because default obstacle representation is 1D lidar.
- `SERPPO-LSTM` can reuse `HO-SERPPO`, because both map to LSTM actor with no future-observing critic.
- `pseudo_termination/SERPPO` and `pseudo_termination/SERPPO-noPD` can reuse `framework_ablation` logs if critic/value loss fields are present.
- `final_hfo_training/HFO-SERPPO` can reuse `future_observing_critic/HFO-SERPPO`.

## New Files

- `experiment_registry.yaml`: JSON-compatible YAML registry for training groups, variants, reuse rules, and missing-switch notes.
- `scripts/rm_experiment.py`: one seed training CLI with config/status/git/log/checkpoint layout.
- `scripts/rm_evaluate.py`: one checkpoint evaluation CLI for HFO/SERPPO-style policies.
- `scripts/quality_report.py`: inventory and data quality report generator.
- `scripts/plot_training_curves.py`: JSONL-based multi-seed curve plotter with step-bin alignment and CSV/manifest outputs.
- `docs/plotting_data_pipeline.md`: current collection, plotting, and paper-grade curve protocol.
- `run_all_10seeds.sh`: batch training runner with max concurrency, GPU assignment, skip-completed logic, and per-run stdout/stderr.
- `run_all_evals.sh`: batch evaluation runner for currently implemented HFO Table 2-style opponent evaluations.
- `robomaster2D/robomaster2D/envs/src/agents/random_enemy.py`: random-action scripted policy.

## Known Blockers Before Full Paper Sweep

- Treat the current `MAPPO` curve as a shared-reward MAPPO-style baseline unless a stricter paper definition requires the separate upstream `AgentMAPPO` runner.
- Define exact Arena 1/2/3 obstacle layouts before Table 4 evaluation.
- Add exact disabled-robot-at-reset support before Table 3 team-size evaluation.
- Add replay/screenshot export support before qualitative case collection.
- Full default training budget is computationally large on the current machine. One default run emitted 3 JSONL records and reached 196,618 env steps in about 13.5 minutes; the registry default is 100,000,000 env steps per run, and 90 implemented/reused training runs are needed for all 10-seed implemented groups.
- Skip/restart safety: `run_all_10seeds.sh` only skips a completed run when `final_step` reaches the requested budget. `scripts/rm_experiment.py` archives incomplete existing run directories to `seed_N_bak0`, `seed_N_bak1`, ... before starting a clean replacement run.

## Smoke And Execution Status

- Training smoke passed for all 8 selected three-graph variants with `seed=0`, `BREAK_STEP=1024`, `TARGET_STEP=1024`, `BATCH_SIZE=512`, `EVAL_TIMES=1`, `NUM_ENVS=1`; see `graph_runs/reports/smoke_matrix_20260501_graph_smoke_report.md`.
- The passed variants are `SERPPO`, `SERPPO-noPD`, `SERPPO-noAM`, `SERPPO-noBO`, `MAPPO`, `SERPPO-1DActionSpace`, `HO-SERPPO`, and `HFO-SERPPO`.
- Evaluation smoke passed for HFO-SERPPO against the currently wired Table 2 opponent subset: aggressive BT, defensive BT, stationary, random-action, random neural, and HFO-SERPPO.
- Smoke outputs were preserved in `runs_multi_seed_smoke_bak0/` and `eval_results_smoke_bak0/`.
- A formal default-budget run was started for `framework_ablation/SERPPO/seed_0`, then stopped cleanly with a `checkpoints/stop` file after the feasibility estimate. It is preserved under `runs_multi_seed/framework_ablation/SERPPO/seed_0/` with `final_step=196618`.
- `framework_ablation/SERPPO/seed_1` was started by the batch script immediately after seed 0 completed and was then stopped; its `status.json` records the stop reason.
- Final inventory files were generated for the current state: `run_inventory.csv`, `eval_inventory.csv`, `failed_runs.txt`, and `data_quality_report.md`.

## Command Templates

Single run:

```bash
CONDA_ENV=rm8 CUDA_VISIBLE_DEVICES=0 conda run -n rm8 python scripts/rm_experiment.py --experiment-group framework_ablation --variant SERPPO --seed 0
```

Batch training, after confirming environment and run budget:

```bash
CONDA_ENV=rm8 GPU_IDS=0 MAX_JOBS=1 bash run_all_10seeds.sh
```

Short smoke run, recommended before the full sweep:

```bash
CONDA_ENV=rm8 GPU_IDS=0 MAX_JOBS=1 SEEDS=0 BREAK_STEP=1024 TARGET_STEP=1024 BATCH_SIZE=512 EVAL_TIMES=2 EVAL_GAP=0 NUM_ENVS=2 bash run_all_10seeds.sh
```

Implemented evaluation subset after HFO checkpoints exist:

```bash
CONDA_ENV=rm8 GPU_IDS=0 MAX_JOBS=1 bash run_all_evals.sh
```

Quality report after runs:

```bash
conda run -n rm8 python scripts/quality_report.py
```
