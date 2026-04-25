# sudo_log.md

本文件记录项目中需要使用 `sudo` 的命令。

当前尚未运行任何 `sudo` 命令。

## 2026-04-26

```text
路径: /home/xybuser/rl/RM_rl
命令: sudo apt-get update && sudo apt-get install -y gh
原因: 安装 GitHub CLI
结果: 未执行安装，sudo 需要交互式密码，已中止；随后改用用户目录本地安装。
```


路径: /home/xybuser/rl/RM_rl
命令: sudo apt update
原因: 安装 GitHub CLI gh 前刷新软件源

路径: /home/xybuser/rl/RM_rl
命令: sudo apt install -y gh
原因: 安装 GitHub CLI，用于认证并推送当前分支到 GitHub
