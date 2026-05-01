#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1

python3 - <<'PY'
import json
from collections import defaultdict
from pathlib import Path

wanted = [
    ("framework_ablation", "SERPPO"),
    ("framework_ablation", "SERPPO-noPD"),
    ("framework_ablation", "SERPPO-noAM"),
    ("framework_ablation", "SERPPO-noBO"),
    ("future_observing_critic", "HO-SERPPO"),
    ("future_observing_critic", "HFO-SERPPO"),
]

for group, variant in wanted:
    counts = defaultdict(int)
    details = []
    for seed in range(5):
        path = Path("runs_multi_seed") / group / variant / f"seed_{seed}" / "status.json"
        if not path.exists():
            counts["missing"] += 1
            details.append(f"seed_{seed}: missing")
            continue
        data = json.loads(path.read_text())
        counts[data.get("status", "unknown")] += 1
        details.append(f"seed_{seed}: {data.get('status')} step={data.get('final_step')}")
    print(f"{group}/{variant}: {dict(counts)}")
    for item in details:
        print("  " + item)
PY

