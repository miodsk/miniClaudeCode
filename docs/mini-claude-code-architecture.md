# Mini Claude Code 实现说明

本文档用于系统整理当前项目的实现思路、模块分工、消息流转方式，以及各阶段能力是如何逐步落地的。

项目目标不是 1:1 复制官方 Claude Code，而是基于 `LangChain + DeepSeek` 做一个可运行、可扩展、可继续实验的 `mini Claude Code harness`。

---

## 1. 项目整体目标

当前项目的核心目标是实现一个具备以下能力的智能体系统：

- 主智能体循环执行用户请求
- 通过工具系统访问文件、目录、搜索、后台命令等能力
- 通过任务系统记录计划与状态
- 支持子智能体与多智能体协作
- 支持技能按需加载
- 支持长上下文压缩
- 支持后台任务与团队协议
- 支持 worktree/workspace 隔离执行

整体上，它已经不再是一个简单的“工具调用 demo”，而是一个具备 agent harness 雏形的工程项目。

---

## 2. 目录结构与职责划分

当前关键文件可以按职责分为以下几层：

### 2.1 入口层

- `main.py`

负责主智能体循环，是整个系统的主入口。它完成：

- 初始化主模型
- 初始化 `TeamManager`
- 构建 lead 工具集
- 接收用户输入
- 驱动主循环与队友循环
- 执行工具调用
- 保存对话历史到 `output.json`

### 2.2 团队编排层

- `team.py`

负责多智能体团队编排，是当前系统里最重要的 orchestration 模块。它管理：

- `lead / researcher / coder` 三种角色
- mailbox 邮件通信
- shutdown / reactivation / merge / plan 等协议
- agent workspace / worktree
- workspace-aware 工具包装
- 非 lead agent 的执行循环

### 2.3 静态工具策略层

- `graph/tool_policy.py`

负责定义每个角色的**静态工具权限**。

这里把工具分组后再按角色分配，例如：

- `lead`：更偏管理、审阅、协调
- `researcher`：更偏只读调查
- `coder`：更偏实现与后台执行

这让“角色拥有什么静态工具”成为一个中心化配置，而不是分散写在各个地方。

### 2.4 工具实现层

- `graph/tools/*.py`

负责实现各种具体工具，例如：

- 文件读写
- 目录遍历
- Web 搜索
- 技能加载
- 后台命令
- 子智能体任务
- 任务系统

### 2.5 消息处理层

- `graph/prepare_main_messages.py`
- `graph/message_compaction.py`
- `graph/execute_tool_calls.py`

负责：

- 主消息预处理
- 后台通知注入
- 长上下文压缩
- 工具调用执行与状态记录

---

## 3. 主循环是怎么工作的

主循环定义在 `main.py` 的 `loop()` 中。

### 3.1 初始化阶段

主循环首先完成这些初始化：

1. 创建 `TeamManager`
2. 取出 `lead` 的消息上下文
3. 通过 `get_static_tools_for_agent("lead") + team.get_agent_tools("lead")` 组装 lead 的工具集
4. 用 `deepseek.bind_tools(...)` 绑定工具

这样 lead 就同时拥有：

- 静态工具（文件、任务、技能、压缩等）
- 动态团队工具（发送邮件、审批、shutdown、merge response 等）

### 3.2 每轮用户请求处理

主循环逻辑大致如下：

1. 用户输入问题
2. 将问题提交给 lead：`team.submit_user_task(query)`
3. lead 循环运行直到当前轮不再有工具调用

在每轮 lead 调用前，会做三件重要的事：

#### A. 投递 lead 的未读邮件

```python
team.deliver_mail("lead")
```

这样 researcher / coder 回报的内容会在下一轮进入 lead 的上下文。

#### B. 预处理消息

通过 `prepare_main_messages(...)` 完成：

- micro compaction
- auto compaction
- 后台任务完成通知注入

#### C. 调用 lead 模型

```python
response = lead_llm.invoke(input=messages)
```

若有工具调用，则交给 `execute_tool_calls(...)` 处理。

### 3.3 主循环与团队循环联动

你后来做了一个很重要的改进：

```python
team_responses = team.team_cycle(deepseek)
```

并将本轮 researcher / coder 的结果摘要注入回 lead 上下文：

```python
<team_cycle>
[researcher] ...
[coder] ...
</team_cycle>
```

这一步补足了原先 “team_cycle 返回值被丢弃” 的问题，使主循环能够感知当前轮队友做了什么。

---

## 4. TeamManager 是怎么实现团队协作的

`team.py` 中的 `TeamManager` 是整个系统目前最核心的模块。

### 4.1 角色模型

当前有三个角色：

- `lead`：主协调者，负责面向用户、拆解任务、审查计划、审查 merge、整合答案
- `researcher`：调研者，负责读文件、找信息、总结
- `coder`：执行者，负责修改文件、执行命令、提交 merge 请求

每个角色都有自己的：

- `messages`
- mailbox
- 运行状态 `agent_status`
- workspace

### 4.2 mailbox 协议

团队成员之间不是共享上下文，而是通过 mailbox 沟通：

- `send_message(...)`
- `check_mail()`
- `deliver_mail(agent_name)`

每封 `Mail` 包含：

- `sender`
- `recipient`
- `content`
- `message_type`
- `metadata`

这让团队通信是**结构化的**，而不是简单把字符串硬塞进消息历史。

### 4.3 团队协议

当前已经实现了三类 protocol：

#### A. 计划审批协议

- `submit_plan_request(...)`
- `respond_plan_request(...)`

用于 researcher 向 lead 提交高风险计划。

#### B. 停机协议

- `request_shutdown(...)`
- `respond_shutdown(...)`
- `reactivate_agent(...)`

用于 lead 优雅停止某个 agent，并允许后续重新激活。

#### C. 合并协议

- `submit_merge_request(...)`
- `respond_merge_request(...)`

用于 coder 在自己的 worktree 分支上完成实现后，正式向 lead 提交“请求合并”的协议化请求。

这使得 coder 不直接决定“合并进主线”，而是由 lead 审查后决定。

### 4.4 动态工具构造

`get_agent_tools(agent_name)` 负责给不同角色构造**动态团队工具**。

例如：

- 所有人都有：`send_message`、`check_mail`
- researcher 有：`submit_plan_request`
- coder 有：`submit_merge_request`
- lead 有：`request_shutdown`、`reactivate_agent`、`respond_plan_request`、`respond_merge_request`

这部分目前功能已经可用，但结构上逐渐变得拥挤，是后续值得重构的点。

---

## 5. 静态工具权限是怎么实现的

静态工具由 `graph/tool_policy.py` 管理。

### 5.1 工具分组

当前分成这些组：

- `inspect`
- `edit`
- `task_manage`
- `task_read`
- `background`
- `knowledge`
- `context`
- `outsource`

### 5.2 角色权限策略

通过 `AGENT_TOOL_POLICY` 配置：

- `lead` 拿管理/审阅/调度相关静态工具
- `researcher` 拿只读调查类静态工具
- `coder` 拿实现与后台执行相关静态工具

### 5.3 解析函数

`get_static_tools_for_agent(agent_name)` 负责：

1. 取出该角色的工具组列表
2. 从 `TOOL_GROUPS` 里解析成工具对象
3. 去重后返回

这实现了角色静态权限中心化管理。

---

## 6. 任务系统是怎么实现的

任务系统实现于 `graph/tools/todo_list.py`，但现在它实际上已经不只是 todo，而是持久化任务板。

### 6.1 数据模型

任务包括：

- `id`
- `subject`
- `status`
- `blocks`
- `blocked_by`
- `description`

### 6.2 持久化方式

每个任务写入 `.tasks/task_<id>.json`

这意味着任务在：

- 压缩上下文后仍然存在
- 程序重启后仍然存在

### 6.3 核心能力

- `task_create`
- `task_update`
- `task_list`
- `task_get`

### 6.4 自动解锁依赖

当某个任务完成时，`_clear_dependency()` 会自动把它从其他任务的 `blocked_by` 中移除。

这让任务系统具备了基本的 DAG/依赖能力，而不是简单扁平清单。

---

## 7. 子智能体是怎么实现的

子智能体实现于 `graph/tools/sub_agent_task.py`。

### 核心思路

与主智能体不同，子智能体有自己的独立消息上下文：

- 不继承主循环全部上下文
- 只接收一个 prompt
- 自己循环调用工具
- 最终只返回摘要文本

### 为什么这样做

这样可以避免主智能体消息无限膨胀，也能把一次性外包工作局部化。

当前 `sub_agent_task` 更像**临时外包 agent**，而不是正式团队成员。

---

## 8. 技能系统是怎么实现的

技能系统实现于 `graph/tools/load_skill.py`。

### 8.1 技能来源

从 `graph/skills/*/SKILL.md` 扫描技能文件。

### 8.2 解析方式

每个技能文件包含：

- frontmatter（name / description）
- body（完整技能内容）

### 8.3 两层设计

#### Layer 1

系统 prompt 中只放技能描述列表：

```text
可用技能:
- git: ...
- test: ...
```

#### Layer 2

当模型调用 `load_skill(name)` 时，再返回完整技能正文。

这样避免把所有技能全文都塞进 system prompt，节省 token。

---

## 9. 上下文压缩是怎么实现的

压缩逻辑主要在：

- `graph/message_compaction.py`
- `graph/prepare_main_messages.py`

### 9.1 Layer 1：micro compaction

`micro_compact()` 会把过旧的 `ToolMessage` 内容替换为：

```text
[Previous: used xxx]
```

只保留最近几个工具结果的完整内容。

### 9.2 Layer 2：auto compaction

`auto_compact()` 会在 token 超过阈值时：

1. 把完整对话写到 `.transcripts/`
2. 用模型总结对话
3. 用总结替换原始消息

### 9.3 Layer 3：manual compaction

模型主动调用 `compact` 工具时，也会触发压缩。

### 9.4 主循环预处理

`prepare_main_messages()` 会在每轮 lead 调用前统一做：

- micro compaction
- token 阈值检查
- auto compaction
- 注入后台任务结果

---

## 10. 后台任务是怎么实现的

后台任务实现于 `graph/tools/background_task.py`。

### 10.1 核心对象

- `BackgroundManager`

管理：

- `tasks`
- `_notification_queue`
- 线程执行

### 10.2 关键能力

- `run(command, cwd=None)`
- `check(task_id="")`
- `drain_notifications()`

### 10.3 线程模型

后台任务通过 `Thread(..., daemon=True)` 异步执行，不阻塞主循环。

### 10.4 与 workspace 结合

你后来把 `BG_MANAGER.run(command, cwd=str(workspace))` 接入了 workspace-bound wrapper。

这使得 coder / researcher 的后台命令可以真正跑在它们自己的 worktree 目录里。

---

## 11. workspace / worktree 隔离是怎么实现的

这部分主要在 `team.py` 中完成，是当前项目非常关键的一步。

### 11.1 核心状态

`agent_workspaces` 记录每个 agent 的工作目录：

- lead → 主工作区
- researcher → 独立 worktree
- coder → 独立 worktree

### 11.2 worktree 生命周期起点

`ensure_agent_workspace(agent_name)` 会：

1. 如果是 lead，则直接用主目录
2. 如果是 researcher / coder，则确保对应 worktree 存在
3. 必要时执行 `git worktree add`

### 11.3 原始问题

最开始只是把 workspace 路径提示给 agent：

```text
你的工作目录是 xxx，只在该目录下读写文件。
```

这只是 prompt 约束，不是真正的 harness 约束。

### 11.4 关键升级：workspace-bound tools

现在 `TeamManager.get_workspace_bound_tools()` 会对以下工具做 wrapper：

- `read_file`
- `write_file`
- `list_dir`
- `background_run`

### 11.5 具体策略

#### 文件类工具

- agent 传相对路径
- wrapper 自动拼到当前 agent 的 workspace 下
- 用 `Path.relative_to()` 做越界检查
- 越界直接返回错误

#### 后台命令工具

- agent 只传 command
- wrapper 自动把 `cwd` 设为当前 workspace
- 调用 `BG_MANAGER.run(command, cwd=workspace)`

### 11.6 为什么这一步重要

这一步让 s12 从：

> “告诉模型你应该在哪工作”

变成：

> “harness 强制工具只能在你的 workspace 内执行”

这是当前项目一个很重要的工程化突破。

---

## 12. merge_request 与分支生命周期的关系

当前 merge protocol 已经实现，但还属于“协议层已到位、自动集成层未完全打通”。

### 当前已有能力

- coder 可以调用 `submit_merge_request(branch, commit, summary)`
- lead 可以调用 `respond_merge_request(request_id, approve, feedback)`
- `merge_requests` 持有：
  - from
  - to
  - branch
  - commit
  - summary
  - status

### 当前语义

这使得 coder 不再只发一封普通文本消息说“我做完了”，而是可以发送一个**正式审批请求**。

### 仍可继续完善的点

后续可以继续打通：

- 自动获取当前 worktree branch
- 自动获取最近 commit hash
- lead 批准后触发 merge / cherry-pick 流程

也就是说，现在协议已经有了，但还没真正接到“Git 集成动作”上。

---

## 13. 测试覆盖到哪了

目前测试集中在 `tests/test_team_manager.py`。

当前已经覆盖：

- coder 注册
- mailbox 存在
- shutdown request / response
- reactivation
- merge request / response
- merge/shutdown 动态工具暴露
- workspace 越界拦截
- workspace 内写文件
- background_run 使用正确 cwd

这说明：

- 团队协议层有基本测试兜底
- workspace 绑定的核心行为已有最小测试

但还可以继续补：

- worktree 创建成功 / 失败路径
- branch 已存在时的处理
- merge_request 与真实 git branch/commit 的自动联动

---

## 14. 当前项目的优点与不足

### 优点

1. 已经形成了完整的 agent harness 雏形
2. 不只是一个 tool demo，而是有：任务、团队、协议、压缩、后台、workspace
3. 核心抽象开始稳定：
   - `TeamManager`
   - `tool_policy`
   - `prepare_main_messages`
   - `execute_tool_calls`
4. 已有一定测试基础

### 不足

1. `get_agent_tools()` 开始变乱，适合后续重构
2. `merge_request` 还没真正联动到 git 合并动作
3. mailbox / requests 还未持久化
4. worktree 清理与生命周期回收还不完整
5. 某些工具仍然比较轻量，工程稳健性还可以继续加强

---

## 15. 当前阶段结论

如果把这个项目定义为一个 `mini Claude Code`，那么它已经是：

- **学习版：合格且偏强**
- **工程版：已有骨架，但还在继续工程化**

它最大的价值不在于“是否完全复刻官方 Claude Code”，而在于：

> 你已经逐步把一个单体 agent loop，演化成了一个有团队、有协议、有任务板、有上下文治理、有 workspace 隔离的 agent harness。

这已经是一个非常扎实的 mini Claude Code 项目。

---

## 16. 后续建议

如果继续推进，建议优先级如下：

1. 重构 `get_agent_tools()`
2. 让 `merge_request` 自动携带当前 branch / commit 信息
3. 给 worktree 生命周期补更多测试和清理逻辑
4. 把 mailbox / requests 做持久化
5. 再逐步考虑把部分 TeamManager 内部逻辑拆成独立模块
