import argparse
import json
import math
import os
import subprocess
import sys
import time
import traceback
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = Path(os.environ.get("RUNS_ROOT", ROOT / "runs_multi_seed")).expanduser()
DEFAULT_SEEDS = list(range(10))


def env_value(name, default=None):
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def override_value(overrides, name, variant, default):
    value = getattr(overrides, name, None)
    return value if value is not None else variant.get(name, default)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_registry(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def find_variant(registry, group_name, variant_name):
    for group in registry["experiment_groups"]:
        if group["name"] != group_name:
            continue
        for variant in group["variants"]:
            if variant["name"] == variant_name:
                merged = deepcopy(registry["defaults"])
                merged.update(deepcopy(group.get("defaults", {})))
                merged.update(deepcopy(variant))
                merged["experiment_group"] = group_name
                merged["variant_name"] = variant_name
                merged["reuse_of"] = variant.get("reuse_of")
                return merged
    raise KeyError(f"Unknown experiment/variant: {group_name}/{variant_name}")


def iter_train_variants(registry):
    seen = set()
    for group in registry["experiment_groups"]:
        for variant in group["variants"]:
            key = (group["name"], variant["name"])
            if key in seen or variant.get("reuse_of"):
                continue
            seen.add(key)
            yield group["name"], variant["name"], variant


def update_command_log(command, cwd=ROOT):
    command_log = ROOT / "command.md"
    with open(command_log, "a", encoding="utf-8") as file:
        file.write(f"\n## {datetime.now().astimezone().isoformat()}\n")
        file.write(f"- path: {cwd}\n")
        file.write("- command:\n```bash\n")
        file.write(command)
        file.write("\n```\n")


def git_text():
    lines = []
    for command in (["git", "rev-parse", "HEAD"], ["git", "status", "--short", "--branch"]):
        try:
            output = subprocess.check_output(command, cwd=ROOT, text=True, stderr=subprocess.STDOUT)
        except Exception as exc:
            output = f"<failed: {exc}>"
        lines.append("$ " + " ".join(command))
        lines.append(output.strip())
    return "\n".join(lines) + "\n"


def latest_checkpoint(checkpoint_dir):
    checkpoint_dir = Path(checkpoint_dir)
    preferred = [checkpoint_dir / "actor_best.pth", checkpoint_dir / "actor.pth"]
    for path in preferred:
        if path.exists():
            return str(path)
    candidates = sorted(checkpoint_dir.glob("actor_step:*.pth"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else None


def archive_existing_path(path):
    path = Path(path)
    if not path.exists():
        return None
    index = 0
    while True:
        candidate = path.with_name(f"{path.name}_bak{index}")
        if not candidate.exists():
            path.rename(candidate)
            return candidate
        index += 1


def contains_bad_number(record):
    for value in record.values():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return True
    return False


def scan_nan(path):
    path = Path(path)
    if not path.exists():
        return False
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            try:
                if contains_bad_number(json.loads(line)):
                    return True
            except json.JSONDecodeError:
                return True
    return False


class JsonlRunLogger:
    def __init__(self, run_dir, metadata, train_enabled=True):
        self.run_dir = Path(run_dir)
        self.metadata = metadata
        self.train_enabled = train_enabled
        self.train_log = self.run_dir / "train_log.jsonl"
        self.eval_log = self.run_dir / "eval_log.jsonl"
        self.checkpoint_dir = self.run_dir / "checkpoints"
        self.started_at = time.time()
        self.train_log_index = 0
        self.eval_log_index = 0
        self.previous_train_step = None

    def save(self, path):
        return None

    def log(self, data, step=None):
        train_index = self.train_log_index
        self.train_log_index += 1
        record = self._train_record(data, step, train_index)
        if self.train_enabled:
            with open(self.train_log, "a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n")
        if data.get("avgR_eval") is not None or data.get("red_win") is not None:
            eval_index = self.eval_log_index
            self.eval_log_index += 1
            eval_record = self._eval_record(data, step, record.get("checkpoint_path"), eval_index)
            with open(self.eval_log, "a", encoding="utf-8") as file:
                file.write(json.dumps(eval_record, ensure_ascii=True, allow_nan=False) + "\n")

    def _clean(self, value):
        if value is None:
            return None
        if isinstance(value, (int, str, bool)):
            return value
        if isinstance(value, float):
            return value if not (math.isnan(value) or math.isinf(value)) else None
        try:
            value = float(value)
            return value if not (math.isnan(value) or math.isinf(value)) else None
        except Exception:
            return value

    def _obstacle_reward(self, data):
        values = [data.get("reward_wheel_hit"), data.get("reward_hit_by_obstacle")]
        values = [self._clean(value) for value in values if value is not None]
        return sum(values) if values else None

    def _base_record(self, record_type, step, log_index):
        step_value = self._clean(step)
        return {
            "schema_version": "paper_curve_v2",
            "collector": "custom_jsonl",
            "collector_backend": "scripts.rm_experiment.JsonlRunLogger",
            "record_type": record_type,
            "log_index": log_index,
            "created_at_utc": utc_now(),
            "elapsed_seconds": self._clean(time.time() - self.started_at),
            "global_step": step_value,
            "env_step": step_value,
            "target_step": self.metadata["target_step"],
            "break_step": self.metadata["break_step"],
            "batch_size": self.metadata["batch_size"],
            "num_envs": self.metadata["num_envs"],
            "eval_gap_seconds": self.metadata["eval_gap_seconds"],
            "eval_times": self.metadata["eval_times"],
            "wandb_enabled": self.metadata["wandb_enabled"],
            "tensorboard_enabled": False,
            "log_frequency_unit": "ppo_update_after_target_step_rollout",
        }

    def _train_record(self, data, step, log_index):
        checkpoint_path = latest_checkpoint(self.checkpoint_dir)
        record = self._base_record("train_iteration", step, log_index)
        current_step = record.get("global_step")
        if current_step is not None and self.previous_train_step is not None:
            record["step_delta"] = self._clean(current_step - self.previous_train_step)
        else:
            record["step_delta"] = None
        self.previous_train_step = current_step
        record = {
            **record,
            "experiment_group": self.metadata["experiment_group"],
            "variant_name": self.metadata["variant_name"],
            "seed": self.metadata["seed"],
            "episode": self._clean(data.get("iteration") or data.get("Epoch")),
            "episodic_return": self._clean(data.get("avgR")),
            "episodic_return_mean": self._clean(data.get("avgR")),
            "training_win_rate": self._clean(data.get("win_rate_training")),
            "eval_win_rate": self._clean(data.get("red_win")),
            "critic_loss": self._clean(data.get("objC")),
            "value_loss": self._clean(data.get("value_loss") or data.get("objC")),
            "policy_loss": self._clean(data.get("objA")),
            "entropy_loss": self._clean(data.get("dist_entropy")),
            "approx_kl": self._clean(data.get("approx_kl")),
            "clip_fraction": self._clean(data.get("clip_fraction")),
            "shared_reward": self._clean(data.get("shared_reward")),
            "exclusive_reward": self._clean(data.get("exclusive_reward")),
            "total_reward": self._clean(data.get("total_reward") if data.get("total_reward") is not None else data.get("avgR")),
            "obstacle_related_reward": self._obstacle_reward(data),
            "episode_length": self._clean(data.get("avgS_eval")),
            "true_done_count": self._clean(data.get("true_done_count")),
            "truncation_count": self._clean(data.get("truncation_count")),
            "pseudo_termination_flag": self._clean(data.get("pseudo_termination_flag")),
            "action_mask_enabled": self.metadata["action_mask_enabled"],
            "pseudo_termination_enabled": self.metadata["pseudo_termination_enabled"],
            "obstacle_representation": self.metadata["obstacle_representation"],
            "actor_critic_parameterization": self.metadata["actor_critic_parameterization"],
            "recurrent_type": self.metadata["recurrent_type"],
            "future_observing_critic": self.metadata["future_observing_critic"],
            "opponent_policy": self.metadata["opponent_policy"],
            "arena_layout": self.metadata["arena_layout"],
            "team_size": self.metadata["team_size"],
            "checkpoint_path": checkpoint_path,
        }
        return {key: self._clean(value) for key, value in record.items()}

    def _eval_record(self, data, step, checkpoint_path, log_index):
        record = self._base_record("in_training_evaluation", step, log_index)
        record = {
            **record,
            "experiment_group": self.metadata["experiment_group"],
            "variant_name": self.metadata["variant_name"],
            "seed": self.metadata["seed"],
            "checkpoint_path": checkpoint_path,
            "eval_win_rate": self._clean(data.get("red_win")),
            "eval_return_mean": self._clean(data.get("avgR_eval")),
            "eval_return_std": self._clean(data.get("stdR_eval")),
            "opponent_policy": self.metadata["opponent_policy"],
            "arena_layout": self.metadata["arena_layout"],
            "team_size": self.metadata["team_size"],
            "rl_robot_count": self.metadata["rl_robot_count"],
            "enemy_count": self.metadata["enemy_count"],
        }
        return {key: self._clean(value) for key, value in record.items()}


def opponent_paths(name):
    mapping = {
        "mixed_bt": ["src.agents.handcrafted_enemy", "src.agents.retreat_enemy"],
        "aggressive_bt": ["src.agents.handcrafted_enemy"],
        "defensive_bt": ["src.agents.retreat_enemy"],
        "stationary": ["src.agents.static_enemy"],
        "random_action": ["src.agents.random_enemy"],
        "random_neural": ["src.agents.nn_enemy"],
        "MAPPO": ["src.agents.nn_enemy"],
        "HFO-SERPPO": ["src.agents.nn_enemy"],
        "mappo_policy": ["src.agents.nn_enemy"],
        "hfo_serppo_policy": ["src.agents.nn_enemy"],
    }
    if name not in mapping:
        raise ValueError(f"Unknown opponent policy: {name}")
    return mapping[name]


def build_env_args(variant, eval_mode=False):
    from robomaster2D.envs.options import Parameters

    params = Parameters()
    params.robot_r_num = int(variant.get("rl_robot_count", 2))
    params.robot_b_num = int(variant.get("enemy_count", 2))
    params.red_agents_path = ["src.agents.rl_trainer"]
    params.blue_agents_path = opponent_paths(variant.get("opponent_policy", "mixed_bt"))
    params.eval_blue_agents_path = opponent_paths(variant.get("eval_opponent_policy", variant.get("opponent_policy", "mixed_bt")))
    params.enable_blocks = bool(variant.get("enable_blocks", True))
    params.arena_layout = variant.get("arena_layout", "original")
    params.use_action_mask = bool(variant.get("action_mask_enabled", True))
    params.action_type = variant.get("action_type", "MultiDiscrete")
    params.reward_scheme = variant.get("reward_scheme", "serppo")

    obstacle = variant.get("obstacle_representation", "lidar")
    params.use_lidar = obstacle == "lidar"
    params.use_obstacle_map = obstacle == "local_map"

    if eval_mode:
        params.render = bool(variant.get("render_eval", False))
    return params


def build_training_args(variant, run_dir, seed, overrides):
    from elegantrl_dq.agents.AgentPPO import MultiEnvDiscretePPO
    from elegantrl_dq.envs.env import VecEnvironments
    from elegantrl_dq.train.run import Arguments

    args = Arguments(if_on_policy=True)
    args.agent = MultiEnvDiscretePPO()
    args.config.if_multi_processing = True
    args.config.new_processing_for_evaluation = False
    args.config.num_envs = int(override_value(overrides, "num_envs", variant, 10))
    args.config.if_wandb = bool(getattr(overrides, "wandb", False))
    args.config.wandb_project = env_value("WANDB_PROJECT", variant.get("wandb_project", "exbody_test"))
    args.config.wandb_user = env_value("WANDB_ENTITY", variant.get("wandb_entity", "goodnight-mkbk-northeastern-university"))
    args.config.wandb_group = env_value("WANDB_GROUP", variant.get("wandb_group", f"{variant['experiment_group']}/{variant['variant_name']}"))
    args.config.wandb_name = env_value("WANDB_NAME", variant.get("wandb_name", f"{variant['experiment_group']}__{variant['variant_name']}__seed_{seed}"))
    args.config.wandb_notes = env_value("WANDB_NOTES", variant.get("wandb_notes", "KBS graph rerun"))

    args.config.reward_scale = variant.get("reward_scale", 2 ** -1)
    args.config.net_dim = int(variant.get("net_dim", 256))
    args.config.gamma = float(variant.get("gamma", 0.998))
    args.config.batch_size = int(override_value(overrides, "batch_size", variant, 2 ** 13))
    args.config.critic_eval_batch_size = int(variant.get("critic_eval_batch_size", 512))
    args.config.repeat_times = int(variant.get("repeat_times", 4))
    args.config.repeat_times_policy = int(variant.get("repeat_times_policy", 4))
    args.config.target_step = int(override_value(overrides, "target_step", variant, 2 ** 16))
    args.config.learning_rate = float(variant.get("learning_rate", 2e-4))
    args.config.adaptive_entropy = bool(variant.get("adaptive_entropy", False))
    args.config.lambda_entropy = float(variant.get("lambda_entropy", 0.0))
    args.config.if_per_or_gae = bool(variant.get("pseudo_termination_enabled", True))
    args.config.if_allow_break = False
    args.config.break_step = int(override_value(overrides, "break_step", variant, 100000000))
    args.config.random_seed = int(seed)
    args.config.eval_times = int(override_value(overrides, "eval_times", variant, 20))
    args.config.eval_gap = int(override_value(overrides, "eval_gap", variant, 180))

    obstacle = variant.get("obstacle_representation", "lidar")
    args.config.if_use_cnn = obstacle in ("lidar", "local_map")
    args.config.if_use_rnn = variant.get("recurrent_type", "none") != "none"
    args.config.LSTM_or_GRU = variant.get("recurrent_type") == "lstm"
    args.config.sequence_length = int(variant.get("sequence_length", 8))
    args.config.if_share_network = variant.get("actor_critic_parameterization") == "partially_shared"
    args.config.if_print_time = True
    args.config.if_train = True

    args.config.self_play = False
    args.config.enemy_act_update_interval = int(variant.get("enemy_act_update_interval", 2 ** 12))
    args.config.model_pool_capacity_historySP = int(variant.get("model_pool_capacity_historySP", 1000))
    args.config.delta_historySP = float(variant.get("delta_historySP", 1.0))
    args.config.enemy_stochastic_policy = bool(variant.get("enemy_stochastic_policy", True))
    args.config.use_extra_state_for_critic = bool(variant.get("future_observing_critic", False))
    args.config.use_action_prediction = bool(variant.get("future_observing_critic", False))
    args.config.use_joint_action_head = variant.get("policy_action_head") == "joint_discrete"
    args.config.frame_stack_num = int(variant.get("frame_stack_num", 1))
    args.config.history_action_stack_num = int(variant.get("history_action_stack_num", 0))
    args.config.cwd = str((Path(run_dir) / "checkpoints").resolve())
    args.config.if_remove = False
    args.config.deterministic_torch = bool(getattr(overrides, "deterministic_torch", False))

    env_args = build_env_args(variant, eval_mode=False)
    eval_args = build_env_args(variant, eval_mode=True)
    pseudo_step = 1 if args.config.use_action_prediction else 0
    env_name = "Robomaster-v0"
    args.env = VecEnvironments(env_name, args.config.num_envs, pseudo_step=pseudo_step,
                               seed_offset=seed * 10000, env_args=env_args)
    args.env_eval = VecEnvironments(env_name, args.config.num_envs, seed_offset=seed * 100000,
                                    env_args=eval_args)
    args.agent.cri_target = False
    metadata = {
        "experiment_group": variant["experiment_group"],
        "variant_name": variant["variant_name"],
        "seed": seed,
        "eval_times": args.config.eval_times,
        "pseudo_termination_enabled": args.config.if_per_or_gae,
        "action_mask_enabled": env_args.use_action_mask,
        "obstacle_representation": variant.get("obstacle_representation", "lidar"),
        "actor_critic_parameterization": variant.get("actor_critic_parameterization", "independent"),
        "recurrent_type": variant.get("recurrent_type", "none"),
        "future_observing_critic": args.config.use_extra_state_for_critic,
        "opponent_policy": variant.get("opponent_policy", "mixed_bt"),
        "arena_layout": variant.get("arena_layout", "original"),
        "team_size": variant.get("team_size", "2v2"),
        "rl_robot_count": int(variant.get("rl_robot_count", 2)),
        "enemy_count": int(variant.get("enemy_count", 2)),
        "num_envs": args.config.num_envs,
        "target_step": args.config.target_step,
        "break_step": args.config.break_step,
        "batch_size": args.config.batch_size,
        "eval_gap_seconds": args.config.eval_gap,
        "wandb_enabled": args.config.if_wandb,
    }
    args.config.run_logger = JsonlRunLogger(run_dir, metadata)
    return args, env_args, metadata


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=True, allow_nan=False)
        file.write("\n")


def effective_training_config(config):
    keys = [
        "num_envs",
        "break_step",
        "target_step",
        "batch_size",
        "repeat_times",
        "repeat_times_policy",
        "eval_times",
        "eval_gap",
        "random_seed",
        "gamma",
        "reward_scale",
        "learning_rate",
        "if_per_or_gae",
        "if_use_cnn",
        "if_use_rnn",
        "LSTM_or_GRU",
        "if_share_network",
        "use_joint_action_head",
        "use_extra_state_for_critic",
        "use_action_prediction",
        "frame_stack_num",
        "history_action_stack_num",
        "deterministic_torch",
        "cwd",
    ]
    return {key: getattr(config, key) for key in keys if hasattr(config, key)}


def run_one(args):
    registry = load_registry(args.registry)
    variant = find_variant(registry, args.experiment_group, args.variant)
    if not variant.get("implemented", False):
        raise SystemExit(f"Variant is marked unimplemented in registry: {args.experiment_group}/{args.variant}")

    run_dir = RUNS_ROOT / args.experiment_group / args.variant / f"seed_{args.seed}"
    status_path = run_dir / "status.json"
    requested_break_step = int(override_value(args, "break_step", variant, 100000000))
    if status_path.exists() and not args.force:
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
            final_step = status.get("final_step") or 0
            if status.get("status") == "completed" and final_step >= requested_break_step:
                print(f"Skip completed run: {run_dir}")
                return 0
        except json.JSONDecodeError:
            pass
    if run_dir.exists() and not args.force:
        archived = archive_existing_path(run_dir)
        print(f"Archived existing incomplete run: {archived}")

    (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    (run_dir / "train_log.jsonl").touch(exist_ok=True)
    (run_dir / "eval_log.jsonl").touch(exist_ok=True)
    start_time = utc_now()
    write_json(status_path, {"status": "running", "start_time": start_time, "end_time": None,
                             "final_step": None, "final_checkpoint": None,
                             "has_nan": False, "error": None})

    try:
        training_args, env_args, metadata = build_training_args(variant, run_dir, args.seed, args)
        config_payload = {
            "metadata": metadata,
            "variant": variant,
            "effective_training_config": effective_training_config(training_args.config),
            "env_config": env_args.get_dict(),
            "worker_seeds": {
                "train": training_args.env.worker_seeds,
                "eval": training_args.env_eval.worker_seeds,
            },
            "command": " ".join(sys.argv),
            "created_at": start_time,
        }
        write_json(run_dir / "config.yaml", config_payload)
        (run_dir / "git_commit.txt").write_text(git_text(), encoding="utf-8")

        from elegantrl_dq.train.run import train_and_evaluate

        result = train_and_evaluate(training_args) or {}
        final_checkpoint = latest_checkpoint(run_dir / "checkpoints")
        has_nan = scan_nan(run_dir / "train_log.jsonl")
        write_json(status_path, {"status": "completed", "start_time": start_time, "end_time": utc_now(),
                                 "final_step": result.get("total_step"),
                                 "final_checkpoint": final_checkpoint,
                                 "has_nan": has_nan, "error": None})
        return 0
    except Exception as exc:
        error = traceback.format_exc()
        write_json(status_path, {"status": "failed", "start_time": start_time, "end_time": utc_now(),
                                 "final_step": None, "final_checkpoint": latest_checkpoint(run_dir / "checkpoints"),
                                 "has_nan": scan_nan(run_dir / "train_log.jsonl"),
                                 "error": error})
        print(error, file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run one RoboMaster paper experiment seed.")
    parser.add_argument("--registry", default=str(ROOT / "experiment_registry.yaml"))
    parser.add_argument("--experiment-group", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--num-envs", type=int, default=None)
    parser.add_argument("--break-step", type=int, default=None)
    parser.add_argument("--target-step", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--eval-times", type=int, default=None)
    parser.add_argument("--eval-gap", type=int, default=None)
    parser.add_argument("--wandb", action="store_true")
    parser.add_argument("--deterministic-torch", action="store_true")
    parser.add_argument("--force", action="store_true")
    parsed = parser.parse_args()
    os.chdir(ROOT)
    return run_one(parsed)


if __name__ == "__main__":
    raise SystemExit(main())
