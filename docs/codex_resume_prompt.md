# Codex Resume Prompt

如果 Codex 对话中断，重新进入 `/home/xybuser/rl/RM_rl` 后把下面这段发给 Codex：

```text
继续完成 RoboMaster HFO-SERPPO 多 seed 实验。使用 rm8 环境，不要重置或删除已有结果。先检查后台 watchdog 和训练状态：

ps -ef | grep -E "experiment_watchdog|run_all_10seeds|rm_experiment|run_all_evals|rm_evaluate" | grep -v grep
tail -n 80 logs/experiment_watchdog.log
python3 - <<'PY'
import json
from collections import defaultdict
from pathlib import Path
by=defaultdict(lambda: defaultdict(int))
for p in Path("runs_multi_seed").glob("*/*/seed_*/status.json"):
    if not p.parent.name.replace("seed_", "", 1).isdigit():
        continue
    d=json.loads(p.read_text())
    by[(p.parts[-4], p.parts[-3])][d.get("status")] += 1
for key in sorted(by):
    print(key[0]+"/"+key[1], dict(by[key]))
PY

如果 watchdog 没有运行，执行：
CONDA_ENV=rm8 GPU_IDS=0 MAX_JOBS=1 BREAK_STEP=100000 EVAL_TIMES=5 EVAL_EPISODES=100 WATCH_INTERVAL=300 bash scripts/start_experiment_watchdog.sh

然后继续监控直到训练、评估、质检和 plots_draft/training_curves 草图曲线全部生成。
```

也可以不打开 Codex，直接在普通终端运行：

```bash
cd /home/xybuser/rl/RM_rl
CONDA_ENV=rm8 GPU_IDS=0 MAX_JOBS=1 BREAK_STEP=100000 EVAL_TIMES=5 EVAL_EPISODES=100 WATCH_INTERVAL=300 bash scripts/start_experiment_watchdog.sh
```

如果希望在 Codex 对话外也持续守住这个实验任务，运行下面的后台监控器。它会每隔 300 秒检查实验 watchdog 是否还活着；如果不在，就自动重启 watchdog，并把一键恢复 Codex 的命令写到 `logs/codex_resume_command.sh`。

```bash
cd /home/xybuser/rl/RM_rl
CONDA_ENV=rm8 GPU_IDS=0 MAX_JOBS=1 BREAK_STEP=100000 EVAL_TIMES=5 EVAL_EPISODES=100 WATCH_INTERVAL=300 bash scripts/start_codex_autoresume_monitor.sh
```

默认它不会自动启动新的 Codex 会话，只会保证实验队列继续跑。如果确实要让它在 watchdog 中断时尝试自动执行恢复提示词，可以显式加 `AUTORUN_CODEX=1`：

```bash
cd /home/xybuser/rl/RM_rl
AUTORUN_CODEX=1 CONDA_ENV=rm8 GPU_IDS=0 MAX_JOBS=1 BREAK_STEP=100000 EVAL_TIMES=5 EVAL_EPISODES=100 WATCH_INTERVAL=300 bash scripts/start_codex_autoresume_monitor.sh
```
