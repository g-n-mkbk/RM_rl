# Smoke Matrix Report

Run time: 2026-05-01 00:13-00:18 Asia/Shanghai

Command:

```bash
STAMP=20260501_graph_smoke WANDB=0 SEED=0 BREAK_STEP=1024 TARGET_STEP=1024 BATCH_SIZE=512 EVAL_GAP=0 EVAL_TIMES=1 NUM_ENVS=1 bash graph_runs/scripts/smoke_test_selected_graph_experiments.sh
```

Output root:

```text
graph_runs/smoke_matrix_20260501_graph_smoke/
```

Summary:

| Experiment group | Variant | Status | Final step | Train log | Checkpoint |
|---|---|---:|---:|---:|---:|
| framework_ablation | SERPPO | completed | 1024 | yes | yes |
| framework_ablation | SERPPO-noPD | completed | 1024 | yes | yes |
| framework_ablation | SERPPO-noAM | completed | 1024 | yes | yes |
| framework_ablation | SERPPO-noBO | completed | 1024 | yes | yes |
| framework_ablation | MAPPO | completed | 1024 | yes | yes |
| framework_ablation | SERPPO-1DActionSpace | completed | 1025 | yes | yes |
| future_observing_critic | HO-SERPPO | completed | 1024 | yes | yes |
| future_observing_critic | HFO-SERPPO | completed | 1024 | yes | yes |

All selected graph experiments passed the smoke test. Each run completed one rollout/update/evaluation cycle and produced `train_log.jsonl`, `status.json`, and `actor_best.pth`.
