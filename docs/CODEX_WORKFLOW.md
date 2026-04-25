# VSCode Codex 与云端 Codex 对齐指南

这份文档用于把本地 VSCode、GitHub fork、云端 Codex 的工作方式对齐。核心原则是：GitHub 仓库是同步中心，本地和云端都通过提交、推送、拉取来同步代码。

## 三者关系

- 本地 VSCode：你电脑上的真实工作目录，适合调试、训练、看终端输出、操作文件。
- GitHub fork：同步中心，云端和本地都应以它为准。
- 云端 Codex：通常从 GitHub 拉取仓库快照，在云端环境中修改，再通过 commit、push 或 PR 回到 GitHub。

云端看到的项目不是自动读取你本地硬盘，而是读取 GitHub 上的仓库和分支。你本地没有 push 的改动，云端默认看不到；云端没有 push 的改动，你本地默认也看不到。

## 推荐日常流程

1. 本地开始工作前：

```bash
git status --short --branch
git pull --ff-only origin master
```

2. 创建工作分支：

```bash
git switch -c work/your-task-name
```

3. 在 VSCode 或 Codex 中修改代码。

4. 本地验证：

```bash
git status --short
```

5. 提交并推送：

```bash
git add <changed-files>
git commit -m "docs: add codex workflow"
git push -u origin work/your-task-name
```

6. 在 GitHub 上开 Pull Request，或让云端 Codex 基于这个分支继续工作。

## VSCode 推荐设置

建议安装：

- GitHub Pull Requests and Issues
- Python
- Pylance
- Codex 或 OpenAI/Codex 相关扩展

建议习惯：

- VSCode 打开项目根目录 `/home/xybuser/rl/RM_rl`。
- VSCode 终端先激活虚拟环境，再执行 Python/训练/测试命令。
- 每次开始前先 `git pull --ff-only`，每次结束前 commit + push。

## 是否需要 CLI 版 Codex

不是必须，但推荐安装，尤其当你想在本地终端里使用 Codex、让它直接操作当前仓库时。

适合安装 CLI 的情况：

- 你希望 Codex 在本地 Ubuntu 环境里运行命令。
- 你希望看到所有命令输出都出现在本地终端。
- 你希望它使用本机 GPU、conda 环境、数据集和已安装依赖。

不安装 CLI 也可以：

- VSCode 扩展可以辅助编辑。
- 云端 Codex 可以处理 GitHub 仓库里的任务。

## 关于“能否打开 VSCode 里的终端”

云端或网页会话不能直接控制你已经打开的 VSCode 终端标签页。只有在本地 VSCode 插件或本地 CLI 授权的情况下，Codex 才能在你的本机终端环境里执行命令。

如果你希望命令都显示在 VSCode 终端中，推荐流程是：

1. 在 VSCode 中打开本仓库。
2. 打开 VSCode 内置终端。
3. 激活虚拟环境。
4. 使用本地 Codex CLI 或 VSCode Codex 扩展发出任务。

## 虚拟环境建议

如果项目还没有固定环境文件，建议先选择一种：

Conda：

```bash
conda create -n rm-rl python=3.8
conda activate rm-rl
pip install -e .
pip install -e ./robomaster2D
```

venv：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e ./robomaster2D
```

如果后续确认依赖版本，再补充 `requirements.txt` 或 `environment.yml`。

