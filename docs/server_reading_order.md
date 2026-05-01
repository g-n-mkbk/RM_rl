# 服务器迁移与训练文档阅读顺序

这份文件是入口索引。迁移到服务器后，不要从旧的实验报告或零散脚本开始，按下面顺序读。

## 第一遍阅读顺序

1. `docs/server_reading_order.md`

   当前文件。先确认整体路线。

2. `docs/kbs_server_migration_and_graph_runs.md`

   主手册。包含服务器环境、`rm8` 环境创建、WandB 登录、smoke 测试、正式 5-seed 命令、FPS 含义、并发规则、质检和结果回传。

3. `graph_runs/README.md`

   了解 `graph_runs/` 目录里哪些文件是配置、脚本、日志、报告。

4. `graph_runs/configs/experiments.tsv`

   三张图的真实实验矩阵。确认 `yb3_9`、`yb3_15`、`yb4_8` 对应哪些 group/variant。

5. `graph_runs/configs/kbs_three_graphs_5seeds.env`

   默认运行参数。重点看 `SEEDS`、`BREAK_STEP`、`TARGET_STEP`、`EVAL_GAP`、`EVAL_TIMES`、`WANDB_PROJECT`、`WANDB_ENTITY`。

6. `graph_runs/reports/smoke_matrix_20260501_graph_smoke_report.md`

   本地已经通过的 smoke 结果。服务器第一次跑完 smoke 后，可以和这里对照。

7. `graph_runs/reports/current_parallelism_assessment.md`

   如果想一张 4090 同时跑两个实验，先读这里。重点看 CPU idle、GPU utilization、显存和 FPS 下降阈值。

8. `docs/plotting_data_pipeline.md`

   训练完成后再读。它说明正式曲线如何从 JSONL 聚合、如何使用 95% CI、哪些指标该画。

9. `docs/experiment_readiness_report.md`

   作为完整论文实验映射参考。当前三张图运行以 `docs/kbs_server_migration_and_graph_runs.md` 和 `graph_runs/configs/experiments.tsv` 为准。

## 按任务查文档

准备服务器环境：

```text
docs/kbs_server_migration_and_graph_runs.md
environment.yaml
```

确认三张图要跑什么：

```text
graph_runs/configs/experiments.tsv
docs/kbs_server_migration_and_graph_runs.md
```

修改默认 seed、WandB 项目、训练预算：

```text
graph_runs/configs/kbs_three_graphs_5seeds.env
```

正式跑某一个实验的 5 个 seed：

```text
graph_runs/scripts/run_graph_experiment_5seeds.sh
run_one_experiment_5seeds.sh
```

检查实验是否跑完：

```text
graph_runs/scripts/check_graph_progress.sh
runs_multi_seed/{group}/{variant}/seed_{seed}/status.json
```

排查速度变慢或是否能并发：

```text
docs/kbs_server_migration_and_graph_runs.md
graph_runs/reports/current_parallelism_assessment.md
```

训练完成后画草图和质检：

```text
docs/plotting_data_pipeline.md
scripts/quality_report.py
scripts/plot_training_curves.py
```

## 最短执行路线

服务器上最短路线如下：

```bash
conda env create -f environment.yaml
conda activate rm8
pip install -e .
pip install -e ./robomaster2D
wandb login
```

先 smoke：

```bash
STAMP=server_smoke_$(date +%Y%m%d_%H%M%S) WANDB=0 SEED=0 BREAK_STEP=1024 TARGET_STEP=1024 BATCH_SIZE=512 EVAL_GAP=0 EVAL_TIMES=1 NUM_ENVS=1 bash graph_runs/scripts/smoke_test_selected_graph_experiments.sh
```

再正式跑单个实验的 5 seed，例如：

```bash
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO
```

跑完所有选定实验后：

```bash
conda run -n rm8 python scripts/quality_report.py
conda run -n rm8 python scripts/plot_training_curves.py --no-title --shade ci95 --min-seeds 2
```
