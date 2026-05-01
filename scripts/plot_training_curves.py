import argparse
import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/rmrl_matplotlib_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

GROUP_METRICS = {
    "framework_ablation": ["episodic_return_mean", "training_win_rate", "critic_loss", "eval_win_rate"],
    "pseudo_termination": ["critic_loss", "value_loss"],
    "obstacle_representation": ["episodic_return_mean", "training_win_rate", "obstacle_related_reward", "critic_loss"],
    "actor_critic_parameterization": ["episodic_return_mean", "training_win_rate", "critic_loss"],
    "reward_related_training_behavior": ["episodic_return_mean", "training_win_rate", "total_reward", "shared_reward", "exclusive_reward"],
    "recurrent_actor": ["episodic_return_mean", "training_win_rate", "critic_loss"],
    "future_observing_critic": ["episodic_return_mean", "training_win_rate", "critic_loss"],
    "final_hfo_training": ["episodic_return_mean", "training_win_rate", "critic_loss"],
}

METRIC_LABELS = {
    "episodic_return_mean": "Mean episode reward during rollout",
    "training_win_rate": "Training win rate",
    "eval_win_rate": "In-training evaluation win rate",
    "critic_loss": "Critic loss",
    "value_loss": "Value loss",
    "policy_loss": "Policy loss",
    "obstacle_related_reward": "Obstacle-related reward",
    "total_reward": "Total reward",
    "shared_reward": "Shared reward",
    "exclusive_reward": "Exclusive reward",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def read_jsonl(path):
    rows = []
    path = Path(path)
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


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


def variant_source(group_name, variant):
    reuse = variant.get("reuse_of")
    if reuse:
        source_group, source_variant = reuse.split("/", 1)
        return source_group, source_variant
    return group_name, variant["name"]


def run_config(seed_dir):
    payload = load_json(seed_dir / "config.yaml") if (seed_dir / "config.yaml").exists() else {}
    return payload.get("effective_training_config", {})


def sort_and_dedupe(points):
    by_step = {}
    for step, value in points:
        by_step[float(step)] = float(value)
    return sorted(by_step.items())


def collect_variant_series(runs_dir, source_group, source_variant, metric):
    series = []
    source_dir = Path(runs_dir) / source_group / source_variant
    for seed_dir in sorted(source_dir.glob("seed_*")):
        seed_text = seed_dir.name.replace("seed_", "", 1)
        if not seed_text.isdigit():
            continue
        status = load_json(seed_dir / "status.json") if (seed_dir / "status.json").exists() else {}
        if status.get("status") != "completed":
            continue
        rows = read_jsonl(seed_dir / "train_log.jsonl")
        points = []
        for row in rows:
            x = clean_float(row.get("global_step"))
            y = clean_float(row.get(metric))
            if x is not None and y is not None:
                points.append((x, y))
        points = sort_and_dedupe(points)
        if not points:
            continue
        config = run_config(seed_dir)
        target_step = clean_float(config.get("target_step"))
        series.append({
            "seed": int(seed_text),
            "points": points,
            "run_dir": str(seed_dir),
            "final_step": clean_float(status.get("final_step")),
            "target_step": target_step,
        })
    return series


def infer_step_bin(seed_series):
    configured = [item["target_step"] for item in seed_series if item.get("target_step")]
    if configured:
        return int(round(float(np.median(configured))))
    deltas = []
    for item in seed_series:
        steps = [step for step, _value in item["points"]]
        deltas.extend([b - a for a, b in zip(steps, steps[1:]) if b > a])
    if not deltas:
        return None
    return int(round(float(np.median(deltas))))


def step_to_bin(step, step_bin):
    if step_bin and step_bin > 0:
        return int(round(step / step_bin) * step_bin)
    return int(round(step))


def aggregate_by_step(seed_series, min_seeds=2, step_bin=None, shared_range=True):
    if not seed_series:
        return None
    eligible = [item for item in seed_series if item["points"]]
    if len(eligible) < min_seeds:
        return None

    actual_step_bin = int(step_bin) if step_bin else infer_step_bin(eligible)
    seed_bin_maps = []
    for item in eligible:
        seed_bins = defaultdict(list)
        for step, value in item["points"]:
            seed_bins[step_to_bin(step, actual_step_bin)].append(value)
        if seed_bins:
            seed_bin_maps.append(seed_bins)

    if len(seed_bin_maps) < min_seeds:
        return None
    if shared_range and len(seed_bin_maps) > 1:
        start_step = max(min(seed_bins) for seed_bins in seed_bin_maps)
        end_step = min(max(seed_bins) for seed_bins in seed_bin_maps)
    else:
        start_step = min(min(seed_bins) for seed_bins in seed_bin_maps)
        end_step = max(max(seed_bins) for seed_bins in seed_bin_maps)
    if start_step > end_step:
        return None

    bins_by_step = defaultdict(list)
    for seed_bins in seed_bin_maps:
        for binned_step, values in seed_bins.items():
            if binned_step < start_step or binned_step > end_step:
                continue
            bins_by_step[binned_step].append(float(np.mean(values)))

    rows = []
    for binned_step in sorted(bins_by_step):
        values = np.array(bins_by_step[binned_step], dtype=float)
        if values.size < min_seeds:
            continue
        std = float(np.std(values, ddof=1)) if values.size > 1 else 0.0
        stderr = float(std / math.sqrt(values.size)) if values.size else None
        ci95 = float(1.96 * stderr) if stderr is not None else None
        mean = float(np.mean(values))
        rows.append({
            "global_step": int(binned_step),
            "mean": mean,
            "std": std,
            "stderr": stderr,
            "ci95_low": mean - ci95 if ci95 is not None else None,
            "ci95_high": mean + ci95 if ci95 is not None else None,
            "seed_count": int(values.size),
            "min_seed_value": float(np.min(values)),
            "max_seed_value": float(np.max(values)),
            "step_bin": actual_step_bin,
            "shared_start_step": int(round(start_step)),
            "shared_end_step": int(round(end_step)),
            "available_seed_count": len(eligible),
        })
    return rows


def write_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def apply_plot_style(metric):
    plt.xlabel("Environment steps")
    plt.ylabel(METRIC_LABELS.get(metric, metric))
    if metric.endswith("win_rate"):
        plt.ylim(-0.03, 1.03)
    plt.grid(True, alpha=0.25, linewidth=0.6)


def plot_group_metric(output_dir, group_name, metric, variant_payloads, args):
    plt.figure(figsize=(8, 5), dpi=160)
    plotted = 0
    summary_rows = []
    variant_summaries = []
    for payload in variant_payloads:
        variant_name = payload["variant_name"]
        seed_series = payload["series"]
        aggregate = aggregate_by_step(
            seed_series,
            min_seeds=args.min_seeds,
            step_bin=args.step_bin,
            shared_range=not args.include_partial_range,
        )
        if not aggregate:
            continue
        xs = np.array([row["global_step"] for row in aggregate], dtype=float)
        means = np.array([row["mean"] for row in aggregate], dtype=float)
        stds = np.array([row["std"] for row in aggregate], dtype=float)
        ci_low = np.array([row["ci95_low"] for row in aggregate], dtype=float)
        ci_high = np.array([row["ci95_high"] for row in aggregate], dtype=float)
        counts = [row["seed_count"] for row in aggregate]

        label = f"{variant_name} (n={max(counts)})"
        plt.plot(xs, means, label=label, linewidth=1.8)
        if args.shade == "std":
            plt.fill_between(xs, means - stds, means + stds, alpha=0.18)
        elif args.shade == "ci95":
            plt.fill_between(xs, ci_low, ci_high, alpha=0.18)
        plotted += 1

        for row in aggregate:
            summary_rows.append({
                "group": group_name,
                "metric": metric,
                "variant": variant_name,
                "source_group": payload["source_group"],
                "source_variant": payload["source_variant"],
                **row,
            })
        variant_summaries.append({
            "variant": variant_name,
            "source_group": payload["source_group"],
            "source_variant": payload["source_variant"],
            "available_seed_count": len(seed_series),
            "plotted_points": len(aggregate),
            "step_bin": aggregate[0]["step_bin"],
            "shared_start_step": aggregate[0]["shared_start_step"],
            "shared_end_step": aggregate[0]["shared_end_step"],
        })

    if plotted == 0:
        plt.close()
        return None

    apply_plot_style(metric)
    if not args.no_title:
        plt.title(f"{group_name}: {METRIC_LABELS.get(metric, metric)}")
    plt.legend(fontsize=8)
    plt.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / f"{group_name}__{metric}.png"
    csv_path = output_dir / f"{group_name}__{metric}.csv"
    plt.savefig(image_path)
    plt.close()

    write_csv(csv_path, summary_rows, [
        "group", "metric", "variant", "source_group", "source_variant",
        "global_step", "mean", "std", "stderr", "ci95_low", "ci95_high",
        "seed_count", "available_seed_count", "min_seed_value", "max_seed_value",
        "step_bin", "shared_start_step", "shared_end_step",
    ])
    return {
        "image": str(image_path),
        "csv": str(csv_path),
        "group": group_name,
        "metric": metric,
        "variants": variant_summaries,
    }


def build_plots(args):
    registry = load_json(args.registry)
    output_dir = Path(args.output_dir)
    manifest = []
    for group in registry.get("experiment_groups", []):
        group_name = group["name"]
        metrics = GROUP_METRICS.get(group_name, ["episodic_return_mean", "training_win_rate"])
        variants = group.get("variants", [])
        for metric in metrics:
            payloads = []
            for variant in variants:
                if variant.get("implemented") is False and not variant.get("reuse_of"):
                    continue
                source_group, source_variant = variant_source(group_name, variant)
                series = collect_variant_series(args.runs_dir, source_group, source_variant, metric)
                if series:
                    payloads.append({
                        "variant_name": variant["name"],
                        "source_group": source_group,
                        "source_variant": source_variant,
                        "series": series,
                    })
            result = plot_group_metric(output_dir, group_name, metric, payloads, args)
            if result:
                manifest.append(result)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.txt").write_text(
        "\n".join(item["image"] for item in manifest) + ("\n" if manifest else ""),
        encoding="utf-8",
    )
    with open(output_dir / "manifest.json", "w", encoding="utf-8") as file:
        json.dump({
            "generated_at_utc": utc_now(),
            "runs_dir": str(Path(args.runs_dir)),
            "registry": str(Path(args.registry)),
            "alignment": "step_bin_shared_completed_range" if not args.include_partial_range else "step_bin_partial_range",
            "shade": args.shade,
            "min_seeds": args.min_seeds,
            "step_bin_override": args.step_bin,
            "plots": manifest,
        }, file, indent=2, ensure_ascii=True)
        file.write("\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Plot paper-style multi-seed training curves from JSONL logs.")
    parser.add_argument("--registry", default=str(ROOT / "experiment_registry.yaml"))
    parser.add_argument("--runs-dir", default=str(ROOT / "runs_multi_seed"))
    parser.add_argument("--output-dir", default=str(ROOT / "plots_draft" / "training_curves"))
    parser.add_argument("--min-seeds", type=int, default=2)
    parser.add_argument("--step-bin", type=int, default=None,
                        help="Override step bin width. Default: infer from target_step per variant.")
    parser.add_argument("--shade", choices=["ci95", "std", "none"], default="ci95")
    parser.add_argument("--include-partial-range", action="store_true",
                        help="Plot bins before all available seeds reached them. Paper figures should normally omit this.")
    parser.add_argument("--no-title", action="store_true")
    parsed = parser.parse_args()
    manifest = build_plots(parsed)
    print(f"wrote {len(manifest)} plot files")


if __name__ == "__main__":
    main()
