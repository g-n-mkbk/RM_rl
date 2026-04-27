# Git 版本管理工作流

## 先理解几个概念

- 本地仓库：你电脑上的 `/home/xybuser/rl/RM_rl`。
- 远程仓库：GitHub 上的 fork，当前 `origin`。
- 分支：一条独立工作线。`master` 建议保持稳定，具体修改用工作分支。
- commit：一次可追踪的保存点。
- push：把本地 commit 上传到 GitHub。
- pull：把 GitHub 上的新 commit 拉到本地。

## 目标

这个项目的版本管理目标是：本地每完成一个小步骤就形成 commit，重要节点及时 push 到 GitHub。这样可以回溯历史版本，也能让 VSCode、云端 Codex 和其他机器通过 GitHub 同步。

不要理解成“每保存一个文件自动上传一次”。更稳妥的实时管理方式是小步提交：

- 修改前先看状态。
- 每完成一个独立动作就 commit。
- 每次准备换设备、让云端继续、或当天结束前 push。
- Python/训练/测试/安装命令先确认虚拟环境；纯 Git/文档命令不依赖虚拟环境。

## 第一次检查配置

```bash
git remote -v
git branch --show-current
git status --short --branch
```

如果还没有设置用户名和邮箱：

```bash
git config --global user.name "你的 GitHub 用户名"
git config --global user.email "你的邮箱"
```

GitHub 登录使用 GitHub CLI：

```bash
gh auth status
gh auth login -h github.com
gh auth setup-git
```

`gh auth login` 会打开网页登录或显示一次性验证码。账号密码、验证码、token 只由你自己输入，Codex 只负责启动命令和检查结果。

## 每次开始工作

```bash
git status --short --branch
git pull --ff-only origin master
git switch -c work/task-name
```

如果已经在工作分支：

```bash
git status --short --branch
git pull --ff-only
```

## 保存修改

```bash
git status --short
git diff
git add <files>
git commit -m "type: short description"
```

常见提交类型：

- `docs:` 文档
- `fix:` 修 bug
- `feat:` 新功能
- `test:` 测试
- `chore:` 工程配置

本项目建议把这些配置纳入版本管理：

- `.vscode/`
- `.codex`
- `AGENTS.md`
- `docs/`
- `command.md`
- `sudo_log.md`

提交前需要避免纳入这些内容：

- 虚拟环境目录，例如 `.venv/`、`venv/`
- Python 缓存，例如 `__pycache__/`
- 训练结果和模型权重，例如 `results/`、`runs/`、`*.pt`、`*.pth`
- 明文 token、密码、私钥、GitHub PAT

## 推送到 GitHub

首次推送新分支：

```bash
git push -u origin work/task-name
```

之后推送同一分支：

```bash
git push
```

## 从云端同步回本地

云端 Codex 修改并 push 后，本地执行：

```bash
git fetch origin
git status --short --branch
git pull --ff-only
```

如果你本地也有未提交改动，先不要强行 pull。先 `git status --short` 看清楚，必要时先 commit 或 stash。

## 高频版本管理节奏

工作时推荐使用这个节奏：

```bash
git status --short --branch
git diff
git add <files>
git commit -m "type: short description"
git push
```

如果是第一次推送当前分支：

```bash
git push -u origin HEAD
```

推荐提交频率：

- 改完一组相关文档后提交一次。
- 改完一个 bug 后提交一次。
- 训练脚本或核心逻辑改动前后分别提交。
- 长时间实验前先提交并 push，方便回退。

## 新手安全线

- 不确定时先运行 `git status --short --branch`。
- 不懂一个命令是否会删东西时，先问。
- 不要轻易使用：
  - `git reset --hard`
  - `git clean -fd`
  - `rm -rf`
  - `git push --force`
