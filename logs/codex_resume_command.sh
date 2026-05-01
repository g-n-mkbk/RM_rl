#!/usr/bin/env bash
set -euo pipefail
cd "/home/xybuser/rl/RM_rl"
export CODEX_HOME="${CODEX_HOME:-/home/xybuser/.codex_dh}"
codex-dh run "$(cat "/home/xybuser/rl/RM_rl/docs/codex_resume_prompt.md")"
