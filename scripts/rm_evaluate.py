import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace

import torch

from rm_experiment import (ROOT, JsonlRunLogger, build_training_args, find_variant,
                           latest_checkpoint, load_registry, utc_now, write_json)


NEURAL_OPPONENTS = {"random_neural", "MAPPO", "HFO-SERPPO", "mappo_policy", "hfo_serppo_policy"}


def source_for_policy(policy):
    if policy == "HFO-SERPPO":
        return "future_observing_critic", "HFO-SERPPO"
    if policy == "SERPPO":
        return "framework_ablation", "SERPPO"
    raise ValueError(f"Policy evaluation is not wired yet for {policy}")


def load_actor(path, actor):
    state = torch.load(path, map_location=lambda storage, loc: storage)
    actor.load_state_dict(state)


def evaluate_one(args):
    registry = load_registry(args.registry)
    source_group, source_variant = args.source_group, args.source_variant
    if args.policy and (not source_group or not source_variant):
        source_group, source_variant = source_for_policy(args.policy)
    if not source_group or not source_variant:
        raise SystemExit("Provide --policy or both --source-group and --source-variant.")

    variant = find_variant(registry, source_group, source_variant)
    if not variant.get("implemented", False):
        raise SystemExit(f"Source variant is marked unimplemented: {source_group}/{source_variant}")
    variant["opponent_policy"] = args.opponent
    variant["eval_opponent_policy"] = args.opponent
    variant["eval_times"] = args.eval_episodes

    run_dir = ROOT / "runs_multi_seed" / source_group / source_variant / f"seed_{args.seed}"
    checkpoint = args.checkpoint or latest_checkpoint(run_dir / "checkpoints")
    if not checkpoint:
        raise SystemExit(f"No checkpoint found for {run_dir}")

    overrides = SimpleNamespace(num_envs=args.num_envs, break_step=None,
                                eval_times=args.eval_episodes, eval_gap=0,
                                wandb=False, deterministic_torch=args.deterministic_torch)
    training_args, _env_args, metadata = build_training_args(variant, run_dir, args.seed, overrides)
    metadata["experiment_group"] = args.eval_name
    metadata["variant_name"] = args.policy or source_variant
    metadata["opponent_policy"] = args.opponent
    metadata["eval_times"] = args.eval_episodes

    training_args.init_before_training()
    env = training_args.env
    env_eval = training_args.env_eval
    config = training_args.config
    agent = training_args.agent

    env.init(config.frame_stack_num, config.history_action_stack_num, config.if_use_cnn)
    env_eval.init(config.frame_stack_num, config.history_action_stack_num, config.if_use_cnn)

    action_prediction_dim = env.action_dim.copy()
    action_prediction_dim += 1
    extra_state_kwargs = {
        "use_extra_state_for_critic": config.use_extra_state_for_critic,
        "use_action_prediction": config.use_action_prediction,
        "agent_num": env.args.robot_r_num + env.args.robot_b_num,
        "action_prediction_dim": action_prediction_dim,
    }
    train_args = {"adaptive_entropy": config.adaptive_entropy,
                  "dual_clip": config.dual_clip}
    self_play_args = {
        "self_play": False,
        "if_build_enemy_act": args.opponent in NEURAL_OPPONENTS,
        "enemy_policy_share_memory": False,
        "enemy_act_update_interval": config.enemy_act_update_interval,
        "self_play_mode": config.self_play_mode,
        "delta_historySP": config.delta_historySP,
        "model_pool_capacity_historySP": config.model_pool_capacity_historySP,
        "enemy_stochastic_policy": False if args.opponent in NEURAL_OPPONENTS else config.enemy_stochastic_policy,
    }
    rnn_kwargs = {"if_use_rnn": config.if_use_rnn,
                  "LSTM_or_GRU": config.LSTM_or_GRU,
                  "rnn_hidden_size": config.rnn_hidden_size,
                  "sequence_length": config.sequence_length}
    evaluation_kwargs = {"cwd": str(run_dir / "checkpoints"),
                         "eval_times": args.eval_episodes,
                         "eval_gap": 0,
                         "save_interval": config.save_interval,
                         "stochastic_policy_or_deterministic": config.stochastic_policy_or_deterministic}

    agent.init(config.net_dim, env.state_dim, env.action_dim, config.learning_rate, gamma=config.gamma,
               if_use_gae=config.if_per_or_gae, max_step=env.max_step,
               if_use_conv1D=env.args.use_lidar, env=env, if_use_cnn=config.if_use_cnn,
               if_share_network=config.if_share_network, if_new_proc_eval=False,
               observation_matrix_shape=env.observation_matrix_shape,
               **train_args, **self_play_args, **extra_state_kwargs, **rnn_kwargs, **evaluation_kwargs)
    load_actor(checkpoint, agent.act)
    if args.enemy_checkpoint and agent.enemy_act is not None:
        load_actor(args.enemy_checkpoint, agent.enemy_act)
    elif args.opponent in {"HFO-SERPPO", "hfo_serppo_policy"} and agent.enemy_act is not None:
        load_actor(checkpoint, agent.enemy_act)

    logger = JsonlRunLogger(run_dir, metadata, train_enabled=False)
    status_dir = ROOT / "eval_results" / args.eval_name / (args.policy or source_variant) / args.opponent / f"seed_{args.seed}"
    status_dir.mkdir(parents=True, exist_ok=True)
    write_json(status_dir / "status.json", {"status": "running", "start_time": utc_now(),
                                            "seed": args.seed, "checkpoint": checkpoint,
                                            "opponent": args.opponent})
    try:
        agent.evaluate(env_eval, if_save=False, steps=args.global_step, log_tuple=[0, 0, 0, 0, 0, 0], logger=logger)
        write_json(status_dir / "status.json", {"status": "completed", "end_time": utc_now(),
                                                "seed": args.seed, "checkpoint": checkpoint,
                                                "opponent": args.opponent})
    finally:
        env.stop()
        if env_eval is not env and hasattr(env_eval, "stop"):
            env_eval.stop()
    return 0


def main():
    parser = argparse.ArgumentParser(description="Evaluate one trained RoboMaster policy seed.")
    parser.add_argument("--registry", default=str(ROOT / "experiment_registry.yaml"))
    parser.add_argument("--eval-name", required=True)
    parser.add_argument("--policy", default="HFO-SERPPO")
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--source-group", default=None)
    parser.add_argument("--source-variant", default=None)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--enemy-checkpoint", default=None)
    parser.add_argument("--eval-episodes", type=int, default=100)
    parser.add_argument("--num-envs", type=int, default=10)
    parser.add_argument("--global-step", type=int, default=0)
    parser.add_argument("--deterministic-torch", action="store_true")
    parsed = parser.parse_args()
    os.chdir(ROOT)
    return evaluate_one(parsed)


if __name__ == "__main__":
    raise SystemExit(main())
