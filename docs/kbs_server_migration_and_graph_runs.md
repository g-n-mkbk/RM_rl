# KBS 三张图服务器迁移与训练总手册

本文档是迁移到服务器后最主要的操作手册，面向 `docs/graph/` 里三张旧图的 5-seed 重采集：

- `docs/graph/yb3_9.jpg`：SERPPO 框架消融，奖励曲线和胜率曲线。
- `docs/graph/yb3_15.jpg`：伪终止信号对 value/critic loss 的影响。
- `docs/graph/yb4_8.jpg`：HO-SERPPO 与 HFO-SERPPO 对比，奖励曲线和胜率曲线。

本轮正式采集规则：

```bash
SEEDS="0 1 2 3 4"
BREAK_STEP=15000000
TARGET_STEP=16384
EVAL_GAP=0
EVAL_TIMES=20
WANDB=1
```

本轮只跑这三张图需要的数据，不跑全部论文表格和附录实验。

## FPS 是什么

训练终端里的 `FPS` 不是渲染帧率，也不是游戏画面的 frames per second。这里的 FPS 是训练吞吐量，近似表示：

```text
FPS = 已采集 environment steps / 训练已用秒数
```

例如终端出现：

```text
TrainIter:00075 Step:1229465/15000000 ... FPS:219.6
```

意思是当前训练从开始到现在平均每秒采集约 219.6 个环境 step。

它的用途：

- 判断训练是否变慢；
- 比较 `NUM_ENVS`、`TARGET_STEP`、并发实验数量对吞吐的影响；
- 观察服务器 CPU/GPU 是否被抢占；
- 判断是否适合在同一张 GPU 上再开第二个实验。

它不应该作为论文性能指标，也不应该画进正式论文图里。论文曲线仍使用 `train_log.jsonl` 里的 `global_step`、`episodic_return_mean`、`training_win_rate`、`critic_loss/value_loss` 等字段。

## 代码和文档阅读顺序

服务器上第一次接手时，按这个顺序读：

1. `docs/server_reading_order.md`：总索引，告诉你每份文档什么时候看。
2. `docs/kbs_server_migration_and_graph_runs.md`：本文档，负责服务器环境、迁移、运行、监控。
3. `graph_runs/README.md`：`graph_runs/` 目录结构和关键脚本。
4. `graph_runs/configs/experiments.tsv`：三张图到底要跑哪些实验。
5. `graph_runs/configs/kbs_three_graphs_5seeds.env`：4090 单卡默认参数、WandB 默认项目、seed 设置。
6. `graph_runs/reports/smoke_matrix_20260501_graph_smoke_report.md`：当前 8 个实验的 smoke 测试结果。
7. `graph_runs/reports/current_parallelism_assessment.md`：什么时候可以考虑一张 GPU 同时跑第二个实验。
8. `docs/plotting_data_pipeline.md`：训练完成后如何从 JSONL 画 95% CI 曲线。
9. `docs/experiment_readiness_report.md`：完整论文实验映射参考，当前三张图以本文档和 `experiments.tsv` 为准。

## 服务器准备

推荐服务器配置：

- 单卡 RTX 4090；
- 显存 24 GB，系统内存建议 64 GB 起步，CPU 建议 16 vCPU/线程以上；
- Ubuntu 20.04/22.04；
- Conda 或 Mambaforge；
- CUDA driver 能被 PyTorch 识别；
- 足够 CPU 核数。这个环境训练偏 CPU-heavy，GPU 不是唯一瓶颈。

先检查 GPU：

```bash
nvidia-smi
```

如果 `nvidia-smi` 看不到 4090，先处理驱动，不要继续建环境。

## 租 4090 时镜像怎么选

优先选择：

```text
Ubuntu 22.04 + NVIDIA Driver + CUDA 11.8/12.x + Miniconda 或 Conda
```

如果平台提供社区镜像，推荐顺序如下：

1. `PyTorch + CUDA + Conda` 社区镜像。
2. `CUDA + Conda` 基础深度学习镜像。
3. 纯 `Ubuntu + NVIDIA Driver` 基础镜像。

不建议选择：

- Windows 镜像；
- 没有 NVIDIA driver 的纯 Ubuntu 镜像；
- 只预装 TensorFlow、没有 Conda/PyTorch 的镜像；
- CUDA 版本很老、driver 很老的镜像；
- 需要自己编译 PyTorch 的镜像。

本项目不需要系统级手动安装完整 CUDA Toolkit，只要 `nvidia-smi` 能看到 4090，且 Conda/PyTorch 里的 CUDA runtime 可用即可。`nvidia-smi` 里显示的 `CUDA Version` 表示 driver 最高兼容的 CUDA 运行时版本，不等于你 Conda 环境里安装的 PyTorch CUDA 版本。

## PyTorch 和 Miniconda 怎么选

本仓库当前环境文件固定为：

```text
environment.yaml
python=3.8.20
torch==1.13.1
CUDA 11.7 runtime packages
gym==0.19.0
numpy==1.23.5
wandb==0.16.6
```

因此最稳妥路线是：

```bash
conda env create -f environment.yaml
conda activate rm8
pip install -e .
pip install -e ./robomaster2D
```

租服务器时不用特意选择某个“PyTorch 2.x”镜像。即使社区镜像自带 PyTorch 2.x，也建议创建独立的 `rm8` 环境，不要直接用镜像默认 base 环境。

Miniconda/Mambaforge 版本通常不关键，满足下面条件即可：

- 能创建 Python 3.8 环境；
- `conda env create -f environment.yaml` 可用；
- `pip install -e .` 可用；
- 不把包安装到系统 Python 或 base 环境。

如果 `environment.yaml` 装完后 `torch.cuda.is_available()` 是 `False`，优先用官方 PyTorch 1.13.1 + CUDA 11.7 Conda 命令修复当前环境：

```bash
conda activate rm8
conda install pytorch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 pytorch-cuda=11.7 -c pytorch -c nvidia
```

然后重新检查：

```bash
python - <<'PY'
import torch
print(torch.__version__)
print(torch.version.cuda)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
PY
```

4090 是 Ada Lovelace 架构。实际租机时建议 driver 版本尽量新，优先选择 CUDA 11.8/12.x 镜像，因为这类镜像通常配套较新的 NVIDIA driver；项目环境内部仍然可以使用 PyTorch 1.13.1 的 CUDA 11.7 runtime。不要因为镜像显示 CUDA 12.x 就把项目环境强行升级到 PyTorch 2.x，除非 smoke 测试长期失败且明确是 PyTorch/CUDA 兼容问题。

## 迁移代码

推荐用 Git 迁移：

```bash
git clone <your-repo-url> RM_rl
cd RM_rl
```

如果本地还有未提交改动，先在本地提交或打包再迁移。不要只复制 `runs_multi_seed/`，因为服务器必须拿到当前脚本、注册表、日志补丁和 1D/MAPPO 相关代码。

如果用压缩包迁移，至少包含：

```text
elegantrl/
elegantrl_dq/
robomaster2D/
scripts/
graph_runs/
docs/
experiment_registry.yaml
environment.yaml
run_one_experiment_5seeds.sh
setup.py
```

训练输出目录 `runs_multi_seed/` 可以单独同步，不建议和代码混在一起覆盖。

## 创建环境

仓库根目录已经有：

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

如果服务器已有 `rm8`：

```bash
conda activate rm8
pip install -e .
pip install -e ./robomaster2D
```

GPU 和导入检查：

```bash
conda run -n rm8 python - <<'PY'
import torch
import robomaster2D
from elegantrl_dq.train.run import Arguments
print("torch:", torch.__version__)
print("cuda:", torch.cuda.is_available())
print("gpu:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
print("imports ok")
PY
```

如果 `torch.cuda.is_available()` 是 `False`，先重装匹配服务器 CUDA driver 的 PyTorch，再开始训练。

## WandB 设置

本轮建议使用个人/团队 WandB 做实时监控，但论文最终画图仍以本地 JSONL 为准。

服务器首次登录：

```bash
conda activate rm8
wandb login
```

当前默认配置在：

```text
graph_runs/configs/kbs_three_graphs_5seeds.env
```

关键默认值：

```bash
WANDB=1
WANDB_PROJECT=exbody_test
WANDB_ENTITY=goodnight-mkbk-northeastern-university
WANDB_GROUP=
WANDB_NOTES="KBS three graph 5-seed rerun"
```

本地之前验证过可写入：

```text
https://wandb.ai/goodnight-mkbk-northeastern-university/exbody_test
```

如果你在 WandB 新建了正式项目，例如 `RM_rl_KBS_graphs`，只需要运行前覆盖：

```bash
WANDB_PROJECT=RM_rl_KBS_graphs
```

如果换 entity：

```bash
WANDB_ENTITY=<your_entity_or_team>
```

## 先跑 smoke 测试

迁移到服务器后，正式 15M 训练前必须先跑 smoke：

```bash
STAMP=server_smoke_$(date +%Y%m%d_%H%M%S) \
WANDB=0 \
SEED=0 \
BREAK_STEP=1024 \
TARGET_STEP=1024 \
BATCH_SIZE=512 \
EVAL_GAP=0 \
EVAL_TIMES=1 \
NUM_ENVS=1 \
bash graph_runs/scripts/smoke_test_selected_graph_experiments.sh
```

它会依次测试三张图需要的 8 个实验：

- `framework_ablation/SERPPO`
- `framework_ablation/SERPPO-noPD`
- `framework_ablation/SERPPO-noAM`
- `framework_ablation/SERPPO-noBO`
- `framework_ablation/MAPPO`
- `framework_ablation/SERPPO-1DActionSpace`
- `future_observing_critic/HO-SERPPO`
- `future_observing_critic/HFO-SERPPO`

本地已通过的 smoke 报告见：

```text
graph_runs/reports/smoke_matrix_20260501_graph_smoke_report.md
```

服务器 smoke 如果失败，优先看：

```text
graph_runs/logs/
graph_runs/smoke_matrix_<stamp>/
```

## 三张图实验矩阵

以 `graph_runs/configs/experiments.tsv` 为准：

| 图 | 实验组 | Variant | 用途 |
|---|---|---|---|
| `yb3_9` | `framework_ablation` | `SERPPO` | 默认方法 |
| `yb3_9` | `framework_ablation` | `SERPPO-noPD` | 去掉 pseudo termination-aware value estimation |
| `yb3_9` | `framework_ablation` | `SERPPO-noAM` | 去掉 action mask |
| `yb3_9` | `framework_ablation` | `SERPPO-noBO` | 去掉 obstacle observation |
| `yb3_9` | `framework_ablation` | `MAPPO` | shared-reward MAPPO-style baseline |
| `yb3_9` | `framework_ablation` | `SERPPO-1DActionSpace` | joint-discrete single-head action policy |
| `yb3_15` | `framework_ablation` | `SERPPO` | 复用 `yb3_9`，画 value/critic loss |
| `yb3_15` | `framework_ablation` | `SERPPO-noPD` | 复用 `yb3_9`，画 value/critic loss |
| `yb4_8` | `future_observing_critic` | `HO-SERPPO` | LSTM actor，无 future-observing critic |
| `yb4_8` | `future_observing_critic` | `HFO-SERPPO` | LSTM actor，有 future-observing critic |

注意：`yb3_15` 不需要重复训练，它直接复用 `yb3_9` 里的 `SERPPO` 和 `SERPPO-noPD` 的 loss 日志。

## 正式运行命令

本轮不使用“一次性跑所有实验”的总脚本。你每次选择一个实验，让脚本顺序跑完这个实验的 5 个 seed。

通用格式：

```bash
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh <experiment_group> <variant>
```

### yb3_9: SERPPO 消融

```bash
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-noPD
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-noAM
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-noBO
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation MAPPO
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO-1DActionSpace
```

### yb3_15: pseudo termination value loss

不用单独跑。画图时复用：

```text
runs_multi_seed/framework_ablation/SERPPO/seed_*/train_log.jsonl
runs_multi_seed/framework_ablation/SERPPO-noPD/seed_*/train_log.jsonl
```

### yb4_8: HO-SERPPO vs HFO-SERPPO

```bash
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh future_observing_critic HO-SERPPO
BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh future_observing_critic HFO-SERPPO
```

旧图 `yb4_8` 横轴约到 100M。本轮先统一跑 15M；如果趋势和日志都正常，再决定是否只把这两个实验补跑到 100M：

```bash
BREAK_STEP=100000000 TARGET_STEP=65536 bash graph_runs/scripts/run_graph_experiment_5seeds.sh future_observing_critic HO-SERPPO
BREAK_STEP=100000000 TARGET_STEP=65536 bash graph_runs/scripts/run_graph_experiment_5seeds.sh future_observing_critic HFO-SERPPO
```

## 终端实时输出

`graph_runs/scripts/run_graph_experiment_5seeds.sh` 会调用：

```text
run_one_experiment_5seeds.sh
```

底层使用：

```bash
conda run --no-capture-output -n rm8 python -u scripts/rm_experiment.py ...
```

所以训练输出会实时显示在当前终端，同时写入：

```text
runs_multi_seed/{group}/{variant}/seed_{seed}/stdout.log
runs_multi_seed/{group}/{variant}/seed_{seed}/stderr.log
graph_runs/logs/{group}__{variant}__5seeds.log
```

你在终端里看到的 `TrainIter` 行就是每个 PPO update 的实时进度。

## 如何监控

另开一个终端看 GPU：

```bash
watch -n 2 nvidia-smi
```

看 CPU：

```bash
htop
```

看当前实验日志：

```bash
tail -f graph_runs/logs/framework_ablation__SERPPO__5seeds.log
```

看 5 seed 进度：

```bash
bash graph_runs/scripts/check_graph_progress.sh framework_ablation SERPPO
```

查看某个 seed 的最终状态：

```bash
cat runs_multi_seed/framework_ablation/SERPPO/seed_0/status.json
```

## 单卡 4090 是否可以同时跑多个实验

默认建议：

```bash
MAX_JOBS=1
```

也就是一个实验脚本内部按 seed 顺序跑，一个时间点只训练一个 seed。

4090 显存通常够，但这个项目的环境仿真偏 CPU-heavy，所以能不能并发主要看 CPU 和整体吞吐，不只看显存。

只有同时满足这些条件，才考虑开第二个实验：

- GPU 显存占用低于约 45%；
- GPU 利用率多数时间低于约 55%；
- CPU idle 持续高于约 35%；
- load average 低于物理核心数附近；
- 开第二个实验后两个终端里的 FPS 都没有下降超过约 15%；
- 两个实验都没有 OOM、NaN、eval 卡死或明显变慢。

如果要试并发，建议每个实验降低环境 worker：

```bash
NUM_ENVS=5 BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO
```

再开第二个终端跑另一个 variant。只要 FPS 明显掉，立即回到一次一个实验。

## 训练输出和保存路径

每个 run 的标准目录：

```text
runs_multi_seed/{experiment_group}/{variant}/seed_{seed}/
```

至少应包含：

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

训练 JSONL 是正式画图的数据源。WandB 只作为监控镜像，不作为唯一归档。

## 中断和恢复

如果某个 seed 正常完成，脚本再次运行同一个实验时会由训练程序识别已有状态。若你希望强制重跑，显式加：

```bash
FORCE=1 BREAK_STEP=15000000 TARGET_STEP=16384 bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO
```

注意：强制重跑会触发已有 run 目录的备份/归档逻辑。不要手动删除结果目录。

如果训练卡住，先看：

```bash
tail -n 80 runs_multi_seed/<group>/<variant>/seed_<seed>/stderr.log
tail -n 80 runs_multi_seed/<group>/<variant>/seed_<seed>/stdout.log
cat runs_multi_seed/<group>/<variant>/seed_<seed>/status.json
```

## 训练后质检

所有选定实验完成后运行：

```bash
conda run -n rm8 python scripts/quality_report.py
```

检查：

```bash
cat failed_runs.txt
sed -n '1,220p' data_quality_report.md
```

进入正式曲线的 run 至少满足：

- 5 个 seed 都有 `status=completed`；
- 每个 seed 有 `train_log.jsonl`；
- 每个 seed 有 `eval_log.jsonl`；
- 每个 seed 有 checkpoint；
- 没有 NaN/inf；
- 同一张图内训练预算一致；
- 只因程序错误、训练中断、NaN、日志损坏等客观原因剔除 seed，并在报告中记录。

## 画图原则

当前阶段正式训练完成前不要急着美化图。训练完成后按 `docs/plotting_data_pipeline.md` 执行。

KBS 投稿图建议：

- 正式曲线使用全部有效 seed；
- 本轮使用 `n=5 seeds`；
- 阴影区域使用 `95% CI`；
- 横轴使用 `Environment steps`；
- 图内文字使用英文；
- 曲线导出 PDF/EPS，必要时额外导出 TIFF；
- 不挑 seed，不只画表现好的一条；
- 所有剔除 seed 必须写明客观原因。

可先生成草图：

```bash
conda run -n rm8 python scripts/plot_training_curves.py --no-title --shade ci95 --min-seeds 2
```

正式投稿图再单独导出到 `graph_runs/plots_paper/` 或 `plots_paper/`。

## 结果回传

服务器训练完成后，至少回传：

```text
runs_multi_seed/
run_inventory.csv
eval_inventory.csv
failed_runs.txt
data_quality_report.md
graph_runs/logs/
graph_runs/reports/
plots_draft/
```

如果网络方便，可用：

```bash
rsync -avh --progress server:/path/to/RM_rl/runs_multi_seed/ ./runs_multi_seed/
rsync -avh --progress server:/path/to/RM_rl/graph_runs/logs/ ./graph_runs/logs/
```

不要只从 WandB 下载曲线截图；论文复现实验需要保留本地原始 JSONL、配置、checkpoint 和状态文件。
