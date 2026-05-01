# Current Parallelism Assessment

Captured at 2026-04-30 23:14 local time while `framework_ablation/SERPPO/seed_0` was running.

## Current Snapshot

- GPU: RTX 4070 Laptop GPU
- GPU utilization: about 34%
- GPU memory: 1383 / 8188 MiB
- GPU temperature: 52 C
- CPU: about 69% busy, about 31% idle
- Load average: 21.78, 20.49, 17.01
- Memory: 31 GiB total, about 21 GiB available
- Current run: 10 environment workers plus trainer/evaluator process
- Current speed: about 219 env steps/s

## Interpretation

This workload is CPU-heavy. The GPU has spare memory and only moderate utilization, but the environment workers are already consuming many CPU cores. Starting a second full `NUM_ENVS=10` experiment on this local machine would likely compete for CPU first, and the total throughput per experiment would probably drop sharply.

## When A Second Experiment Is Reasonable

On a single GPU, only consider a second experiment if all of these are true:

- GPU memory used is below about 45% of total.
- GPU utilization is below about 55% most of the time.
- CPU idle is above about 35% for several minutes.
- Load average is below the approximate physical core count.
- Current run FPS does not drop by more than about 15% after starting the second job.

For this local snapshot, the GPU side looks permissive, but the CPU/load side is already high. Do not start a second full experiment here.

## Safer 4090 Rule

On a rented single RTX 4090 with more VRAM, two concurrent experiments may be acceptable only if CPU is also strong enough. Start with:

```bash
NUM_ENVS=5
```

for each concurrent experiment, monitor `nvidia-smi`, `top` or `htop`, and compare FPS in the terminal. If either run slows down heavily, return to one experiment at a time.
