# agit

AI-Powered Git CLI — Git's AI copilot.

> **缰绳始终在人手中** — 所有 AI 计划默认先展示，人类批准后才动手。

## 安装

```bash
pip install -e .
```

## 快速开始

```bash
# 1. 初始化（自动创建 git 仓库 + .agit 配置）
agit init

# 2. 配置 AI
agit config set ai.baseurl "https://api.openai.com/v1"
agit config set ai.model "gpt-4o"
agit config set ai.apikey "your-key"

# 3. 添加远程仓库
agit remote add https://github.com/user/repo.git

# 4. 开始使用
agit commit        # AI 辅助提交
agit sync          # 智能同步
agit doctor        # 仓库健康检查
```

## 命令速查

| 命令 | 说明 | 示例 |
|------|------|------|
| `agit init` | 初始化仓库 + agit 配置 | `agit init` |
| `agit add` | 暂存文件 | `agit add -A` / `agit add file.py` |
| `agit commit` | AI 辅助提交 | `agit commit` / `agit commit -m "msg"` |
| `agit sync` | 智能同步远程 | `agit sync` |
| `agit changelog` | AI 生成变更日志 | `agit changelog --from v1.0` |
| `agit explain` | 解读提交 | `agit explain HEAD~3..HEAD` |
| `agit review` | AI 代码审查 | `agit review` / `agit review --all` |
| `agit doctor` | 仓库健康检查 | `agit doctor` / `agit doctor --fix` |
| `agit agent` | 交互式 Agent | `agit agent "发布 v1.0.0"` |
| `agit remote` | 管理远程仓库 | `agit remote add URL` |
| `agit config` | 管理配置 | `agit config set ai.model gpt-4o` |
| `agit undo` | 回滚操作 | `agit undo` |
| `agit replay` | 重放历史 | `agit replay` |

## 配置

```bash
# 设置 AI 配置
agit config set ai.baseurl "https://api.deepseek.com/v1"
agit config set ai.model "deepseek-chat"
agit config set ai.apikey "your-key"

# 查看所有配置
agit config list

# 校验配置 + 测试 AI 连通性
agit config validate
```

### 环境变量

```bash
export AGIT_AI_APIKEY="your-key"
export AGIT_AI_BASEURL="https://api.openai.com/v1"
export AGIT_AI_MODEL="gpt-4o"
export AGIT_AI_PROVIDER="openai"  # openai | anthropic | ollama | custom
```

## 远程仓库管理

```bash
# 添加远程仓库（自动识别 GitHub/Gitee/GitLab）
agit remote add https://github.com/user/repo.git
agit remote add https://gitee.com/user/repo.git

# 自定义名称
agit remote add https://github.com/user/repo.git --name origin

# 查看 / 删除 / 重命名
agit remote ls
agit remote rm github
agit remote rename github origin

# 完整设置（添加 + 推送）
agit remote setup https://github.com/user/repo.git --push
```

## 国际化

```bash
# 中文（默认）
agit doctor

# 英文
agit -l en_US doctor
agit -l en_US config list
```

## 风险等级

| 等级 | 操作 | 处理策略 |
|------|------|----------|
| LOW | status, diff, log, show | 自动执行 |
| MEDIUM | add, stash, checkout | 自动执行 |
| HIGH | commit, push, tag | 用户批准后执行 |
| CRITICAL | force push, reset --hard | 二次确认 + 免责声明 |

## 详细文档

- [操作指南](docs/USAGE.md)
- [架构设计](document.md)
