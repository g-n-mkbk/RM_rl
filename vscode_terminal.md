# VS Code 终端继承系统终端环境配置

本文档记录已验证成功的配置流程，用于让 VS Code 集成终端继承系统终端环境，并确保 Codex CLI 在 VS Code 终端中可以正常访问网络和启动 MCP。

## 目标

- VS Code 集成终端继承系统环境变量。
- VS Code 终端中 `codex-dh` 使用项目内稳定入口。
- Codex 启动时带有代理变量和 `nvm` 环境。
- ChatGPT/Codex VS Code 扩展的 `codex app-server` 进程也继承代理环境。

## 1. 开启 VS Code 终端环境继承

编辑 VS Code 用户配置：

```json
{
  "terminal.integrated.inheritEnv": true
}
```

配置文件位置：

```text
/home/xybuser/.config/Code/User/settings.json
```

## 2. 固化用户级代理环境

创建用户级 systemd 环境文件：

```text
/home/xybuser/.config/environment.d/10-codex-proxy.conf
```

内容：

```ini
HTTP_PROXY=http://127.0.0.1:7890/
HTTPS_PROXY=http://127.0.0.1:7890/
ALL_PROXY=socks://127.0.0.1:7890/
NO_PROXY=localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,::1
http_proxy=http://127.0.0.1:7890/
https_proxy=http://127.0.0.1:7890/
all_proxy=socks://127.0.0.1:7890/
no_proxy=localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,::1
NVM_DIR=/home/xybuser/.nvm
```

把当前环境导入用户级 systemd/dbus 会话：

```bash
systemctl --user import-environment HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy NVM_DIR PATH
dbus-update-activation-environment --systemd HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy NVM_DIR PATH
```

## 3. 在 Bash 中同步代理变量

在 `/home/xybuser/.bashrc` 中加入：

```bash
export HTTP_PROXY=http://127.0.0.1:7890/
export HTTPS_PROXY=http://127.0.0.1:7890/
export ALL_PROXY=socks://127.0.0.1:7890/
export NO_PROXY=localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,::1
export http_proxy=$HTTP_PROXY
export https_proxy=$HTTPS_PROXY
export all_proxy=$ALL_PROXY
export no_proxy=$NO_PROXY
```

## 4. 创建项目内 Codex 启动入口

创建：

```text
/home/xybuser/rl/RM_rl/.vscode/bin/codex-dh
```

内容：

```bash
#!/usr/bin/env bash
set -euo pipefail

export CODEX_HOME="$HOME/.codex_dh"

export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:7890/}"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7890/}"
export ALL_PROXY="${ALL_PROXY:-socks://127.0.0.1:7890/}"
export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,::1}"
export http_proxy="${http_proxy:-$HTTP_PROXY}"
export https_proxy="${https_proxy:-$HTTPS_PROXY}"
export all_proxy="${all_proxy:-$ALL_PROXY}"
export no_proxy="${no_proxy:-$NO_PROXY}"

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
fi

exec /home/xybuser/.nvm/versions/node/v24.14.0/bin/codex "$@"
```

赋予执行权限：

```bash
chmod +x /home/xybuser/rl/RM_rl/.vscode/bin/codex-dh
```

`.vscode/bin/codex` 只保留为兼容跳转脚本，日常命令使用 `codex-dh`。

## 5. 配置项目 VS Code 终端 PATH

编辑：

```text
/home/xybuser/rl/RM_rl/.vscode/settings.json
```

加入或合并：

```json
{
  "terminal.integrated.env.linux": {
    "PATH": "${workspaceFolder}/.vscode/bin:/home/xybuser/.nvm/versions/node/v24.14.0/bin:${env:PATH}",
    "HTTP_PROXY": "http://127.0.0.1:7890/",
    "HTTPS_PROXY": "http://127.0.0.1:7890/",
    "ALL_PROXY": "socks://127.0.0.1:7890/",
    "NO_PROXY": "localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,::1",
    "http_proxy": "http://127.0.0.1:7890/",
    "https_proxy": "http://127.0.0.1:7890/",
    "all_proxy": "socks://127.0.0.1:7890/",
    "no_proxy": "localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,::1"
  }
}
```

## 6. 配置 VS Code Tasks

编辑：

```text
/home/xybuser/rl/RM_rl/.vscode/tasks.json
```

使用项目内 wrapper 启动 Codex：

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Codex: Open CLI",
      "type": "shell",
      "command": "${workspaceFolder}/.vscode/bin/codex-dh",
      "options": {
        "cwd": "${workspaceFolder}"
      },
      "problemMatcher": [],
      "presentation": {
        "panel": "new",
        "focus": true,
        "clear": false
      }
    },
    {
      "label": "Codex: Resume Last Chat",
      "type": "shell",
      "command": "${workspaceFolder}/.vscode/bin/codex-dh resume --last",
      "options": {
        "cwd": "${workspaceFolder}"
      },
      "problemMatcher": [],
      "presentation": {
        "panel": "new",
        "focus": true,
        "clear": false
      }
    },
    {
      "label": "Codex: Pick Previous Chat",
      "type": "shell",
      "command": "${workspaceFolder}/.vscode/bin/codex-dh resume",
      "options": {
        "cwd": "${workspaceFolder}"
      },
      "problemMatcher": [],
      "presentation": {
        "panel": "new",
        "focus": true,
        "clear": false
      }
    }
  ]
}
```

## 7. 重启 VS Code

关闭旧 VS Code 进程，并从已配置环境重新打开项目：

```bash
pkill -TERM -x code
sleep 3
code /home/xybuser/rl/RM_rl
```

如果只改了终端设置，也可以在 VS Code 中执行：

```text
Developer: Reload Window
```

然后关闭旧终端标签页，重新创建一个新终端。

## 8. 验证

在新 VS Code 集成终端中运行：

```bash
which codex-dh
printf '%s\n' "$CODEX_HOME"
echo $HTTPS_PROXY
codex-dh --ask-for-approval never exec "say hello in Chinese"
```

成功结果应包含：

```text
/home/xybuser/rl/RM_rl/.vscode/bin/codex-dh
/home/xybuser/.codex_dh
http://127.0.0.1:7890/
你好！
```

## 9. 检查扩展进程环境

确认 ChatGPT/Codex 扩展的 app-server 进程继承代理：

```bash
ps -eo pid,ppid,tty,stat,lstart,cmd | rg "[c]odex app-server|[o]penai.chatgpt"
tr '\0' '\n' < /proc/<PID>/environ | rg "^(PATH|HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|NO_PROXY|http_proxy|https_proxy|all_proxy|no_proxy|NVM_DIR)="
```

成功时应看到 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 和 `NVM_DIR`。
