# GoGoal CLI 命令参考

文档中的 `gogoal` 表示：

```bash
python3.12 <skill目录>/scripts/gogoal.py
```

命令从项目根目录或其子目录执行。所有查询命令可用 `--json` 获取稳定 JSON；修改命令会返回受影响文件和建议提交说明，但永不执行 Git 提交。可用全局 `--project-root <路径>` 显式指定项目根目录。

`config.locale` 决定 CLI 帮助、成功信息、错误前缀、状态和动作的界面语言；支持 `zh-CN` 与 `en-US`。`--json` 的字段名、状态码和动作码保持稳定，用户标题、描述、结果和 Markdown 原文不翻译。提交建议按项目约定保持中文 GoGoal 格式。

## 初始化、配置与校验

| 命令 | 作用和使用方式 |
| --- | --- |
| `gogoal init [--project "名称"] [--locale zh-CN\|en-US]` | 创建 `gogoal/`、默认配置、空数据、日志、详情目录和对应语言写作指南；不覆盖已有项目。 |
| `gogoal config list` | 列出完整有效配置。 |
| `gogoal config get dashboard.port` | 按点路径读取单个值。 |
| `gogoal config set dashboard.port 4180` | 设置已有配置项；布尔和数字按 JSON 字面量解析，字符串直接传入。 |
| `gogoal summary [--archive]` | 汇总目标和任务状态，可包含归档数据。 |
| `gogoal validate [--strict]` | 校验配置、结构、编号、关联、状态、日志、指南、文档路径和一级标题；严格模式把警告视为失败。 |

对象创建后应立即补充返回路径中的 Markdown；标题更新后应立即同步一级标题。文档缺失或标题不同步时，后续业务修改会停止，直到 `validate` 重新通过。用户任务没有 Markdown，不产生该短暂状态。

## 目标查询与流转

| 命令 | 作用和使用方式 |
| --- | --- |
| `gogoal goal list [--status active] [--archive\|--all]` | 查询目标。默认仅未归档。 |
| `gogoal goal show 1` | 返回目标完整结构化信息和是否归档。 |
| `gogoal goal context 1` | 返回目标及全部关联 AI/用户任务的紧凑上下文。 |
| `gogoal goal create --title "标题" --description "描述"` | 登记 `pending` 目标并分配永久编号与 `targets/<id>.md` 路径。随后由主 AI 创建 Markdown。 |
| `gogoal goal update 1 [--title "新标题"] [--description "新描述"]` | 更新标题和/或描述；标题变化后主 AI 同步 Markdown 一级标题。 |
| `gogoal goal start 1` | 在用户已经批准当前计划后从 `pending` 进入 `active`。 |
| `gogoal goal block 1 --reason "原因" --condition "解除条件"` | 从 `active` 阻塞目标；存在 `active` AI 任务时拒绝。 |
| `gogoal goal resume 1` | 解除阻塞并恢复为 `active`。 |
| `gogoal goal submit 1` | 所有关联任务终态后从 `active` 提交为 `review`。 |
| `gogoal goal revise 1 --note "验收修改摘要"` | 根据用户范围内修改要求从 `review` 恢复为 `active`。 |
| `gogoal goal complete 1` | 用户验收通过后从 `review` 完成目标。 |
| `gogoal goal cancel 1 --reason "取消原因"` | 取消目标，并一致地取消全部非终态关联任务。 |
| `gogoal goal archive 1` | 归档终态目标及仍在活动区的终态关联任务，Markdown 不移动。 |

## 任务查询与流转

AI 和用户任务分别编号，因此单对象命令必须传 `--type ai` 或 `--type user`。

| 命令 | 作用和使用方式 |
| --- | --- |
| `gogoal task list [--goal 1] [--type ai\|user] [--status blocked] [--archive\|--all]` | 组合筛选任务。 |
| `gogoal task show 2 --type ai` | 查询单个任务。 |
| `gogoal task capacity` | 显示配置上限、环境有效上限、活跃数、剩余名额、阻塞数和 Git 能力。 |
| `gogoal task create --type ai --goal 1 --title "标题" --description "描述"` | 为 `active` 目标登记 AI 任务；随后由主 AI 创建 `tasks/<id>.md`。 |
| `gogoal task create --type user --kind dependency\|decision\|other --goal 1 --title "标题" --description "描述"` | 登记需要用户提供、决定或处理的事项，不创建 Markdown。 |
| `gogoal task update 2 --type ai\|user [--title "新标题"] [--description "新描述"]` | 更新允许状态下的任务信息。 |
| `gogoal task start 2 --type ai` | 容量允许且目标为 `active` 时启动 AI 任务；调用前主 AI 必须确认文档中声明的前置任务、用户依赖和共享资源已经就绪。 |
| `gogoal task block 2 --type ai --reason "原因" --condition "解除条件"` | 阻塞活跃 AI 任务并释放并行名额。 |
| `gogoal task resume 2 --type ai` | 恢复阻塞任务；允许非抢占式临时超额。 |
| `gogoal task complete 2 --type ai` | 主 AI 确认整合与验证门槛后完成任务。 |
| `gogoal task complete 2 --type user --result "用户交付或决定"` | 保存非空结果并完成用户任务。 |
| `gogoal task cancel 2 --type ai --reason "取消原因"` | 取消 AI 任务。 |
| `gogoal task cancel 2 --type user --result "取消原因"` | 保存非空原因并取消用户任务。 |
| `gogoal task archive 2 --type ai\|user` | 归档终态任务。 |

“实现”不是生命周期命令。它只用于主 AI 对已经通过对应验证的有意义实现提交使用 `AI任务-实现-A-<id>-<标题>` 提交说明；不改变任务状态，也不写 `log.json`。

## 日志与看板

| 命令 | 作用和使用方式 |
| --- | --- |
| `gogoal log list [--limit 50] [--goal 1] [--entity goal\|ai\|user] [--id 2] [--action block]` | 从最新到最旧查询管理日志。默认最近 20 条。 |
| `gogoal log show 15` | 查询一条完整日志。 |
| `gogoal dashboard serve [--host 127.0.0.1] [--port 4180] [--open]` | 启动动态读取项目数据的本地只读看板；参数只临时覆盖本次监听，不修改配置。 |

看板默认只监听 `127.0.0.1`。通过配置或 `--host` 指定非本机地址时不会再次确认，应仅在可信网络中使用。

CLI 不提供日志新增/修改/删除、静态看板导出、Git 提交、推送、PR、发布、子代理调度或 Markdown 正文生成命令。

## 退出码

- `0`：成功。
- `2`：参数、环境、状态迁移、数据、校验或安全边界错误。
- `130`：用户中断。
