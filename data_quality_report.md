# Data Quality Report

Formal paper curves should use all objectively valid seeds. Do not keep only visually good seeds; exclude a run only for documented failures such as interruption, NaN/inf, corrupted logs, or missing checkpoints.

## framework_ablation
- MAPPO: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; implemented=False
  - Missing seeds: 0,1,2,3,4,5,6,7,8,9
- SERPPO: seeds=0,1,2,3,4,5,6,7,8,9; completed=10/10; final_steps=196618,196619,196622,196628,196631,196632,196635,196640,196645; train_log_rows=3
- SERPPO-noPD: seeds=0,1,2,3,4,5,6,7,8,9; completed=10/10; final_steps=196615,196620,196627,196630,196632,196634,196638,196653,196657; train_log_rows=3
- SERPPO-noAM: seeds=0,1,2,3,4,5,6,7,8,9; completed=10/10; final_steps=196610,196612,196625,196629,196630,196638,196640,196642,196644,196651; train_log_rows=3
- SERPPO-1DActionSpace: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; implemented=False
  - Missing seeds: 0,1,2,3,4,5,6,7,8,9
- SERPPO-noBO: seeds=0,1,2,3,4,5,6,7,8,9; completed=10/10; final_steps=196628,196629,196630,196641,196644,196645,196646,196647,196654; train_log_rows=3

## pseudo_termination
- SERPPO: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; reuse_of=framework_ablation/SERPPO
- SERPPO-noPD: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; reuse_of=framework_ablation/SERPPO-noPD

## obstacle_representation
- SERPPO-L: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; reuse_of=framework_ablation/SERPPO
- SERPPO-M: seeds=0,1,2,3,4,5,6,7,8,9; completed=10/10; final_steps=106535,106536,122939,180277,180286,180296,180298,180305; train_log_rows=13,15,22
- SERPPO-noBO: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; reuse_of=framework_ablation/SERPPO-noBO

## actor_critic_parameterization
- independent_actor_critic: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; reuse_of=framework_ablation/SERPPO
- partially_shared_actor_critic: seeds=0,1,2,3,4,5,6,7,8,9; completed=10/10; final_steps=131082,131091,131092,131093,131094,131098,131101,131103; train_log_rows=2

## reward_related_training_behavior
- SERPPO: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; reuse_of=framework_ablation/SERPPO
- MAPPO: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; implemented=False; reuse_of=framework_ablation/MAPPO

## recurrent_actor
- SERPPO: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; reuse_of=framework_ablation/SERPPO
- SERPPO-LSTM: seeds=0,1,2,3,4,5,6,7,8,9; completed=10/10; final_steps=131078,131079,131086,131089,131091,131099; train_log_rows=2
- SERPPO-GRU: seeds=0,1,2,3,4,5,6,7,8,9; completed=10/10; final_steps=131077,131084,131086,131087,131088,131089,131091,131097,131103,131106; train_log_rows=2

## future_observing_critic
- HO-SERPPO: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; reuse_of=recurrent_actor/SERPPO-LSTM
- HFO-SERPPO: seeds=0,1,2,3,4,5,6,7,8,9; completed=10/10; final_steps=131082,131083,131084,131086,131092,131093,131095,131097,131100; train_log_rows=2

## final_hfo_training
- HFO-SERPPO: seeds=none; completed=0/10; final_steps=none; train_log_rows=none; reuse_of=future_observing_critic/HFO-SERPPO

## External Evaluation Inventory
- table2_opponent_policy/HFO-SERPPO/HFO-SERPPO: completed=10/10; eval_episodes=100
- table2_opponent_policy/HFO-SERPPO/aggressive_bt: completed=10/10; eval_episodes=100
- table2_opponent_policy/HFO-SERPPO/defensive_bt: completed=10/10; eval_episodes=100
- table2_opponent_policy/HFO-SERPPO/random_action: completed=10/10; eval_episodes=100
- table2_opponent_policy/HFO-SERPPO/random_neural: completed=10/10; eval_episodes=100
- table2_opponent_policy/HFO-SERPPO/stationary: completed=10/10; eval_episodes=100

## Budget And Setting Checks
- Completed-run final_step values: 106535,106536,122939,131077,131078,131079,131082,131083,131084,131086,131087,131088,131089,131091,131092,131093,131094,131095,131097,131098,131099,131100,131101,131103,131106,180277,180286,180296,180298,180305,196610,196612,196615,196618,196619,196620,196622,196625,196627,196628,196629,196630,196631,196632,196634,196635,196638,196640,196641,196642,196644,196645,196646,196647,196651,196653,196654,196657
- Warning: completed runs do not all use the same training budget.
- Warning: 80 completed runs have fewer than 5 training log points. This usually means `target_step` is large relative to `break_step`, so curves are not paper-grade yet.
- Observed target_step to train_log_rows pairs: 65536->2,65536->3,8192->13,8192->15,8192->22
- Default-experiment opponents observed: mixed_bt
- Default-experiment arenas observed: original
- Default-experiment team sizes observed: 2v2

## Evaluation Summary
- table2_opponent_policy/HFO-SERPPO vs HFO-SERPPO: win_rate=0.2950 ci95=[0.2206,0.3694] n=10
- table2_opponent_policy/HFO-SERPPO vs aggressive_bt: win_rate=0.1180 ci95=[0.0723,0.1637] n=10
- table2_opponent_policy/HFO-SERPPO vs defensive_bt: win_rate=0.1490 ci95=[0.1064,0.1916] n=10
- table2_opponent_policy/HFO-SERPPO vs random_action: win_rate=0.2980 ci95=[0.2111,0.3849] n=10
- table2_opponent_policy/HFO-SERPPO vs random_neural: win_rate=0.2720 ci95=[0.1966,0.3474] n=10
- table2_opponent_policy/HFO-SERPPO vs stationary: win_rate=0.3520 ci95=[0.2460,0.4580] n=10
- training_eval/HFO-SERPPO vs HFO-SERPPO: win_rate=0.2947 ci95=[0.2207,0.3687] n=10
- training_eval/HFO-SERPPO vs aggressive_bt: win_rate=0.1178 ci95=[0.0722,0.1635] n=10
- training_eval/HFO-SERPPO vs defensive_bt: win_rate=0.1490 ci95=[0.1064,0.1916] n=10
- training_eval/HFO-SERPPO vs mixed_bt: win_rate=0.0991 ci95=[0.0482,0.1500] n=10
- training_eval/HFO-SERPPO vs random_action: win_rate=0.2980 ci95=[0.2111,0.3849] n=10
- training_eval/HFO-SERPPO vs random_neural: win_rate=0.2709 ci95=[0.1956,0.3461] n=10
- training_eval/HFO-SERPPO vs stationary: win_rate=0.3511 ci95=[0.2451,0.4570] n=10
- training_eval/SERPPO vs mixed_bt: win_rate=0.1155 ci95=[0.0775,0.1536] n=10
- training_eval/SERPPO-GRU vs mixed_bt: win_rate=0.1208 ci95=[0.0673,0.1743] n=10
- training_eval/SERPPO-LSTM vs mixed_bt: win_rate=0.1473 ci95=[0.0874,0.2072] n=10
- training_eval/SERPPO-M vs mixed_bt: win_rate=0.1556 ci95=[0.1096,0.2015] n=10
- training_eval/SERPPO-noAM vs mixed_bt: win_rate=0.0955 ci95=[0.0573,0.1337] n=10
- training_eval/SERPPO-noBO vs mixed_bt: win_rate=0.1614 ci95=[0.0702,0.2525] n=10
- training_eval/SERPPO-noPD vs mixed_bt: win_rate=0.1094 ci95=[0.0521,0.1667] n=10
## Reuse Notes
- `pseudo_termination/SERPPO` reuses `framework_ablation/SERPPO` when critic-loss fields are present.
- `pseudo_termination/SERPPO-noPD` reuses `framework_ablation/SERPPO-noPD` when critic-loss fields are present.
- `obstacle_representation/SERPPO-L` reuses default `framework_ablation/SERPPO` because default obstacle representation is lidar.
- `actor_critic_parameterization/independent_actor_critic` reuses default `framework_ablation/SERPPO`.
- `future_observing_critic/HO-SERPPO` reuses `recurrent_actor/SERPPO-LSTM`.
- `final_hfo_training/HFO-SERPPO` reuses `future_observing_critic/HFO-SERPPO`.

## Known Gaps
- MAPPO and SERPPO-1DActionSpace are marked unimplemented in the registry until their real training paths are completed.
- Arena 1/2/3 and disabled-robot team-size evaluation need exact environment switches before final robustness evaluation.
