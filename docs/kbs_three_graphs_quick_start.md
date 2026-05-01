# KBS 三张图 5-Seed 快速运行说明

这份文档只讲一件事：租一台单卡 RTX 4090 服务器后，怎么把 `docs/graph/` 里的三张图重新采集 5 个 seed 的数据，并用 wandb 监控。

如果是第一次迁移到服务器，先读完整手册：

```text
docs/kbs_server_migration_and_graph_runs.md
```

本文档只保留最短运行路径。

## 0. 你现在要跑哪些图

目录 `docs/graph/` 里有三张旧图：

```text
docs/graph/yb3_9.jpg
docs/graph/yb3_15.jpg
docs/graph/yb4_8.jpg
```

对应关系：

| 图 | 内容 | 需要的实验 |
|---|---|---|
| `yb3_9` | SERPPO 消融：奖励曲线、胜率曲线 | `MAPPO`, `SERPPO`, `SERPPO-noPD`, `SERPPO-noAM`, `SERPPO-noBO`, `SERPPO-1DActionSpace` |
| `yb3_15` | 是否使用伪终止信号的价值损失 | 直接复用 `SERPPO` 和 `SERPPO-noPD` 的 `critic_loss/value_loss` |
| `yb4_8` | HO-SERPPO vs HFO-SERPPO：奖励曲线、胜率曲线 | `HO-SERPPO`, `HFO-SERPPO` |

本轮计划：每个可运行实验跑 5 个 seed。

```bash
SEEDS="0 1 2 3 4"
```

## 1. 跑图目录结构

我已经新建：

```text
graph_runs/
  README.md
  configs/
    kbs_three_graphs_5seeds.env
    experiments.tsv
  scripts/
    run_graph_experiment_5seeds.sh
    check_graph_progress.sh
  logs/
  outputs/
    raw_jsonl/
    checkpoints/
  reports/
  plots_draft/
  plots_paper/
  server_notes/
  wandb/
```

注意：训练程序真实输出仍然写到统一目录：

```text
runs_multi_seed/{experiment_group}/{variant}/seed_{seed}/
```

每个 seed 会有：

```text
config.yaml
train_log.jsonl
eval_log.jsonl
status.json
stdout.log
stderr.log
git_commit.txt
checkpoints/
```

## 2. 原来默认跑多少步，现在改成多少步

代码注册表里的原完整预算是：

```text
break_step = 100000000
```

也就是 100M environment steps。

我之前为了让本机快速完成，把 watchdog 默认改成：

```text
BREAK_STEP = 100000
```

也就是约 100k steps。本机那批只是可跑性和数据链路验证，不适合作为最终 KBS 投稿曲线。

现在建议按旧图横轴重跑：

| 图 | 建议步数 |
|---|---:|
| `yb3_9` | `BREAK_STEP=15000000` |
| `yb3_15` | 复用 `yb3_9` 的 `SERPPO` 和 `SERPPO-noPD` |
| `yb4_8` | 先跑 `BREAK_STEP=15000000`；确认无误后再考虑 100M |

## 3. 服务器环境配置

仓库根目录有：

```text
environment.yaml
```

服务器上执行：

```bash
conda env create -f environment.yaml
conda activate rm8
pip install -e .
pip install -e ./robomaster2D
```

检查 GPU：

```bash
conda run -n rm8 python - <<'PY'
import torch
print(torch.__version__)
print("cuda:", torch.cuda.is_available())
print("gpu:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
PY
```

4090 单卡建议：

- `GPU_ID=0`
- `MAX_JOBS=1`
- 一次只跑一个 seed
- 多个实验顺序跑，避免多个训练进程抢显存

## 4. WandB 怎么用

我已经把 wandb 接入改成可用环境变量控制。

推荐先登录：

```bash
wandb login
```

默认配置在：

```text
graph_runs/configs/kbs_three_graphs_5seeds.env
```

关键项：

```bash
WANDB=1
WANDB_PROJECT=exbody_test
WANDB_ENTITY=goodnight-mkbk-northeastern-university
WANDB_GROUP=
WANDB_NOTES="KBS three graph 5-seed rerun"
```

当前账号的个人 entity 被 WandB 禁用，直接写 `WANDB_ENTITY=goodnight-mkbk` 会返回 403。已验证可写的目标是：

```text
https://wandb.ai/goodnight-mkbk-northeastern-university/exbody_test
```

因此默认先写入 `goodnight-mkbk-northeastern-university/exbody_test`，保证你能实时观察训练。后续如果你在 WandB 网页里创建了正式项目，比如 `RM_rl_KBS_graphs`，再把 `WANDB_PROJECT` 改回正式项目名。

本地已验证 WandB 可以成功写入，上一次写入测试 run 为：

```text
https://wandb.ai/goodnight-mkbk-northeastern-university/exbody_test/runs/o8r60ab4
```

服务器第一次运行前仍然需要手动登录：

```bash
conda activate rm8
wandb login
```

如果以后改用别的团队 entity，例如 `my_lab`，再改成：

```bash
WANDB_ENTITY=my_lab
```

建议：wandb 用来远程看训练状态；论文最终画图仍然以本地 `train_log.jsonl` 为准。

## 5. 单独跑某一个实验

本轮不使用“一次性跑所有实验”的脚本。你手动选择一个实验运行，确认没问题后再跑下一个。

格式：

```bash
bash graph_runs/scripts/run_graph_experiment_5seeds.sh <experiment_group> <variant>
```

示例 1：跑 `yb3_9` 里的 SERPPO，5 个 seed，15M steps：

```bash
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO
```

示例 2：跑 HFO-SERPPO，5 个 seed，先跑 15M steps：

```bash
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh future_observing_critic HFO-SERPPO
```

示例 3：不使用 wandb：

```bash
WANDB=0 BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-noPD
```

脚本会实时把训练输出打印在当前终端，同时保存：

```text
runs_multi_seed/{group}/{variant}/seed_{seed}/stdout.log
runs_multi_seed/{group}/{variant}/seed_{seed}/stderr.log
graph_runs/logs/{group}__{variant}__5seeds.log
```

终端里的 `FPS` 是训练吞吐量，表示大约每秒采集多少 environment steps，不是画面帧率。它主要用来判断服务器是否变慢，以及是否适合并发第二个实验；论文正式图不画 FPS。

## 6. 当前所有运行命令

### `yb3_9` 和 `yb3_15`

```bash
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-noPD
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-noAM
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-noBO
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation MAPPO
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-1DActionSpace
```

`yb3_15` 不单独重复训练，直接复用：

```text
framework_ablation/SERPPO
framework_ablation/SERPPO-noPD
```

### `yb4_8`

```bash
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh future_observing_critic HO-SERPPO
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh future_observing_critic HFO-SERPPO
```

## 7. 能不能同时跑多个 5-seed 脚本

技术上可以：不同实验会写到不同目录，例如 `framework_ablation/SERPPO` 和 `framework_ablation/SERPPO-noPD` 不会互相覆盖。

但你租的是单卡 RTX 4090，我建议本轮不要同时跑多个训练脚本：

- 多个训练进程会抢同一张 GPU，显存和速度都不稳定。
- RNN/HFO 变体更容易因为并发触发 OOM。
- 如果同一个实验同一个 seed 被两个终端同时跑，会写同一个目录，必须避免。

推荐策略：

```text
单卡 4090：一次跑一个实验的 5 个 seed。
多卡服务器：每张 GPU 跑一个实验，并设置不同 GPU_ID。
```

## 8. MAPPO 和 1DActionSpace 怎么实现

`yb3_9` 旧图里有：

```text
MAPPO
SERPPO-no1DActionSpace
```

当前已经补到可运行路径：

- `MAPPO`：使用当前 RoboMaster runner 的共享团队奖励 MAPPO-style baseline，关闭伪终止价值目标。
- `SERPPO-1DActionSpace`：策略网络使用单个 joint-discrete categorical head，输出完整动作组合编号，再解码回环境使用的 multi-discrete 动作。

运行命令：

```bash
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation MAPPO
SEEDS="0 1 2 3 4" GPU_ID=0 BREAK_STEP=15000000 TARGET_STEP=16384 EVAL_GAP=0 EVAL_TIMES=20 WANDB=1 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-1DActionSpace
```

## 9. 评估脚本是做什么的

训练脚本会在训练过程中定期写：

```text
train_log.jsonl
eval_log.jsonl
```

这已经足够画学习曲线，例如：

- episodic return
- training win rate
- critic loss/value loss
- in-training eval win rate

评估脚本 `scripts/rm_evaluate.py` 的用途不同：

```text
拿训练好的 checkpoint，固定对手、固定地图、固定评估回合数，单独跑评估。
```

它主要用于表格或最终性能评估，例如：

- HFO-SERPPO vs aggressive opponent
- HFO-SERPPO vs defensive opponent
- HFO-SERPPO vs stationary/random opponent
- 每个 seed 评估 100 episodes
- 最后统计 mean ± std 或 95% CI

也就是说：

- 画 `yb3_9 / yb3_15 / yb4_8` 这种训练曲线：主要看 `train_log.jsonl` 和训练期 `eval_log.jsonl`。
- 做最终胜率表、对手泛化表：用 `scripts/rm_evaluate.py`。

这次你只要重画三张训练曲线，评估脚本不是第一优先级；但训练完成后建议对最终 checkpoint 再跑一轮外部评估，作为论文表格或补充结果。

## 10. 正式图画图标准

本轮正式图统一：

```text
n = 5 seeds, seeds = [0,1,2,3,4]
mean curve + 95% CI shadow
```

不使用单 seed 曲线，不挑 seed。只有程序错误、NaN、日志损坏、checkpoint 缺失等客观失败才能剔除，并且要写进报告。

## 11. 进度检查

```bash
bash graph_runs/scripts/check_graph_progress.sh
```

查看某个 seed 日志：

```bash
tail -n 50 runs_multi_seed/framework_ablation/SERPPO/seed_0/stdout.log
tail -n 50 runs_multi_seed/framework_ablation/SERPPO/seed_0/stderr.log
tail -n 3 runs_multi_seed/framework_ablation/SERPPO/seed_0/train_log.jsonl
cat runs_multi_seed/framework_ablation/SERPPO/seed_0/status.json
```

## 12. 训练后生成质检和草图

```bash
conda run -n rm8 python scripts/quality_report.py
conda run -n rm8 python scripts/plot_training_curves.py --no-title --shade ci95 --min-seeds 3
```

输出：

```text
run_inventory.csv
eval_inventory.csv
failed_runs.txt
data_quality_report.md
plots_draft/training_curves/
```

正式 KBS 投稿图建议之后另存：

```text
graph_runs/plots_paper/
```

并导出：

- PDF/EPS 矢量图
- TIFF 备份图
- 每张图对应的聚合 CSV

## 13. 当前已经确定的运行决策

### `yb4_8` 是否直接补跑 100M？

当前已确定：

```text
先统一跑 15M。
```

15M 数据检查通过后，再决定是否把 `yb4_8` 补到 100M。

### `yb3_9` 里的 MAPPO 和 1DActionSpace 是否纳入本轮？

```text
要补跑。当前代码已经提供可运行映射：MAPPO-style shared-reward baseline 和 joint-discrete 1D action head。
```

### 正式图阴影用 std 还是 95% CI？

当前已确定：

```text
KBS 正式图用 95% CI；补充材料可给 mean ± std。
```

### 5 个 seed 是否固定为 0-4？

当前已确定：

```text
固定使用 seeds = [0,1,2,3,4]。
```

如果后续时间允许，扩展到 10 seed 会更稳。
