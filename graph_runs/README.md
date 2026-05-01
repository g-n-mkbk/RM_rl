# KBS 三张图复现实验目录

这个目录只服务于 `docs/graph/` 里的三张图重跑：

- `yb3_9`：SERPPO 消融。
- `yb3_15`：伪终止信号 value loss/critic loss。
- `yb4_8`：HO-SERPPO vs HFO-SERPPO。

第一次迁移服务器时先读：

```text
docs/server_reading_order.md
docs/kbs_server_migration_and_graph_runs.md
```

核心文件：

- `configs/kbs_three_graphs_5seeds.env`：4090 单卡默认运行参数。
- `configs/experiments.tsv`：三张图对应的实验清单。
- `scripts/run_graph_experiment_5seeds.sh`：跑一个 variant 的 5 个 seed。
- `scripts/smoke_test_selected_graph_experiments.sh`：服务器正式训练前的 smoke 测试。
- `scripts/check_graph_progress.sh`：检查 5-seed 完成情况。
- `logs/`：脚本级日志。
- `reports/`：后续手工汇总报告放这里。
- `plots_paper/`：正式投稿图导出目录。

当前推荐手动逐个运行 `run_graph_experiment_5seeds.sh`。仓库里保留的批量脚本只是备用，不作为本轮主流程。

终端里的 `FPS` 是训练吞吐量，表示每秒采集多少 environment steps，不是视频帧率；它只用于监控服务器速度和判断是否能并发。

训练原始数据仍写入仓库统一目录：

```text
runs_multi_seed/{experiment_group}/{variant}/seed_{seed}/
```
