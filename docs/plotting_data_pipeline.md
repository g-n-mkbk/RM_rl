# Plotting Data Pipeline

This note defines the current data collection and plotting method for paper-style RoboMaster RL curves.

## Current Collection Method

- The canonical curve data is not TensorBoard data.
- The canonical curve data is not wandb data by default.
- `scripts/rm_experiment.py` writes local JSONL files through `JsonlRunLogger`.
- wandb remains optional through `--wandb`, but paper plots should treat local JSONL as the reproducible source of record.
- Terminal `FPS` is only a training-throughput monitor, roughly environment steps per second. It is useful for server diagnostics and concurrency decisions, but it is not a paper metric and is not plotted.

For each seed, the training CLI writes:

- `runs_multi_seed/{group}/{variant}/seed_{seed}/train_log.jsonl`
- `runs_multi_seed/{group}/{variant}/seed_{seed}/eval_log.jsonl`
- `runs_multi_seed/{group}/{variant}/seed_{seed}/config.yaml`
- `runs_multi_seed/{group}/{variant}/seed_{seed}/status.json`

`train_log.jsonl` is one JSON object per PPO update iteration. One iteration means:

1. collect about `target_step` environment samples,
2. update the PPO networks,
3. call `MultiEnvDiscretePPO.evaluate(...)`,
4. append one training record.

`eval_log.jsonl` is appended only when the evaluator actually runs in-training evaluation. The gate is time-based:

- `eval_gap` is measured in seconds, not environment steps.
- `eval_gap=0` means evaluate on every PPO iteration.
- `eval_times` is the number of evaluation episodes sampled at each in-training evaluation point.

The x-axis field for plots is `global_step`, which is the accumulated environment step count returned by the rollout collector. It can differ slightly from exact multiples of `target_step` because the multi-agent collector completes rollout bookkeeping and pseudo-termination handling.

## Why The Current Curves Have So Few Points

Most current runs use:

- `target_step=65536`
- completed budget around `131k` to `196k` environment steps for several groups

That produces only about `ceil(final_step / target_step)` training records, so many seeds have only 2 or 3 points. `SERPPO-M` uses `target_step=8192`, so it has noticeably more points under a similar budget.

This is enough for a smoke or feasibility check, but it is not enough for paper-grade learning curves. Low win rate and negative rewards should therefore be interpreted as early-training behavior, not as a final reproduction of the original experiment.

## Paper-Style Collection Protocol

Use local JSONL as the primary artifact and keep wandb only as an optional monitoring mirror.

Recommended curve policy:

- Use the same `break_step` for all variants in the same figure.
- Use a smaller `target_step` for curve resolution, for example `8192` or `16384` when memory allows.
- Use `eval_gap=0` for dense in-training evaluation, or a small fixed value if evaluation cost dominates.
- Keep `eval_times` fixed across all variants in the same figure.
- Use all valid seeds. Exclude a seed only for a documented failure such as NaN, interruption, missing checkpoint, or corrupted log.
- Use external evaluation sweeps, not noisy rollout reward, for final win-rate tables.

Example curve run:

```bash
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_TIMES=20 EVAL_GAP=0 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO
```

Example final external evaluation, only needed for table-style claims after checkpoints exist:

```bash
CONDA_ENV=rm8 GPU_IDS=0 MAX_JOBS=1 EVAL_EPISODES=100 bash run_all_evals.sh
```

## Current Plotting Method

`scripts/plot_training_curves.py` reads `train_log.jsonl`, not TensorBoard or wandb. For each metric and variant it now:

1. keeps only completed seeds,
2. bins `global_step` by the configured `target_step`,
3. aggregates only the shared completed step range by default,
4. computes seed mean, standard deviation, standard error, and 95% confidence interval,
5. plots the mean curve with 95% confidence interval shading by default,
6. writes both PNG and CSV for every plotted metric,
7. writes `manifest.json` to record plotting parameters and source variants.

Default output:

```bash
conda run -n rm8 python scripts/plot_training_curves.py
```

Outputs:

- `plots_draft/training_curves/*.png`
- `plots_draft/training_curves/*.csv`
- `plots_draft/training_curves/manifest.json`
- `plots_draft/training_curves/manifest.txt`

For manuscript figures without embedded titles:

```bash
conda run -n rm8 python scripts/plot_training_curves.py --no-title --shade ci95 --min-seeds 2
```

## Reading The Plots

- `episodic_return_mean`: average undiscounted episode reward observed during training rollouts. It can be negative because penalties such as damage, death, obstacle contact, and failed engagements dominate early policies.
- `training_win_rate`: win rate from the rollout collector. This is useful for learning trend, but it is not the final evaluation table metric.
- `eval_win_rate`: in-training evaluation win rate when evaluation was run. It depends on `eval_gap` and `eval_times`.
- `critic_loss` / `value_loss`: value-function fitting loss. It should be read for stability and divergence, not as a direct performance score. A lower loss is not automatically a better policy if the reward scale or data distribution changed.
- `obstacle_related_reward`: reward component derived from obstacle and wheel-hit terms. More negative values indicate more obstacle-related penalties.

For final paper claims, use:

- training curves for convergence and ablation trends,
- external evaluation summary for win-rate tables,
- quality report to document excluded or incomplete seeds.
