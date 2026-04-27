# VSCode Codex 迁移说明

这份文档记录本仓库中和 VSCode/Codex 目录迁移有关的路径、配置点、校验命令和注意事项。目标是下一次迁移 Codex 配置目录时，新的 agent 可以按清单处理，不漏掉 VSCode 扩展、终端环境、项目 wrapper 和全局规则。

## 核心原则

- 当前账户的 Codex 配置目录固定为 `/home/xybuser/.codex_dh`。
- CLI 入口固定使用 `/home/xybuser/.local/bin/codex-dh` 或 `codex-dh`。
- 不允许修改 `/home/xybuser/.codex` 内任何文件；如果 VSCode/Codex 仍指向默认目录，只能改工具配置或启动环境指向 `/home/xybuser/.codex_dh`。
- 不使用复制、覆盖、软链接等方式让 `/home/xybuser/.codex` 兼容新目录。

## 当前路径清单

| 用途 | 路径 | 当前要求 |
| --- | --- | --- |
| 账号级 Codex 规则 | `/home/xybuser/.codex_dh/AGENTS.md` | 保留通用规则、`codex-dh`、`CODEX_HOME`、禁止修改默认目录、Git 同步规则 |
| 全局 CLI wrapper | `/home/xybuser/.local/bin/codex-dh` | 导出 `CODEX_HOME=/home/xybuser/.codex_dh` 后执行真实 Codex CLI |
| VSCode 用户设置 | `/home/xybuser/.config/Code/User/settings.json` | `chatgpt.cliExecutable` 指向 `codex-dh`，`codex.localEnvironmentConfigPath` 指向 `.codex_dh/AGENTS.md` |
| 用户环境变量 | `/home/xybuser/.config/environment.d/10-codex-proxy.conf` | 设置 `CODEX_HOME=/home/xybuser/.codex_dh`，供桌面会话和 VSCode 进程继承 |
| 项目 VSCode 设置 | `.vscode/settings.json` | VSCode 终端环境中设置 `CODEX_HOME=/home/xybuser/.codex_dh` |
| 项目 CLI wrapper | `.vscode/bin/codex-dh` | 转发到 `/home/xybuser/.local/bin/codex-dh` |
| 项目兼容 wrapper | `.vscode/bin/codex` | 仅转发到同目录的 `codex-dh`，避免项目任务误用默认配置目录 |
| 项目任务 | `.vscode/tasks.json` | Codex 相关任务使用 `.vscode/bin/codex-dh` |
| 已安装 VSCode 扩展 | `/home/xybuser/.vscode/extensions/openai.chatgpt-26.422.30944-linux-x64/out/extension.js` | 如扩展 UI 硬编码默认路径，需要把 fallback 从 `.codex` 改为 `.codex_dh` |

## 迁移步骤

1. 更新 `/home/xybuser/.codex_dh/AGENTS.md`。
   - 确认包含 `CODEX_HOME=/home/xybuser/.codex_dh`。
   - 确认包含必须使用 `codex-dh` 的规则。
   - 确认包含禁止修改 `/home/xybuser/.codex` 的规则。

2. 创建或校验全局 wrapper `/home/xybuser/.local/bin/codex-dh`。
   - wrapper 内必须导出 `CODEX_HOME=/home/xybuser/.codex_dh`。
   - wrapper 最后执行真实 Codex CLI。
   - 不要把真实 CLI 入口改成裸 `codex` 的常规使用方式。

3. 更新 VSCode 用户设置 `/home/xybuser/.config/Code/User/settings.json`。
   - `chatgpt.cliExecutable` 应为 `/home/xybuser/.local/bin/codex-dh`。
   - `codex.localEnvironmentConfigPath` 应为 `/home/xybuser/.codex_dh/AGENTS.md`。
   - 不要把用户设置中的 token、密钥或其他私人配置复制到仓库文档。

4. 更新用户环境 `/home/xybuser/.config/environment.d/10-codex-proxy.conf`。
   - 确认包含 `CODEX_HOME=/home/xybuser/.codex_dh`。
   - 修改后需要重新登录桌面会话，或至少重启 VSCode 窗口和 Codex 扩展相关进程。

5. 更新项目 `.vscode`。
   - `.vscode/settings.json` 的 `terminal.integrated.env.linux.CODEX_HOME` 指向 `/home/xybuser/.codex_dh`。
   - `.vscode/bin/codex-dh` 转发到 `/home/xybuser/.local/bin/codex-dh`。
   - `.vscode/bin/codex` 只做项目内兼容转发，不直接使用默认配置目录。
   - `.vscode/tasks.json` 的 Codex 任务使用 `.vscode/bin/codex-dh`。

6. 必要时修补已安装的 VSCode 扩展 fallback。
   - 先备份扩展文件，例如 `extension_bak0.js`、`extension_bak1.js`。
   - 只修改当前加载的 `out/extension.js`，不要修改 `/home/xybuser/.codex`。
   - 将扩展中用于本地配置目录 fallback 的 `.codex` 改为 `.codex_dh`。
   - VSCode 扩展升级后路径和文件可能变化，需要重新检查新版本目录。

7. 重启 VSCode。
   - 优先执行完整窗口重载。
   - 如果设置页仍显示旧路径，再重启 VSCode 主进程或检查扩展缓存/状态。
   - 不要通过软链接或复制文件修正旧路径显示。

## 校验命令

以下命令用于迁移后核查。项目规则要求运行命令时同步记录到 `command.md`。

```bash
command -v codex-dh
codex-dh --version
printf '%s\n' "$CODEX_HOME"
rg -n "chatgpt.cliExecutable|codex.localEnvironmentConfigPath" /home/xybuser/.config/Code/User/settings.json
rg -n "CODEX_HOME|codex-dh" .vscode /home/xybuser/.local/bin/codex-dh /home/xybuser/.config/environment.d/10-codex-proxy.conf
node -e 'const fs=require("fs"); const p="/home/xybuser/.vscode/extensions/openai.chatgpt-26.422.30944-linux-x64/out/extension.js"; const s=fs.readFileSync(p,"utf8"); console.log({homedirCodex:(s.match(/homedir\\(\\),".codex"/g)||[]).length,homedirCodexDh:(s.match(/homedir\\(\\),".codex_dh"/g)||[]).length,homeCodex:(s.match(/HOME \\? path\\.join\\(env\\.HOME, ".codex"/g)||[]).length,homeCodexDh:(s.match(/HOME \\? path\\.join\\(env\\.HOME, ".codex_dh"/g)||[]).length,localEnvConfig:(s.match(/localEnvironmentConfigPath/g)||[]).length});'
```

期望结果：

- `codex-dh` 可以找到并运行。
- VSCode 终端内 `CODEX_HOME` 输出 `/home/xybuser/.codex_dh`。
- VSCode 用户设置中的两个 Codex 路径都指向 `/home/xybuser/.codex_dh` 或 `codex-dh`。
- 当前加载的扩展 `extension.js` 中，本地目录 fallback 使用 `.codex_dh`。

## 常见遗漏点

- 只改 `chatgpt.cliExecutable` 不一定能改掉设置页显示路径，因为设置页可能还读取扩展宿主进程环境或扩展内部 fallback。
- `environment.d` 修改后，已经启动的 VSCode 进程不会自动继承新环境。
- `extension_bak*.js` 是备份文件，可能仍包含旧字符串；检查当前行为时以正在加载的 `out/extension.js` 为准。
- VSCode 扩展升级可能覆盖 `out/extension.js`，升级后要重新跑校验命令。
- 任何时候都不要为了兼容 UI 显示去创建 `/home/xybuser/.codex/AGENTS.md` 软链接。

## 文档归档建议

- 账号级长期规则只放在 `/home/xybuser/.codex_dh/AGENTS.md`，避免项目文档重复维护。
- VSCode/Codex 路径迁移说明统一放在本文件：`docs/vscode_trans.md`。
- 项目专属规则保留在仓库根目录 `AGENTS.md`，只写本项目环境、训练输出、文档位置等内容。
- 命令审计保留在仓库根目录 `command.md`，sudo 审计保留在 `sudo_log.md`。
- 真实配置文件仍保留在各自原生位置，不建议把完整配置内容复制进仓库，尤其不要提交密钥、token、账号信息。
- 如果后续文档继续增加，建议新建 `docs/CONFIG_INDEX.md` 作为索引，只列出配置路径、用途和指向文档，不重复粘贴配置正文。
