# Git 新手工作流

## 先理解几个概念

- 本地仓库：你电脑上的 `/home/xybuser/rl/RM_rl`。
- 远程仓库：GitHub 上的 fork，当前 `origin`。
- 分支：一条独立工作线。`master` 建议保持稳定，具体修改用工作分支。
- commit：一次可追踪的保存点。
- push：把本地 commit 上传到 GitHub。
- pull：把 GitHub 上的新 commit 拉到本地。

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

## 新手安全线

- 不确定时先运行 `git status --short --branch`。
- 不懂一个命令是否会删东西时，先问。
- 不要轻易使用：
  - `git reset --hard`
  - `git clean -fd`
  - `rm -rf`
  - `git push --force`

