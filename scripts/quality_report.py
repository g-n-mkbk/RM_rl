import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TRAIN_FIELDS = [
    "experiment_group", "variant_name", "seed", "global_step", "env_step", "episode",
    "episodic_return", "episodic_return_mean", "training_win_rate", "eval_win_rate",
    "critic_loss", "value_loss", "policy_loss", "entropy_loss", "approx_kl",
    "clip_fraction", "shared_reward", "exclusive_reward", "total_reward",
    "obstacle_related_reward", "episode_length", "true_done_count", "truncation_count",
    "pseudo_termination_enabled", "action_mask_enabled", "obstacle_representation",
    "actor_critic_parameterization", "recurrent_type", "future_observing_critic",
    "opponent_policy", "arena_layout", "team_size", "checkpoint_path"
]
REQUIRED_EVAL_FIELDS = [
    "experiment_group", "variant_name", "seed", "checkpoint_path", "global_step",
    "eval_episodes", "eval_win_rate", "eval_return_mean", "eval_return_std",
    "opponent_policy", "arena_layout", "team_size", "rl_robot_count", "enemy_count"
]


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_jsonl(path):
    rows = []
    path = Path(path)
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8") as file:
        for line_no, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"_decode_error": line_no})
    return rows


def has_bad_number(rows):
    for row in rows:
        for value in row.values():
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return True
    return False


def clean_float(value):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def train_log_stats(rows, effective_config, final_step):
    steps = [clean_float(row.get("global_step")) for row in rows]
    steps = sorted(step for step in steps if step is not None)
    deltas = [b - a for a, b in zip(steps, steps[1:]) if b > a]
    target_step = clean_float(effective_config.get("target_step"))
    final_step = clean_float(final_step)
    expected_points = None
    if target_step and final_step:
        expected_points = int(math.ceil(final_step / target_step))
    return {
        "train_log_rows": len(rows),
        "first_train_step": int(round(steps[0])) if steps else None,
        "last_train_step": int(round(steps[-1])) if steps else None,
        "median_train_step_delta": int(round(sorted(deltas)[len(deltas) // 2])) if deltas else None,
        "configured_target_step": int(round(target_step)) if target_step else None,
        "expected_train_points": expected_points,
    }


def missing_fields(rows, required):
    if not rows:
        return required
    present = set()
    for row in rows:
        present.update(row.keys())
    return [field for field in required if field not in present]


def parse_eval_stdout(path):
    metrics = {}
    path = Path(path)
    if not path.exists():
        return metrics
    text = path.read_text(encoding="utf-8", errors="ignore")
    patterns = {
        "eval_episodes": r"Evaluated\s+(\d+)\s+times",
        "eval_return_mean": r"eval_return_avg:\s*([-+0-9.eE]+)",
        "eval_return_std": r"eval_r_std:\s*([-+0-9.eE]+)",
        "eval_win_rate": r"new red_win_rate:\s*([-+0-9.eE]+)",
        "eval_red_win_rate_raw": r"red_win_rate:\s*([-+0-9.eE]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            continue
        value = match.group(1)
        metrics[key] = int(value) if key == "eval_episodes" else float(value)
    return metrics


def write_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def summarize_eval_rows(eval_rows):
    grouped = defaultdict(list)
    for row in eval_rows:
        value = clean_float(row.get("eval_win_rate"))
        if row.get("status") != "completed" or value is None:
            continue
        key = (
            row.get("eval_source"),
            row.get("eval_name"),
            row.get("policy"),
            row.get("opponent_policy"),
            row.get("arena_layout"),
            row.get("team_size"),
        )
        grouped[key].append({**row, "eval_win_rate": value})

    summary_rows = []
    for key, rows in sorted(grouped.items()):
        win_rates = [row["eval_win_rate"] for row in rows]
        returns = [clean_float(row.get("eval_return_mean")) for row in rows]
        returns = [value for value in returns if value is not None]
        count = len(win_rates)
        std = float(np_std(win_rates)) if count > 1 else 0.0
        stderr = std / math.sqrt(count) if count else None
        ci95 = 1.96 * stderr if stderr is not None else None
        return_std = float(np_std(returns)) if len(returns) > 1 else 0.0
        return_stderr = return_std / math.sqrt(len(returns)) if returns else None
        return_ci95 = 1.96 * return_stderr if return_stderr is not None else None
        summary_rows.append({
            "eval_source": key[0],
            "eval_name": key[1],
            "policy": key[2],
            "opponent_policy": key[3],
            "arena_layout": key[4],
            "team_size": key[5],
            "seed_count": len(set(str(row.get("seed")) for row in rows)),
            "row_count": count,
            "eval_win_rate_mean": sum(win_rates) / count,
            "eval_win_rate_std": std,
            "eval_win_rate_stderr": stderr,
            "eval_win_rate_ci95_low": (sum(win_rates) / count) - ci95 if ci95 is not None else None,
            "eval_win_rate_ci95_high": (sum(win_rates) / count) + ci95 if ci95 is not None else None,
            "eval_return_mean": sum(returns) / len(returns) if returns else None,
            "eval_return_std_across_seeds": return_std if returns else None,
            "eval_return_ci95_low": (sum(returns) / len(returns)) - return_ci95 if return_ci95 is not None else None,
            "eval_return_ci95_high": (sum(returns) / len(returns)) + return_ci95 if return_ci95 is not None else None,
        })
    return summary_rows


def np_std(values):
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def build_report(args):
    root = Path(args.runs_dir)
    report_dir = Path(args.output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    registry = load_json(args.registry)
    run_rows = []
    eval_rows = []
    external_eval_rows = []
    failed = []
    grouped = defaultdict(lambda: defaultdict(list))

    for seed_dir in sorted(root.glob("*/*/seed_*")):
        if not seed_dir.name.replace("seed_", "", 1).isdigit():
            continue
        status = load_json(seed_dir / "status.json")
        train_rows = read_jsonl(seed_dir / "train_log.jsonl")
        eval_jsonl_rows = read_jsonl(seed_dir / "eval_log.jsonl")
        checkpoints = sorted((seed_dir / "checkpoints").glob("*.pth"))
        final_step = status.get("final_step")
        if final_step is None and train_rows:
            final_step = train_rows[-1].get("global_step")
        config_payload = load_json(seed_dir / "config.yaml")
        effective_config = config_payload.get("effective_training_config", {})
        log_stats = train_log_stats(train_rows, effective_config, final_step)
        group = seed_dir.parents[1].name
        variant = seed_dir.parents[0].name
        seed = seed_dir.name.replace("seed_", "")
        row = {
            "experiment_group": group,
            "variant_name": variant,
            "seed": seed,
            "status": status.get("status", "missing"),
            "final_step": final_step,
            "has_nan": status.get("has_nan", False) or has_bad_number(train_rows),
            "has_checkpoint": bool(checkpoints),
            "has_train_log": bool(train_rows),
            "has_eval_log": bool(eval_jsonl_rows),
            "eval_log_rows": len(eval_jsonl_rows),
            "missing_train_fields": ",".join(missing_fields(train_rows, REQUIRED_TRAIN_FIELDS)),
            "error": status.get("error"),
            "run_dir": str(seed_dir),
            **log_stats,
        }
        run_rows.append(row)
        grouped[group][variant].append(row)
        if row["status"] != "completed":
            failed.append(f"{group}/{variant}/seed_{seed}: {row['status']} {row['error'] or ''}".strip())
        for eval_row in eval_jsonl_rows:
            eval_rows.append({
                "eval_source": "training_eval_log",
                "eval_name": "training_eval",
                "experiment_group": eval_row.get("experiment_group", group),
                "variant_name": eval_row.get("variant_name", variant),
                "policy": eval_row.get("variant_name", variant),
                "seed": eval_row.get("seed", seed),
                "opponent_policy": eval_row.get("opponent_policy"),
                "status": "completed",
                "arena_layout": eval_row.get("arena_layout"),
                "team_size": eval_row.get("team_size"),
                "global_step": eval_row.get("global_step"),
                "eval_episodes": eval_row.get("eval_episodes"),
                "eval_win_rate": eval_row.get("eval_win_rate"),
                "eval_return_mean": eval_row.get("eval_return_mean"),
                "eval_return_std": eval_row.get("eval_return_std"),
                "has_checkpoint": bool(eval_row.get("checkpoint_path")),
                "missing_eval_fields": ",".join(missing_fields([eval_row], REQUIRED_EVAL_FIELDS)),
                "run_dir": str(seed_dir),
            })

    train_status_by_checkpoint = {}
    for row in run_rows:
        run_dir = Path(row["run_dir"])
        status = load_json(run_dir / "status.json")
        checkpoint = status.get("final_checkpoint")
        if checkpoint:
            train_status_by_checkpoint[str(checkpoint)] = row

    for status_path in sorted((report_dir / "eval_results").glob("*/*/*/seed_*/status.json")):
        status = load_json(status_path)
        seed_dir = status_path.parent
        metrics = parse_eval_stdout(seed_dir / "stdout.log")
        checkpoint = status.get("checkpoint")
        train_row = train_status_by_checkpoint.get(str(checkpoint), {})
        eval_name = status_path.parts[-5]
        policy = status_path.parts[-4]
        opponent = status_path.parts[-3]
        seed = seed_dir.name.replace("seed_", "")
        external_row = {
            "eval_source": "external_eval_results",
            "eval_name": eval_name,
            "experiment_group": train_row.get("experiment_group", "external_eval"),
            "variant_name": train_row.get("variant_name", policy),
            "policy": policy,
            "seed": status.get("seed", seed),
            "opponent_policy": status.get("opponent", opponent),
            "status": status.get("status", "missing"),
            "arena_layout": "original",
            "team_size": "2v2",
            "global_step": train_row.get("final_step"),
            "eval_episodes": metrics.get("eval_episodes"),
            "eval_win_rate": metrics.get("eval_win_rate", metrics.get("eval_red_win_rate_raw")),
            "eval_return_mean": metrics.get("eval_return_mean"),
            "eval_return_std": metrics.get("eval_return_std"),
            "has_checkpoint": bool(checkpoint) and Path(checkpoint).exists(),
            "missing_eval_fields": "",
            "run_dir": str(seed_dir),
        }
        required_for_external = {
            "eval_episodes": external_row["eval_episodes"],
            "eval_win_rate": external_row["eval_win_rate"],
            "eval_return_mean": external_row["eval_return_mean"],
            "eval_return_std": external_row["eval_return_std"],
        }
        external_missing = [key for key, value in required_for_external.items() if value is None]
        external_row["missing_eval_fields"] = ",".join(external_missing)
        external_eval_rows.append(external_row)
        eval_rows.append(external_row)

    write_csv(report_dir / "run_inventory.csv", run_rows, [
        "experiment_group", "variant_name", "seed", "status", "final_step", "has_nan",
        "has_checkpoint", "has_train_log", "has_eval_log", "train_log_rows",
        "eval_log_rows", "first_train_step", "last_train_step", "median_train_step_delta",
        "configured_target_step", "expected_train_points", "missing_train_fields",
        "error", "run_dir"
    ])
    write_csv(report_dir / "eval_inventory.csv", eval_rows, [
        "eval_source", "eval_name", "experiment_group", "variant_name", "policy", "seed",
        "opponent_policy", "status", "arena_layout", "team_size", "global_step",
        "eval_episodes", "eval_win_rate", "eval_return_mean", "eval_return_std",
        "has_checkpoint", "missing_eval_fields", "run_dir"
    ])
    eval_summary_rows = summarize_eval_rows(eval_rows)
    write_csv(report_dir / "eval_summary.csv", eval_summary_rows, [
        "eval_source", "eval_name", "policy", "opponent_policy", "arena_layout", "team_size",
        "seed_count", "row_count", "eval_win_rate_mean", "eval_win_rate_std",
        "eval_win_rate_stderr", "eval_win_rate_ci95_low", "eval_win_rate_ci95_high",
        "eval_return_mean", "eval_return_std_across_seeds", "eval_return_ci95_low",
        "eval_return_ci95_high"
    ])
    (report_dir / "failed_runs.txt").write_text("\n".join(failed) + ("\n" if failed else ""), encoding="utf-8")

    lines = ["# Data Quality Report", ""]
    lines.append("Formal paper curves should use all objectively valid seeds. Do not keep only visually good seeds; exclude a run only for documented failures such as interruption, NaN/inf, corrupted logs, or missing checkpoints.")
    lines.append("")
    if not run_rows:
        lines.append("No runs were found under `runs_multi_seed/`.")
    expected_groups = registry.get("experiment_groups", [])
    for group_info in expected_groups:
        group = group_info["name"]
        lines.append(f"## {group}")
        for variant_info in group_info.get("variants", []):
            variant = variant_info["name"]
            rows = grouped[group][variant]
            completed = [row for row in rows if row["status"] == "completed"]
            seeds = sorted(row["seed"] for row in rows)
            expected_seeds = [str(seed) for seed in registry.get("seeds", list(range(10)))]
            missing_seeds = [seed for seed in expected_seeds if seed not in seeds]
            budgets = sorted(set(str(row["final_step"]) for row in rows))
            log_rows = sorted(set(str(row["train_log_rows"]) for row in rows))
            missing = sorted(set(row["missing_train_fields"] for row in rows if row["missing_train_fields"]))
            implemented = variant_info.get("implemented")
            reuse_of = variant_info.get("reuse_of")
            state_bits = []
            if implemented is not None:
                state_bits.append(f"implemented={implemented}")
            if reuse_of:
                state_bits.append(f"reuse_of={reuse_of}")
            state_text = f"; {'; '.join(state_bits)}" if state_bits else ""
            lines.append(f"- {variant}: seeds={','.join(seeds) or 'none'}; completed={len(completed)}/10; final_steps={','.join(budgets) or 'none'}; train_log_rows={','.join(log_rows) or 'none'}{state_text}")
            if missing_seeds and not reuse_of:
                lines.append(f"  - Missing seeds: {','.join(missing_seeds)}")
            if any(not row["has_checkpoint"] for row in rows):
                lines.append(f"  - Missing checkpoint in seeds: {','.join(row['seed'] for row in rows if not row['has_checkpoint'])}")
            if any(not row["has_train_log"] for row in rows):
                lines.append(f"  - Missing train_log.jsonl in seeds: {','.join(row['seed'] for row in rows if not row['has_train_log'])}")
            if any(row["has_nan"] for row in rows):
                lines.append(f"  - NaN/inf detected in seeds: {','.join(row['seed'] for row in rows if row['has_nan'])}")
            if missing:
                lines.append(f"  - Missing log fields: {' | '.join(missing)}")
        lines.append("")
    if failed:
        lines.append("## Failed Runs")
        for item in failed:
            lines.append(f"- {item}")
        lines.append("")
    if external_eval_rows:
        lines.append("## External Evaluation Inventory")
        eval_grouped = defaultdict(list)
        for row in external_eval_rows:
            eval_grouped[(row["eval_name"], row["policy"], row["opponent_policy"])].append(row)
        for key, rows in sorted(eval_grouped.items()):
            completed = [row for row in rows if row["status"] == "completed"]
            missing = sorted(set(row["missing_eval_fields"] for row in rows if row["missing_eval_fields"]))
            checkpoints_missing = [str(row["seed"]) for row in rows if not row["has_checkpoint"]]
            episodes = sorted(set(str(row["eval_episodes"]) for row in rows))
            lines.append(
                f"- {'/'.join(key)}: completed={len(completed)}/10; "
                f"eval_episodes={','.join(episodes)}"
            )
            if checkpoints_missing:
                lines.append(f"  - Missing checkpoint in seeds: {','.join(checkpoints_missing)}")
            if missing:
                lines.append(f"  - Missing eval fields: {' | '.join(missing)}")
        lines.append("")
    lines.append("## Budget And Setting Checks")
    completed_rows = [row for row in run_rows if row["status"] == "completed"]
    completed_budgets = sorted(set(str(row["final_step"]) for row in completed_rows))
    lines.append(f"- Completed-run final_step values: {','.join(completed_budgets) or 'none'}")
    if len(completed_budgets) > 1:
        lines.append("- Warning: completed runs do not all use the same training budget.")
    sparse_rows = [row for row in completed_rows if int(row.get("train_log_rows") or 0) < 5]
    if sparse_rows:
        lines.append(f"- Warning: {len(sparse_rows)} completed runs have fewer than 5 training log points. This usually means `target_step` is large relative to `break_step`, so curves are not paper-grade yet.")
    density_pairs = sorted(set(
        f"{row['configured_target_step']}->{row['train_log_rows']}"
        for row in completed_rows
        if row.get("configured_target_step") is not None
    ))
    lines.append(f"- Observed target_step to train_log_rows pairs: {','.join(density_pairs) or 'none'}")
    default_rows = [row for row in run_rows if row["experiment_group"] in {"framework_ablation", "pseudo_termination", "reward_related_training_behavior"}]
    default_train_rows = []
    for row in default_rows:
        default_train_rows.extend(read_jsonl(Path(row["run_dir"]) / "train_log.jsonl")[:1])
    opponents = sorted(set(str(row.get("opponent_policy")) for row in default_train_rows if row.get("opponent_policy") is not None))
    arenas = sorted(set(str(row.get("arena_layout")) for row in default_train_rows if row.get("arena_layout") is not None))
    teams = sorted(set(str(row.get("team_size")) for row in default_train_rows if row.get("team_size") is not None))
    lines.append(f"- Default-experiment opponents observed: {','.join(opponents) or 'none'}")
    lines.append(f"- Default-experiment arenas observed: {','.join(arenas) or 'none'}")
    lines.append(f"- Default-experiment team sizes observed: {','.join(teams) or 'none'}")
    if eval_summary_rows:
        lines.append("")
        lines.append("## Evaluation Summary")
        for row in eval_summary_rows[:20]:
            lines.append(
                f"- {row['eval_name']}/{row['policy']} vs {row['opponent_policy']}: "
                f"win_rate={row['eval_win_rate_mean']:.4f} "
                f"ci95=[{row['eval_win_rate_ci95_low']:.4f},{row['eval_win_rate_ci95_high']:.4f}] "
                f"n={row['seed_count']}"
            )
    lines.extend([
        "## Reuse Notes",
        "- `pseudo_termination/SERPPO` reuses `framework_ablation/SERPPO` when critic-loss fields are present.",
        "- `pseudo_termination/SERPPO-noPD` reuses `framework_ablation/SERPPO-noPD` when critic-loss fields are present.",
        "- `obstacle_representation/SERPPO-L` reuses default `framework_ablation/SERPPO` because default obstacle representation is lidar.",
        "- `actor_critic_parameterization/independent_actor_critic` reuses default `framework_ablation/SERPPO`.",
        "- `future_observing_critic/HO-SERPPO` reuses `recurrent_actor/SERPPO-LSTM`.",
        "- `final_hfo_training/HFO-SERPPO` reuses `future_observing_critic/HFO-SERPPO`.",
        "",
        "## Known Gaps",
        "- MAPPO is implemented as the current runner's shared-reward MAPPO-style baseline; use the local JSONL config snapshot to document this mapping.",
        "- SERPPO-1DActionSpace uses a single joint-discrete categorical action head decoded back to the environment's multi-discrete command format.",
        "- Arena 1/2/3 and disabled-robot team-size evaluation need exact environment switches before final robustness evaluation.",
    ])
    (report_dir / "data_quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Build run/eval inventory and data quality report.")
    parser.add_argument("--runs-dir", default=str(ROOT / "runs_multi_seed"))
    parser.add_argument("--output-dir", default=str(ROOT))
    parser.add_argument("--registry", default=str(ROOT / "experiment_registry.yaml"))
    parsed = parser.parse_args()
    build_report(parsed)


if __name__ == "__main__":
    main()
