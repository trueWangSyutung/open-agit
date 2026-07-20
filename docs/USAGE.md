# agit 操作指南

## 目录

- [1. 安装与初始化](#1-安装与初始化)
- [2. 配置 AI](#2-配置-ai)
- [3. 远程仓库管理](#3-远程仓库管理)
- [4. 日常开发流程](#4-日常开发流程)
- [5. 发布流程](#5-发布流程)
- [6. 代码审查](#6-代码审查)
- [7. 仓库健康检查](#7-仓库健康检查)
- [8. Agent 模式](#8-agent-模式)
- [9. 回滚与重放](#9-回滚与重放)
- [10. 国际化](#10-国际化)

---

## 1. 安装与初始化

### 安装

```bash
pip install -e .
```

### 初始化

```bash
agit init
```

自动完成：
- 创建 `.git/` 仓库（如果不存在）
- 创建 `.agit/` 目录（config, history, snapshots）
- 生成默认配置文件 `.agit/config.toml`
- 更新 `.gitignore`

---

## 2. 配置 AI

### 方式一：命令行配置

```bash
# DeepSeek
agit config set ai.baseurl "https://api.deepseek.com/v1"
agit config set ai.model "deepseek-chat"
agit config set ai.apikey "sk-xxxx"

# OpenAI
agit config set ai.baseurl "https://api.openai.com/v1"
agit config set ai.model "gpt-4o"
agit config set ai.apikey "sk-xxxx"

# Ollama（本地）
agit config set ai.baseurl "http://localhost:11434/v1"
agit config set ai.model "llama3"
```

### 方式二：环境变量

```bash
export AGIT_AI_APIKEY="sk-xxxx"
export AGIT_AI_BASEURL="https://api.deepseek.com/v1"
export AGIT_AI_MODEL="deepseek-chat"
```

### 方式三：编辑配置文件

```bash
vim .agit/config.toml
```

```toml
[ai]
baseurl    = "https://api.deepseek.com/v1"
model      = "deepseek-chat"
apikey     = ""
provider   = "openai"
timeout    = 30
temperature = 0.3
```

### 验证配置

```bash
agit config validate    # 校验配置 + 测试 AI 连通性
agit config list        # 查看所有配置及来源
agit config get ai.model
```

---

## 3. 远程仓库管理

### 添加远程仓库

```bash
# 自动识别平台，命名为 github/gitee/gitlab
agit remote add https://github.com/user/repo.git
agit remote add https://gitee.com/user/repo.git
agit remote add https://gitlab.com/user/project.git

# 自定义名称
agit remote add https://github.com/user/repo.git --name origin

# SSH 地址
agit remote add git@github.com:user/repo.git
```

### 查看远程仓库

```bash
agit remote ls
```

输出示例：
```
                    Remotes
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name   ┃ URL                      ┃ Type        ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ github │ https://github.com/...   │ fetch (HTTPS)│
│ github │ https://github.com/...   │ push (HTTPS) │
└────────┴──────────────────────────┴──────────────┘
```

### 其他操作

```bash
agit remote rm github              # 删除
agit remote rename github origin   # 重命名
agit remote set-url github https://github.com/user/new-repo.git  # 修改 URL

# 完整设置（添加 + 推送当前分支）
agit remote setup https://github.com/user/repo.git --push
```

---

## 4. 日常开发流程

### 标准流程

```bash
# 1. 写代码
vim src/app.py

# 2. 暂存文件
agit add src/app.py
# 或暂存所有修改
agit add -A

# 3. AI 辅助提交
agit commit
```

### agit commit 交互流程

```
→ 正在分析暂存区变更...
→ 正在发送 3 个文件到 gpt-4o

╭─────────── Commit Proposal ────────────╮
│ feat(auth): add OAuth2 refresh rotation │
│                                         │
│ Implements automatic token refresh...   │
│                                         │
│ Closes #456                             │
╰─────────────────────────────────────────╯

Action [y/e/r/n] (y):
```

- `y` — 接受提案，执行提交
- `e` — 编辑消息后提交
- `r` — 重新生成提案
- `n` — 取消

### 直接提交（跳过 AI）

```bash
agit commit -m "fix: resolve login bug"
agit commit -m "feat: add dark mode" --signoff
agit commit --amend  # 修改上一次提交
```

### 同步远程

```bash
agit sync
```

自动分析状态并生成同步计划：
- 有未提交修改 + 落后远程 → stash → pull --rebase → stash pop
- 只有本地领先 → push
- 有冲突 → 提示解决建议

---

## 5. 发布流程

### 使用 Agent 发布

```bash
agit agent "准备发布 v1.0.0"
```

Agent 自动生成完整计划：
```
1. git add -A                        [MEDIUM]
2. git commit -m "Release v1.0.0"    [HIGH]
3. git tag -a v1.0.0 -m "v1.0.0"     [HIGH]
4. git push origin main              [CRITICAL]
5. git push origin v1.0.0            [CRITICAL]
```

### 手动发布

```bash
agit add -A
agit commit -m "Release v1.0.0"
agit changelog --output CHANGELOG.md
git tag -a v1.0.0 -m "Version 1.0.0"
git push origin main
git push origin v1.0.0
```

### 生成变更日志

```bash
# 从上个 tag 到 HEAD
agit changelog

# 指定范围
agit changelog --from v1.0 --to v2.0

# 输出 JSON
agit changelog --format json

# 写入文件
agit changelog --output CHANGELOG.md --no-preview
```

---

## 6. 代码审查

```bash
# 审查暂存区
agit review

# 审查所有变更
agit review --all

# 审查某次提交
agit review HEAD~1

# 审查范围
agit review --range abc..def
```

输出示例：
```
  CRITICAL (1)
  ─────────────
  src/auth.py:67   SQL query uses string formatting
    → 使用参数化查询防止 SQL 注入

  WARNING (2)
  ─────────────
  src/auth.py:45   变量 token 未做 null 检查
  src/auth.py:89   异常过于宽泛

  SUGGESTION (1)
  ─────────────
  src/auth.py:23   可以提取为常量
```

---

## 7. 仓库健康检查

```bash
# 完整检查
agit doctor

# 快速检查（跳过 AI）
agit doctor --quick

# 自动修复
agit doctor --fix
```

检查项（12 项）：
1. 未跟踪文件
2. 大文件（>50MB）
3. 敏感信息扫描
4. 二进制文件
5. .gitignore 完整性
6. 潜在合并冲突
7. 提交信息规范
8. 远程仓库连通性
9. 分支状态
10. 依赖安全
11. 孤立分支
12. Stash 积压

---

## 8. Agent 模式

Agent 是 agit 的核心功能，将自然语言转化为 Git 操作计划。

```bash
# 发布
agit agent "准备发布 v1.0.0"

# 同步
agit agent "把今天的改动推到远程"

# 清理
agit agent "清理所有已合并的本地分支"

# 修复
agit agent "撤销上一次错误的提交"
```

### 执行流程

```
用户输入意图
    ↓
AI 分析仓库状态（分支、远程、暂存区、标签...）
    ↓
生成执行计划
    ↓
展示计划 + 风险评估
    ↓
用户批准 [y/N/e/a]
    ↓
逐步执行，展示真实输出
    ↓
写入执行日志
```

### 决策选项

| 输入 | 行为 |
|------|------|
| `y` | 批准全部计划 |
| `N` | 取消全部计划 |
| `e` | 逐条审查，每条独立确认 |
| `a` | 终止整个流程 |

### CRITICAL 操作确认

当遇到 CRITICAL 操作（如 force push）时，会显示：

```
BLOCKED (CRITICAL): git push --force origin main

⚠ 警告：此操作具有高风险

继续执行即表示您理解并接受以下条款：
• 此操作可能导致数据丢失或不可逆的仓库损坏
• 执行后果由操作者自行承担，agit 不承担任何责任
• 建议先备份重要数据或使用 --dry-run 预览

--- Current Context ---
  Branch: main
  Remote: github (https://github.com/user/repo.git)
  Status: ahead=5, behind=0
  HEAD: abc1234
-----------------------

Command: git push --force origin main

Type 'yes' to proceed:
```

输入 `yes` 才会执行，其他任何输入都会取消。

---

## 9. 回滚与重放

### 回滚

```bash
# 预览回滚计划
agit undo

# 执行回滚
agit undo --no-dry-run

# 回滚特定步骤
agit undo --step 2
```

### 重放

```bash
# 重放上一次 session
agit replay

# 重放指定日期
agit replay 2026-07-20

# 只重放特定步骤
agit replay --steps 1,3,5
```

---

## 10. 国际化

```bash
# 中文（默认）
agit doctor

# 英文
agit -l en_US doctor
agit -l en_US config list
agit -l en_US agent "prepare release v1.0.0"
```

支持的 locale：
- `zh_CN` — 中文（默认）
- `en_US` — 英文
