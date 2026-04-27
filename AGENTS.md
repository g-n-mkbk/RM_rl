# AGENTS.md

本文件只保留 `/home/xybuser/rl/RM_rl` 的项目专属规则。账号级通用规则放在 `/home/xybuser/.codex_dh/AGENTS.md`，包括命令日志、sudo 日志、删除备份、visible-command、`codex-dh` 与 `CODEX_HOME` 规则。

## 工作目录

- 项目根目录：`/home/xybuser/rl/RM_rl`
- 默认分支：`master`
- 远程仓库：`origin` 指向 fork 仓库

## 项目环境

- 如果当前会话不知道虚拟环境名称或路径，只运行不会依赖 Python 环境的只读/文件管理命令；需要运行 Python、训练、测试、安装依赖前，先确认虚拟环境。
- 推荐在本地固定一个项目虚拟环境，例如：
  - Conda：`conda create -n rm-rl python=3.8`
  - venv：`python3 -m venv .venv`

## 项目规范

- Python 代码保持现有风格，避免无关重构。
- 强化学习训练输出、模型权重、日志和大文件不要随意提交，除非用户明确要求。
- 新增文档优先放在 `docs/`。
