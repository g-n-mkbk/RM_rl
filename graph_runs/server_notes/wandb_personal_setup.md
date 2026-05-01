# WandB Setup

当前账号的个人 entity 被 WandB 禁用，所以训练默认写入已验证可用的团队项目：

```bash
WANDB=1
WANDB_PROJECT=exbody_test
WANDB_ENTITY=goodnight-mkbk-northeastern-university
```

已验证可写项目：

```text
https://wandb.ai/goodnight-mkbk-northeastern-university/exbody_test
```

如果后续在 WandB 网页里创建正式项目 `RM_rl_KBS_graphs`，再把 `WANDB_PROJECT` 改回正式项目名即可。

本地 `rm8` 环境当前检查结果：

```text
api_key: null
entity: null
```

因此第一次训练前需要手动登录：

```bash
conda activate rm8
wandb login
```

登录后确认：

```bash
conda run -n rm8 wandb status
```

应看到 `api_key` 不再是 `null`。

如果只想本地测试、不上传 wandb：

```bash
WANDB=0 BREAK_STEP=100000 TARGET_STEP=8192 SEEDS="0" bash graph_runs/scripts/run_graph_experiment_5seeds.sh framework_ablation SERPPO
```
