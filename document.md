# `agit` — AI-Powered Git CLI 架构设计

---

## 一、设计哲学

**一句话定义**：`agit` 是 Git 的 AI 副驾驶，不是自动驾驶。缰绳始终在人手中。

**三条铁律**：

| # | 铁律 | 含义 |
|---|------|------|
| 1 | **默认不执行** | 所有 AI 计划默认只展示（Dry Run），人类批准后才动手 |
| 2 | **可逆优先** | 每一步执行前先确保存在回退路径 |
| 3 | **CRITICAL 永不自动** | 即使 solo=true，破坏性操作仍然阻断，输出命令让用户手动执行 |

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           用户 (Rider)                               │
│                  通过 CLI 发出意图，持有最终决策权                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   agit <command> [--flags]                                           │
│        │                                                             │
│        ▼                                                             │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    命令路由器 (CLI Router)                    │   │
│   │   changelog │ commit │ sync │ explain │ review │ doctor     │   │
│   │   agent │ replay │ undo │ config │ init                     │   │
│   └────────────────────────┬────────────────────────────────────┘   │
│                            │                                         │
│                            ▼                                         │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                  Harness Agent 引擎                          │   │
│   │                                                              │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │   │
│   │  │ Intent    │→│ Planner  │→│  Risk     │→│  Decision   │  │   │
│   │  │ Parser    │  │ (步骤分解)│  │ Assessor  │  │  Gate      │  │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └─────┬──────┘  │   │
│   │                                                    │         │   │
│   │                              ┌─────────────────────┤         │   │
│   │                              ▼                     ▼         │   │
│   │                        ┌──────────┐         ┌──────────┐    │   │
│   │                        │ Executor │         │ Journal  │    │   │
│   │                        │ (git桥接) │         │ (审计日志)│    │   │
│   │                        └────┬─────┘         └──────────┘    │   │
│   └─────────────────────────────┼───────────────────────────────┘   │
│                                 │                                    │
│                                 ▼                                    │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                      AI Provider 层                          │   │
│   │                                                              │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │   │
│   │  │ OpenAI   │  │ Anthropic│  │ Ollama   │  │ 自定义端点  │  │   │
│   │  │ 兼容API  │  │          │  │ (本地)    │  │ (OpenAI格式)│  │   │
│   │  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │   │
│   │                                                              │   │
│   │  统一接口: POST /v1/chat/completions (OpenAI 格式)           │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                     底层 (Git Bridge)                        │   │
│   │   不 wrap git 命令——而是解析 git 输出 / 调用 libgit2 /       │   │
│   │   subprocess.run(["git", ...]) 安全执行                      │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、配置系统

### 3.1 配置来源与优先级

```
优先级（高→低）：

  CLI --flag          临时覆盖，仅当次生效
       │
  环境变量 AGIT_*     CI/CD 场景，不落盘
       │
  项目配置 .agit/config.toml     团队共享，提交到仓库
       │
  用户配置 ~/.config/agit/config.toml   个人偏好
       │
  内置默认值
```

### 3.2 配置项全景

```toml
[ai]
# OpenAI 兼容端点，所有 provider 统一走这个格式
baseurl    = "https://api.openai.com/v1"
model      = "gpt-4o"
apikey     = ""                         # 强烈建议用 AGIT_AI_APIKEY 环境变量
provider   = "openai"                   # openai | anthropic | ollama | custom
timeout    = 30
max_tokens = 4096
temperature = 0.3                       # 低温度 = 更稳定的结构化输出

[agent]
solo       = false                      # true: AI 自主执行高风险操作
confirm    = "smart"                    # always | never | smart
dry_run    = true                       # ★ 默认开启，所有计划先展示
verbose    = false
max_steps  = 20                         # 单次 agent session 最大步骤数
auto_push  = false                      # 是否默认包含 push

[risk]
# 可覆盖的风险策略
force_push       = "forbid"             # forbid | confirm | allow
reset_hard       = "confirm"
delete_branch    = "confirm"
push_main        = "confirm"
clean            = "confirm"

# 保护分支列表
protected_branches = ["main", "master", "release/*"]

[changelog]
conventional = true
sections     = ["feat", "fix", "perf", "refactor", "docs", "chore"]
locale       = "zh-CN"                  # 输出语言

[commit]
conventional    = true
auto_stage      = false
signoff         = false
scope_inference = true

[doctor]
# 自定义敏感信息模式（正则）
sensitive_patterns = [
    "AKIA[0-9A-Z]{16}",                 # AWS Access Key
    "sk-[a-zA-Z0-9]{48}",               # OpenAI API Key
    "ghp_[a-zA-Z0-9]{36}",              # GitHub PAT
]
max_file_size  = "50MB"                 # 大文件阈值
binary_extensions = [".exe", ".dll", ".so", ".dylib", ".bin"]
```

### 3.3 配置命令

```
agit config set <key> <value>    设置配置项
agit config get <key>            获取配置项
agit config list                 列出所有配置（标注来源）
agit config validate             校验配置完整性（AI 连通性测试）
agit config reset                重置为默认值
```

**安全机制**：`config set ai.apikey` 时提示将密钥存入环境变量，并自动将 `.agit/config.toml` 中的 apikey 字段替换为 `$AGIT_AI_APIKEY` 引用。

---

## 四、Harness Agent 核心机制

### 4.1 执行流水线

```
用户输入意图
     │
     ▼
┌─────────────┐     ┌──────────────────────────────────┐
│ Intent      │     │  "帮我整理这周的改动，发布 v1.3"    │
│ Parser      │────▶│                                    │
│ (LLM)       │     │  → 结构化意图: release(version=1.3)│
└──────┬──────┘     └──────────────────────────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────────────────────────┐
│ Planner     │     │  Step 1: git add -A               │
│ (LLM +      │────▶│  Step 2: git commit "chore: ..."  │
│  规则引擎)   │     │  Step 3: generate CHANGELOG        │
└──────┬──────┘     │  Step 4: git tag v1.3.0            │
       │            │  Step 5: git push --tags            │
       │            └──────────────────────────────────┘
       ▼
┌─────────────┐     ┌──────────────────────────────────┐
│ Risk        │     │  Step 1: LOW      → auto          │
│ Assessor    │────▶│  Step 2: MEDIUM   → auto          │
│             │     │  Step 3: LOW      → auto          │
│             │     │  Step 4: HIGH     → confirm        │
│             │     │  Step 5: HIGH     → confirm        │
└──────┬──────┘     └──────────────────────────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────────────────────────┐
│ Dry Run     │     │                                  │
│ Presenter   │────▶│  Plan (展示给用户)                 │
│ (默认模式)   │     │  ──────────────────               │
└──────┬──────┘     │  ✓ git add -A                     │
       │            │  ✓ git commit                     │
       │            │  ✓ generate CHANGELOG              │
       │            │  ▸ git tag v1.3.0      [HIGH]     │
       │            │  ▸ git push --tags     [HIGH]     │
       │            │                                  │
       │            │  Risk: HIGH                        │
       │            │  Approve? [y/N/e/a]               │
       │            └──────────────────────────────────┘
       ▼
┌─────────────┐
│ Decision    │    y = 全部执行
│ Gate        │    N = 全部跳过
│             │    e = 逐条审查
│             │    a = abort 整个流程
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────────────────────────┐
│ Executor    │────▶│  依次执行 git 命令                 │
│             │     │  每步执行后验证结果                 │
│             │     │  失败时自动回滚到 checkpoint        │
└──────┬──────┘     └──────────────────────────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────────────────────────┐
│ Journal     │────▶│  写入 .agit/history/YYYY-MM-DD.json│
│ Recorder    │     │  记录：操作、快照、结果、可回滚性    │
└─────────────┘     └──────────────────────────────────┘
```

### 4.2 风险分级

```
┌────────────┬────────────────────────────────┬────────────────────────┐
│  风险等级   │  操作示例                       │  处理策略              │
├────────────┼────────────────────────────────┼────────────────────────┤
│            │  git status / diff / log        │                        │
│  LOW       │  git branch (列出)              │  自动执行              │
│            │  git show / blame               │  仅在 verbose 时展示   │
│            │  AI 分析 / 解释                 │                        │
├────────────┼────────────────────────────────┼────────────────────────┤
│            │  git add (暂存文件)             │                        │
│  MEDIUM    │  git stash                      │  自动执行（solo=true） │
│            │  git checkout / switch          │  交互模式下展示确认     │
│            │  创建本地分支                    │                        │
├────────────┼────────────────────────────────┼────────────────────────┤
│            │  git commit                     │                        │
│  HIGH      │  git push                       │  默认必须确认          │
│            │  git merge / rebase             │  solo=true 自动执行    │
│            │  git tag                        │  solo=true 自动执行    │
│            │  删除本地分支                    │                        │
├────────────┼────────────────────────────────┼────────────────────────┤
│            │  git push --force               │                        │
│  CRITICAL  │  git reset --hard               │  ★ 永远阻断自动执行     │
│            │  git clean -f                   │  输出命令供手动执行     │
│            │  删除远程分支                    │  solo=true 也不执行    │
│            │  推送到 protected branch         │                        │
│            │  涉及 submodules 的破坏性操作    │                        │
└────────────┴────────────────────────────────┴────────────────────────┘
```

### 4.3 上下文感知风险

静态分类之外，Agent 还会根据仓库实时状态调整风险：

- 当前在 `main` 分支 → 所有 commit / push 自动升级为 CRITICAL
- 工作区有未提交修改 → checkout / switch 升级为 HIGH
- 存在 merge conflict → 任何 merge/rebase 操作升级为 CRITICAL
- 距离上次 push 超过 50 个 commit → push 升级为 HIGH（可能需要分批）

---

## 五、功能模块设计

### 5.1 `agit changelog` — 智能变更日志

**输入**：Git 提交历史（指定范围或自上个 tag 起）
**处理**：AI 将原始 commit 信息转化为面向用户的变更日志
**输出**：CHANGELOG.md / JSON / RST

```
工作流：

  git log --oneline v1.2.0..HEAD
       │
       ▼
  ┌────────────────────────────────────────────┐
  │  将 commits 按批次发送给 AI（每批 ~50 条）   │
  │                                              │
  │  AI 任务：                                    │
  │  1. 按 Conventional Commits 分类              │
  │  2. 将技术描述改写为用户可读描述               │
  │  3. 识别 BREAKING CHANGES                     │
  │  4. 合并相关 commits 为一条                    │
  │  5. 过滤无关噪音（typo fix, CI 等）           │
  └──────────────────┬─────────────────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────────┐
  │  合并去重 → 按 section 排序 → 渲染输出       │
  └────────────────────────────────────────────┘
```

**命令**：

```
agit changelog                        # 从上个 tag 到 HEAD
agit changelog --from v1.0 --to v2.0  # 指定范围
agit changelog --format json          # JSON 输出
agit changelog --output CHANGELOG.md  # 写入文件
agit changelog --preview              # 只预览，不写文件（默认）
```

**Risk**：LOW（只读操作，不修改任何东西）

---

### 5.2 `agit commit` — AI 辅助提交

**工作流**：

```
  git diff --staged (或 --cached / working tree)
       │
       ▼
  ┌────────────────────────────────────────────┐
  │  AI 分析 diff，生成 commit message 提案      │
  │                                              │
  │  输出结构：                                   │
  │  {                                           │
  │    type: "feat",                             │
  │    scope: "auth",                            │
  │    subject: "add OAuth2 refresh rotation",   │
  │    body: "详细说明...",                        │
  │    footer: "Closes #456"                     │
  │  }                                           │
  └──────────────────┬─────────────────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────────┐
  │  展示提案：                                  │
  │                                              │
  │  Commit Proposal                             │
  │  ─────────────────                           │
  │  feat(auth): add OAuth2 refresh rotation     │
  │                                              │
  │  Implements automatic token refresh for      │
  │  expired access tokens. Reduces user-facing  │
  │  auth errors by ~90%.                        │
  │                                              │
  │  Closes #456                                 │
  │                                              │
  │  [y] Accept  [e] Edit  [r] Regenerate [n] Cancel │
  └────────────────────────────────────────────┘
```

**Risk**：HIGH（创建 commit 进入历史）

---

### 5.3 `agit sync` — 智能同步

**工作流**：

```
  ┌────────────────────────────────────────────┐
  │  分析仓库状态                                │
  │  - 当前分支 & 是否受保护                      │
  │  - 领先/落后远程多少 commit                   │
  │  - 工作区是否有未提交修改                      │
  │  - 是否存在冲突                               │
  └──────────────────┬─────────────────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────────┐
  │  生成同步计划                                 │
  │                                              │
  │  场景 A: 有未提交修改 + 落后远程              │
  │  → stash → pull --rebase → stash pop         │
  │                                              │
  │  场景 B: 只有本地领先                         │
  │  → git push                                  │
  │                                              │
  │  场景 C: 有冲突                               │
  │  → AI 分析冲突 → 提供解决建议 → 人工决策      │
  │                                              │
  │  场景 D: 需要 force push                      │
  │  → 阻断，提示风险，输出命令供手动执行          │
  └──────────────────┬─────────────────────────┘
                     │
                     ▼
  Dry Run 展示 → 用户确认 → 逐步执行 → 写入 Journal
```

**Risk**：每步独立评估，范围 MEDIUM ~ CRITICAL

---

### 5.4 `agit explain` — 提交解读器

**设计意图**：不看 diff，只用自然语言告诉你"到底改了什么"。

```
agit explain                          # 解释最近 1 次 commit
agit explain HEAD~3..HEAD             # 解释最近 3 次
agit explain v1.2.0..v1.3.0          # 解释版本间变更
agit explain --file src/auth.py       # 解释某个文件的最近变更
agit explain abc123                   # 解释某个特定 commit
```

**输出示例**：

```
$ agit explain HEAD~3..HEAD

  Commit Range: abc1234..def5678 (3 commits, 2 files)

  ┌─ Summary ─────────────────────────────────────────┐
  │                                                     │
  │  这三次提交都在重构认证模块，主要做了三件事：         │
  │                                                     │
  │  1. 把 Token 校验逻辑从 utils/auth.py 移到了        │
  │     services/token_service.py，原因是原来的文件      │
  │     职责太杂。                                       │
  │                                                     │
  │  2. 新增了 refresh token 的自动轮换机制。当          │
  │     access token 过期时，客户端不需要重新登录，      │
  │     后台会用 refresh token 静默换一个新的。          │
  │                                                     │
  │  3. 修了一个边界 bug：当 refresh token 也过期时，    │
  │     之前会返回 500，现在正确返回 401 + 重新登录提示。 │
  │                                                     │
  │  影响范围：所有需要认证的 API 端点行为不变，          │
  │  但客户端 token 刷新逻辑可能需要同步更新。           │
  │                                                     │
  │  ⚠ 注意：第 3 个 commit 修改了 error_handler.py     │
  │  的全局异常捕获，可能影响其他模块的错误返回格式。     │
  │                                                     │
  └─────────────────────────────────────────────────────┘

  Per-Commit Breakdown:

  abc1234 refactor(auth): extract token validation
    → 将 validate_token() 从 utils/auth.py 移至 services/token_service.py
    → 无功能变更，纯结构重组
    → 移动: +87 / -92 (净 -5 行)

  bcd2345 feat(auth): add refresh token rotation
    → 新增 RefreshTokenRotator 类
    → 新增 /auth/refresh 端点
    → 新增: +156 / -3

  cde3456 fix(auth): handle expired refresh token gracefully
    → 修改 error_handler.py 第 42 行
    → 将 refresh token 过期的 500 → 401
    → 修改: +12 / -4
```

**Risk**：LOW（纯只读分析）

---

### 5.5 `agit review` — AI 代码审查

```
agit review                          # 审查当前 diff (staged)
agit review --all                    # 审查所有变更 (staged + unstaged)
agit review HEAD~1                   # 审查最近一次 commit
agit review --range abc..def         # 审查指定范围
agit review --pr 123                 # 审查 PR（需要 GitHub/GitLab 集成）
```

**AI 审查维度**：

```
┌─────────────────────────────────────────────────────────────────┐
│  Review Matrix                                                   │
├──────────────┬──────────────────────────────────────────────────┤
│  维度         │  检查项                                         │
├──────────────┼──────────────────────────────────────────────────┤
│  🐛 潜在 Bug  │  空指针、边界条件、资源泄漏、竞态条件            │
│              │  异常处理缺失、类型错误                           │
├──────────────┼──────────────────────────────────────────────────┤
│  🔒 安全风险  │  SQL 注入、XSS、硬编码密钥                      │
│              │  不安全的反序列化、权限绕过                       │
├──────────────┼──────────────────────────────────────────────────┤
│  ⚡ 性能问题  │  N+1 查询、不必要的循环、内存密集操作            │
│              │  可以用更高效算法替代的逻辑                       │
├──────────────┼──────────────────────────────────────────────────┤
│  📐 风格规范  │  命名一致性、函数长度、圈复杂度                  │
│              │  重复代码、不符合项目约定的写法                   │
├──────────────┼──────────────────────────────────────────────────┤
│  🧪 测试覆盖  │  新增代码是否有对应测试                         │
│              │  边界条件是否被覆盖                              │
├──────────────┼──────────────────────────────────────────────────┤
│  📦 依赖变更  │  新增依赖的安全性、许可证兼容性                  │
│              │  是否有更轻量的替代方案                          │
└──────────────┴──────────────────────────────────────────────────┘
```

**输出示例**：

```
$ agit review

  Reviewing staged changes (3 files, +127/-45)

  ┌─ Review Results ─────────────────────────────────────────┐
  │                                                           │
  │  🔴 CRITICAL (1)                                          │
  │  ─────────────────                                        │
  │  src/auth.py:67   SQL query uses string formatting        │
  │    cursor.execute(f"SELECT * FROM users WHERE id={uid}")  │
  │    → 使用参数化查询防止 SQL 注入                            │
  │    → cursor.execute("SELECT * FROM users WHERE id=%s",    │
  │                      (uid,))                              │
  │                                                           │
  │  🟡 WARNING (2)                                           │
  │  ─────────────────                                        │
  │  src/auth.py:45   变量 token 未做 null 检查               │
  │    → 如果 get_token() 返回 None，下一行会 AttributeError  │
  │                                                           │
  │  src/auth.py:89   异常过于宽泛                             │
  │    except Exception → except (ValueError, KeyError)       │
  │    → 捕获所有异常会隐藏真正的错误                           │
  │                                                           │
  │  💡 SUGGESTION (1)                                        │
  │  ─────────────────                                        │
  │  src/auth.py:23   可以提取为常量                           │
  │    TIMEOUT_SECONDS = 30 （与 utils.py:12 重复）            │
  │                                                           │
  │  ✅ GOOD                                                  │
  │  ─────────────────                                        │
  │  测试文件 tests/test_auth.py 已同步更新                    │
  │  新增函数有 docstring                                     │
  │                                                           │
  └───────────────────────────────────────────────────────────┘

  Summary: 1 critical, 2 warnings, 1 suggestion

  [f] Fix critical issues  [c] Commit anyway  [q] Quit
```

**Risk**：LOW（只读分析），但如果用户选择 `f`（让 AI 自动修复），则变为 HIGH（修改文件）

---

### 5.6 `agit doctor` — 仓库健康检查

```
agit doctor                         # 完整检查
agit doctor --quick                 # 快速检查（跳过 AI 分析）
agit doctor --fix                   # 检查 + 自动修复可修复项
```

**检查项**：

```
┌─────────────────────────────────────────────────────────────────────┐
│  Doctor Health Report                                                │
├──────┬────────────────────────────────┬──────────┬──────────────────┤
│ #    │ 检查项                         │ 状态     │ 详情             │
├──────┼────────────────────────────────┼──────────┼──────────────────┤
│  1   │ 未跟踪文件 (untracked)         │ ⚠ 3个    │ src/temp.py ...  │
│  2   │ 大文件 (>50MB)                 │ ✅ 无     │                  │
│  3   │ 敏感信息扫描                   │ 🔴 2处   │ 见下方详情       │
│  4   │ 待提交的二进制文件              │ ⚠ 1个    │ assets/icon.psd  │
│  5   │ .gitignore 完整性              │ ⚠ 建议   │ 缺少 *.pyc 规则  │
│  6   │ 潜在合并冲突                   │ ✅ 无     │                  │
│  7   │ 提交信息规范                   │ ⚠ 5/23   │ 5条不符合规范    │
│  8   │ 远程仓库连通性                 │ ✅ 正常   │                  │
│  9   │ 分支状态                       │ ⚠ 落后3  │ origin/main      │
│ 10   │ 依赖安全                       │ ✅ 无已知 │                  │
│ 11   │ 孤立分支                       │ ⚠ 2个    │ feat/old-a, ...  │
│ 12   │ Stash 积压                     │ ✅ 0个    │                  │
└──────┴────────────────────────────────┴──────────┴──────────────────┘

  ┌─ 🔴 敏感信息详情 ────────────────────────────────────────┐
  │                                                           │
  │  src/config.py:12     疑似 API Key                        │
  │    OPENAI_KEY = "sk-abc123..."                            │
  │    → 建议：移至 .env，添加到 .gitignore                    │
  │                                                           │
  │  docker-compose.yml:8 疑似数据库密码                      │
  │    DB_PASS = "my_secret_pass"                             │
  │    → 建议：使用环境变量或 Docker secrets                   │
  │                                                           │
  └───────────────────────────────────────────────────────────┘

  ┌─ 修复建议 ───────────────────────────────────────────────┐
  │                                                           │
  │  可自动修复 (agit doctor --fix):                          │
  │  ✓ 将 *.pyc, __pycache__/, .env 加入 .gitignore          │
  │  ✓ 格式化最近 5 条 commit message                         │
  │                                                           │
  │  需要手动处理:                                             │
  │  ! 移除已提交的敏感信息 (需 git filter-branch 或 BFG)      │
  │  ! 清理孤立分支                                            │
  │  ! 将 .psd 文件移出 Git 管理                               │
  │                                                           │
  └───────────────────────────────────────────────────────────┘

  Health Score: 72/100

  [f] Auto-fix  [d] Details  [q] Quit
```

**Risk**：LOW（只读），`--fix` 模式下修改 .gitignore 等为 MEDIUM

---

## 六、Dry Run & Execution Journal 系统

### 6.1 Dry Run 机制

```
默认行为（dry_run = true）：

  AI 生成计划 → 完整展示每一步 → 等待用户决策 → 才执行

  ┌─────────────────────────────────────────────┐
  │  Plan                                        │
  │  ──────────────────                          │
  │  ✓ git add src/auth.py src/test_auth.py      │
  │  ✓ git commit -m "feat(auth): add ..."       │
  │  ✓ generate CHANGELOG.md                     │
  │  ▸ git tag v1.3.0                 [HIGH]     │
  │  ▸ git push origin main --tags    [HIGH]     │
  │                                              │
  │  Risk: HIGH                                  │
  │                                              │
  │  Approve? [y]es / [N]o / [e]dit / [a]bort    │
  └─────────────────────────────────────────────┘

  符号说明：
    ✓ = LOW / MEDIUM（将自动执行）
    ▸ = HIGH（需要确认）
    ✋ = CRITICAL（将被阻断）
    ⚡ = 已在 solo 模式下自动处理
```

**决策选项**：

| 输入 | 行为 |
|------|------|
| `y` / `yes` | 批准全部计划，按序执行 |
| `N` / `no` | 取消全部计划，不做任何操作 |
| `e` / `edit` | 逐条审查，每条独立确认 |
| `a` / `abort` | 终止整个 session |
| `d` / `dry` | 切换到详细 dry run（展示每条 git 命令的完整参数） |
| `m` / `modify` | 修改计划（AI 重新生成部分步骤） |

### 6.2 Execution Journal（执行日志）

**存储结构**：

```
.agit/
├── config.toml
├── history/
│   ├── 2026-07-20.json         # 按日期存储
│   ├── 2026-07-19.json
│   └── index.json              # 全局索引（快速查询）
└── snapshots/
    ├── 2026-07-20T14:30:22/    # 关键操作前的快照
    │   ├── HEAD                # git rev-parse HEAD
    │   ├── reflog              # git reflog -20
    │   ├── staged              # 暂存区快照
    │   └── unstaged_diff       # 工作区 diff
    └── ...
```

**单条 Journal 记录**：

```
session_id    : "sess_20260720_143022"
timestamp     : "2026-07-20T14:30:22+08:00"
trigger       : "agit sync"
mode          : "interactive" | "solo"

intent        : "Sync local changes with remote"

plan:
  - step 1:
      command     : "git add -u"
      risk        : "MEDIUM"
      decision    : "auto"
      result      : "success"
  - step 2:
      command     : "git commit -m 'feat(auth): add token rotation'"
      risk        : "HIGH"
      decision    : "approved_by_user"
      result      : "success"
      commit_hash : "abc1234"
  - step 3:
      command     : "git push origin main"
      risk        : "HIGH"
      decision    : "skipped_by_user"
      result      : "skipped"

snapshot_before : "snapshots/2026-07-20T14:30:22/"
ai_model        : "gpt-4o"
ai_tokens_used  : 1847
duration_ms     : 4230

rollback_plan:
  - "git reset HEAD~1"   # 撤销 step 2 的 commit
  - "git checkout -- ."   # 撤销 step 1 的 add
```

### 6.3 `agit undo` — 回滚机制

```
agit undo                    # 撤销上一次 agent session
agit undo --step 2           # 只撤销 session 中的第 2 步
agit undo --to abc1234       # 回滚到指定 commit
agit undo --dry-run          # 预览回滚计划（默认行为）
```

**回滚策略**：

```
┌────────────────────┬───────────────────────────────────────────┐
│  操作类型           │  回滚方式                                  │
├────────────────────┼───────────────────────────────────────────┤
│  git add           │  git reset HEAD <files>                   │
│  git commit        │  git reset --soft HEAD~1                  │
│  git push          │  git revert <commit> (安全)               │
│                    │  或 git push --force (需确认, CRITICAL)    │
│  git tag           │  git tag -d <tag>                         │
│  git merge         │  git reset --hard ORIG_HEAD               │
│  git rebase        │  git reset --hard ORIG_HEAD               │
│  git branch -d     │  git branch <name> <sha>                  │
│  文件修改          │  git checkout -- <files>                  │
│  CHANGELOG 生成    │  git checkout -- CHANGELOG.md             │
└────────────────────┴───────────────────────────────────────────┘

回滚本身也经过 Risk Gate：
  回滚 LOW/MEDIUM 操作  → 自动
  回滚 HIGH 操作        → 确认
  回滚 CRITICAL 操作    → 手动执行
```

### 6.4 `agit replay` — 重放执行

```
agit replay                      # 重放上一次 session
agit replay 2026-07-20           # 重放指定日期的 session
agit replay --session sess_20260720_143022  # 按 session ID
agit replay --steps 1,3,5        # 只重放指定步骤
```

**典型场景**：

- 每天在 feature 分支上做类似的 add-commit-push 流程，replay 上次的操作
- CI 中重放本地验证过的操作序列
- 回滚后重新执行（修改参数后）

---

## 七、Solo 模式 vs 交互模式

```
┌──────────────────┬─────────────────────────┬──────────────────────────┐
│  Risk Level      │  interactive (默认)      │  solo = true             │
├──────────────────┼─────────────────────────┼──────────────────────────┤
│  LOW             │  ✓ 自动（verbose 时展示）│  ✓ 自动                  │
│  MEDIUM          │  ✓ 自动（展示摘要）      │  ✓ 自动                  │
│  HIGH            │  ❓ 展示 + 等待确认       │  ✓ 自动                  │
│  CRITICAL        │  ❓ 展示 + 等待确认       │  ✋ 阻断 + 输出命令       │
│                  │                         │  （用户手动执行）          │
├──────────────────┼─────────────────────────┼──────────────────────────┤
│  Commit message  │  展示提案 → 确认/编辑    │  自动提交                │
│  Push            │  展示目标 → 确认          │  自动推送                │
│  Force push      │  展示警告 → 确认          │  ★ 阻断                  │
│  Reset --hard    │  展示警告 → 确认          │  ★ 阻断                  │
│  Delete branch   │  展示目标 → 确认          │  ★ 阻断（远程）          │
└──────────────────┴─────────────────────────┴──────────────────────────┘
```

**solo 模式的使用场景**：

- CI/CD 流水线中自动执行预验证的操作
- 个人项目、信任 AI 产出时提升效率
- 配合 `dry_run = false` 使用

**solo 模式的安全保障**：

- CRITICAL 操作永远阻断
- 所有操作写入 Journal（可 undo）
- 每次 session 前自动创建 snapshot
- 超过 `max_steps` 阈值时强制暂停

---

## 八、AI Provider 抽象层

### 8.1 统一接口

```
所有 AI 调用统一走 OpenAI Chat Completions 格式：

  POST {baseurl}/chat/completions
  {
    "model": "{model}",
    "messages": [...],
    "temperature": 0.3,
    "response_format": {"type": "json_object"}  // 结构化输出时
  }
```

**Provider 映射**：

```
┌──────────────┬────────────────────────────────────────────────┐
│  provider    │  实际端点映射                                   │
├──────────────┼────────────────────────────────────────────────┤
│  openai      │  https://api.openai.com/v1/chat/completions   │
│  anthropic   │  通过 adapter 转换为 Anthropic Messages API    │
│  ollama      │  http://localhost:11434/v1/chat/completions    │
│  custom      │  {baseurl}/chat/completions (直接使用)          │
│  azure       │  https://{resource}.openai.azure.com/...      │
└──────────────┴────────────────────────────────────────────────┘
```

### 8.2 AI 调用策略

```
┌──────────────────────────────────────────────────────────────┐
│  不同功能使用不同的 prompt 和参数：                             │
│                                                               │
│  changelog    → 低温度(0.2), JSON 格式, 批量处理              │
│  commit       → 中温度(0.4), JSON 格式, 单次                  │
│  explain      → 中温度(0.5), 自由文本, 长输出                 │
│  review       → 低温度(0.2), JSON 格式, 需要精确              │
│  agent plan   → 中温度(0.3), JSON 格式, 多轮                  │
│  doctor       → 不用 AI（规则引擎为主，AI 辅助敏感信息判断）   │
└──────────────────────────────────────────────────────────────┘
```

### 8.3 数据安全

```
发送给 AI 前的预处理：

  1. 脱敏 (Sanitize)
     自动检测并替换：
     - API Keys (sk-*, AKIA*, ghp_*)
     - 密码赋值语句 (password = "xxx")
     - JWT Token
     - 自定义模式 (配置文件定义)

  2. 截断 (Truncate)
     - 单次发送 diff 上限：8000 tokens
     - 超出时按文件优先级截断
     - 提示用户：已截断 N 个文件

  3. 通知 (Notify)
     每次 AI 调用前展示：
     → Sending 3 files, ~2.4K tokens to gpt-4o @ openai.com
     → [y] Proceed  [n] Cancel  [v] View payload
```

---

## 九、Python 项目结构

```
agit/
├── pyproject.toml                    # 项目元数据 + 依赖
├── README.md
│
├── src/
│   └── agit/
│       ├── __init__.py
│       ├── __main__.py               # python -m agit
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py               # Click/Typer 主入口
│       │   ├── init.py               # agit init
│       │   ├── config.py             # agit config
│       │   ├── changelog_cmd.py      # agit changelog
│       │   ├── commit_cmd.py         # agit commit
│       │   ├── sync_cmd.py           # agit sync
│       │   ├── explain_cmd.py        # agit explain
│       │   ├── review_cmd.py         # agit review
│       │   ├── doctor_cmd.py         # agit doctor
│       │   ├── agent_cmd.py          # agit agent
│       │   ├── replay_cmd.py         # agit replay
│       │   └── undo_cmd.py           # agit undo
│       │
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── engine.py             # Agent 引擎核心循环
│       │   ├── planner.py            # 任务分解 + 步骤规划
│       │   ├── gate.py               # Risk Gate 决策闸门
│       │   ├── executor.py           # Git 命令执行器
│       │   └── presenter.py          # Dry Run 展示器
│       │
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── client.py             # 统一 AI 客户端
│       │   ├── providers/
│       │   │   ├── openai.py         # OpenAI 兼容
│       │   │   ├── anthropic.py      # Anthropic adapter
│       │   │   └── ollama.py         # Ollama 本地
│       │   ├── prompts/
│       │   │   ├── changelog.py      # Changelog prompt 模板
│       │   │   ├── commit.py         # Commit prompt 模板
│       │   │   ├── explain.py        # Explain prompt 模板
│       │   │   ├── review.py         # Review prompt 模板
│       │   │   └── planner.py        # Agent planner prompt
│       │   └── sanitizer.py          # Diff 脱敏
│       │
│       ├── risk/
│       │   ├── __init__.py
│       │   ├── classifier.py         # 静态风险分类
│       │   ├── context.py            # 上下文感知（仓库状态）
│       │   └── matrix.py             # 风险矩阵定义
│       │
│       ├── git/
│       │   ├── __init__.py
│       │   ├── repo.py               # Repository 封装
│       │   ├── diff.py               # Diff 解析
│       │   ├── log.py                # Log 解析
│       │   ├── branch.py             # 分支操作
│       │   └── executor.py           # subprocess 安全执行
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── schema.py             # 配置 schema 定义
│       │   ├── loader.py             # 多源配置加载 + 合并
│       │   └── validator.py          # 值校验
│       │
│       ├── journal/
│       │   ├── __init__.py
│       │   ├── writer.py             # Journal 写入
│       │   ├── reader.py             # Journal 读取
│       │   ├── snapshot.py           # 仓库快照
│       │   └── undo.py               # 回滚逻辑
│       │
│       ├── features/
│       │   ├── __init__.py
│       │   ├── changelog.py          # Changelog 生成逻辑
│       │   ├── commit.py             # Commit 辅助逻辑
│       │   ├── sync.py               # Sync 逻辑
│       │   ├── explain.py            # Explain 逻辑
│       │   ├── review.py             # Review 逻辑
│       │   └── doctor.py             # Doctor 检查引擎
│       │
│       └── utils/
│           ├── __init__.py
│           ├── console.py            # 终端输出（颜色、表格、进度条）
│           └── errors.py             # 统一错误处理
│
└── tests/
    ├── test_agent/
    ├── test_risk/
    ├── test_features/
    └── fixtures/                     # 测试用的 git 仓库 fixture
```

**核心依赖**：

```
typer          # CLI 框架（基于 Click，类型安全）
rich           # 终端富文本输出（表格、颜色、进度条）
httpx          # AI API 调用（async 支持）
pydantic       # 配置 schema + AI 响应解析
python-git     # 或直接 subprocess 调用 git
tomli / tomllib # TOML 配置解析
keyring        # 安全存储 API key（可选）
```

---

## 十、完整命令速查

```
┌─────────────────────────────────────────────────────────────────┐
│  agit 命令速查                                                    │
├─────────────────┬───────────────────────────────────────────────┤
│  命令            │  说明                                          │
├─────────────────┼───────────────────────────────────────────────┤
│  agit init       │  初始化 .agit/ 目录 + 默认配置                  │
│  agit config     │  查看/修改配置                                  │
├─────────────────┼───────────────────────────────────────────────┤
│  agit changelog  │  AI 生成变更日志                                │
│  agit commit     │  AI 辅助提交（分析 diff → 生成 message → 确认） │
│  agit sync       │  智能同步（分析状态 → 规划步骤 → 确认执行）      │
├─────────────────┼───────────────────────────────────────────────┤
│  agit explain    │  用自然语言解释 diff / commit / 范围             │
│  agit review     │  AI 代码审查（bug、安全、风格、性能）            │
│  agit doctor     │  仓库健康检查（12 项检查 + 评分）                │
├─────────────────┼───────────────────────────────────────────────┤
│  agit agent      │  交互式 Agent（自然语言 → 任务分解 → 逐步执行）  │
├─────────────────┼───────────────────────────────────────────────┤
│  agit undo       │  撤销 agent session / 指定步骤                  │
│  agit replay     │  重放历史 session                               │
├─────────────────┼───────────────────────────────────────────────┤
│  agit --help     │  帮助                                          │
│  agit --version  │  版本                                          │
│  agit --dry-run  │  全局 dry run（覆盖配置）                       │
└─────────────────┴───────────────────────────────────────────────┘
```

---

## 十一、典型工作流

### 日常开发流

```bash
# 早上开始工作
agit doctor                    # 检查仓库健康
agit sync                      # 同步远程最新代码

# 写了一上午代码
agit review                    # 提交前 AI 审查
agit commit                    # AI 生成 commit message
agit sync                      # 推送到远程

# 下班前
agit explain HEAD~5..HEAD      # 回顾今天改了什么
```

### 发布流

```bash
agit agent --task "准备发布 v1.3.0"

# Agent 自动：
#   1. 检查是否有未提交的修改
#   2. 生成 CHANGELOG
#   3. 提交 CHANGELOG
#   4. 打 tag
#   5. 每一步 dry run 展示 → 用户确认
```

### CI 流水线

```bash
# .github/workflows/release.yml
agit config set agent.solo true
agit config set agent.dry_run false
agit changelog --output CHANGELOG.md
agit commit --message "docs: update changelog for v1.3.0"
# push 和 tag 仍然被阻断（CRITICAL），由 CI 脚本显式执行
```

---

## `--dry-run` 解释

**dry-run** = "空跑"/"试运行"，意思是**只展示 AI 会做什么，但不真正执行任何 git 操作**。

### 举个例子

正常执行：
```bash
agit sync -a --tag v1.0.0
```
```
✓ Staged 3 files
✓ Committed: "feat(auth): add login flow"
✓ Changelog updated
✓ Tagged: v1.0.0
✓ Pushed to origin/main        ← 真的推上去了
```

加上 `--dry-run`：
```bash
agit sync -a --tag v1.0.0 --dry-run
```
```
[dry-run] Would stage 3 files
[dry-run] Would commit: "feat(auth): add login flow"
[dry-run] Would write CHANGELOG.md
[dry-run] Would create tag v1.0.0
[dry-run] Would push to origin/main    ← 什么都没动，只是告诉你"我会这么做"
```

### 核心用途

| 场景 | 作用 |
|---|---|
| **首次使用** | 看看 AI 准备干什么，不放心就先 dry-run 看一眼 |
| **solo 模式** | 全自动时用 dry-run 先预览，确认没问题再真正跑 |
| **CI/CD 调试** | 验证流水线逻辑是否正确，不产生副作用 |
| **覆盖 solo** | 即使配了 `ai.solo=true`，dry-run 也不会执行任何写操作 |

本质上就是一个**只读预览模式** —— AI 照常推理、生成内容、规划步骤，但 Harness 在执行阶段把所有非 LOW 风险操作全部跳过，只打印"如果执行，会做什么"。