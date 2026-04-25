# AGENTS.md

本文件是给 Codex、VSCode 助手、云端任务和协作者看的项目规则。所有自动化修改都应优先遵守这里的约定。

## 工作目录

- 项目根目录：`/home/xybuser/rl/RM_rl`
- 默认分支：`master`
- 远程仓库：`origin` 指向 fork 仓库

## 环境规则

- 所有运行命令都应在用户指定的虚拟环境中执行。
- 如果当前会话不知道虚拟环境名称或路径，只运行不会依赖 Python 环境的只读/文件管理命令；需要运行 Python、训练、测试、安装依赖前，先确认虚拟环境。
- 推荐在本地固定一个项目虚拟环境，例如：
  - Conda：`conda create -n rm-rl python=3.8`
  - venv：`python3 -m venv .venv`

## 命令日志

- 运行过的命令必须记录到项目根目录的 `command.md`。
- 记录格式：

```text
路径: /home/xybuser/rl/RM_rl
命令: git status --short --branch
```

- 如果一次执行多个命令，逐条记录。

## sudo 规则

- 需要使用 `sudo` 时，先尽量说明原因。
- 所有 `sudo` 命令必须记录到项目根目录的 `sudo_log.md`。
- 记录格式：

```text
路径: /home/xybuser/rl/RM_rl
命令: sudo apt install xxx
原因: 安装系统依赖
```

## 删除文件规则

- 删除任何文件或目录前必须先询问用户。
- 删除前必须创建备份，并说明备份路径。
- 未经用户明确同意，不执行 `rm`、`git clean`、`git reset --hard`、`git checkout -- <path>` 等可能丢失工作的命令。

## Git 规则

- 修改前先查看 `git status --short --branch`。
- 不覆盖用户已有改动。
- 推荐新功能和实验使用独立分支，例如 `work/codex-docs`。
- 小步提交，提交信息写清楚目的。
- 推送前检查：
  - `git status --short`
  - 必要时运行对应测试或最小验证命令

## 项目规范

- Python 代码保持现有风格，避免无关重构。
- 强化学习训练输出、模型权重、日志和大文件不要随意提交，除非用户明确要求。
- 新增文档优先放在 `docs/`。
- 与 GitHub/VSCode/Codex 工作流相关的说明优先维护：
  - `docs/CODEX_WORKFLOW.md`
  - `docs/GIT_WORKFLOW.md`

