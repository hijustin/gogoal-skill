# GoGoal 数据与存储标准

## 项目目录

```text
gogoal/
├── config.json
├── goal-writing.md
├── task-writing.md
├── target.json
├── target-archive.json
├── task.json
├── task-archive.json
├── log.json
├── targets/<目标编号>.md
└── tasks/<AI任务编号>.md
```

四个聚合 JSON 是结构化当前事实源。对象编号在活动和归档数据中共同扫描，永久不复用。目标、AI 任务和用户任务分别独立编号。

## 配置

```json
{
  "format": 1,
  "project": "项目名称",
  "locale": "zh-CN",
  "execution": { "maxParallelTasks": 2 },
  "git": {
    "enabled": true,
    "autoCommit": true,
    "branchPrefix": "gogoal/",
    "worktreeRoot": "../.gogoal-worktrees"
  },
  "dashboard": {
    "host": "127.0.0.1",
    "port": 4173,
    "refreshSeconds": 180,
    "autoOpen": false,
    "gitActivity": true
  }
}
```

- `format`：数据格式版本，当前只支持整数 `1`。
- `project`：看板项目名，非空字符串。
- `locale`：固定为 `zh-CN` 或 `en-US`。
- `execution.maxParallelTasks`：配置并行上限，整数且至少为一。
- `git.enabled`：启用 Git 能力检测、分支/工作树规则和可选 Git 活动；不会自动提交。
- `git.autoCommit`：允许主 AI 在完整动作或已验证实现后自主创建范围明确的本地提交；CLI 永不提交。
- `git.branchPrefix`：任务分支前缀；保存时规范化为以 `/` 结尾。
- `git.worktreeRoot`：任务工作树根目录，必须位于主仓库之外。
- `dashboard.host`、`port`：只读 HTTP 服务监听地址和端口。
- `dashboard.refreshSeconds`：页面重新读取数据的间隔，至少一秒。
- `dashboard.autoOpen`：启动服务后是否尝试打开浏览器。
- `dashboard.gitActivity`：Git 集成有效时是否补充符合 GoGoal 提交格式的历史。

配置对象及其嵌套对象只允许上表定义的字段。未知字段、缺失字段、错误类型和不兼容的 `format` 均由 `validate` 拒绝；CLI 不猜测或静默迁移数据。

## 目标

`target.json` 与 `target-archive.json` 根字段均为 `targets` 数组。活动目标字段：

```json
{
  "id": 1,
  "title": "建立任务管理看板",
  "description": "提供全局可视化能力",
  "status": "active",
  "document": "targets/1.md",
  "recordedAt": "2026-08-25 10:00",
  "endedAt": null,
  "blocker": null
}
```

状态只允许 `pending`、`active`、`blocked`、`review`、`completed`、`cancelled`。归档记录保留终态并增加非空 `archivedAt`。

## 任务

任务文件根结构为 `{"aiTasks": [], "userTasks": []}`。AI 任务字段：

```json
{
  "id": 1,
  "title": "实现校验器",
  "description": "校验数据与文档一致性",
  "status": "pending",
  "goalId": 1,
  "document": "tasks/1.md",
  "recordedAt": "2026-08-25 10:10",
  "endedAt": null,
  "blocker": null
}
```

AI 状态只允许 `pending`、`active`、`blocked`、`completed`、`cancelled`。用户任务字段：

```json
{
  "id": 1,
  "title": "确认许可证",
  "description": "确认开源许可证选择",
  "kind": "decision",
  "status": "pending",
  "result": null,
  "goalId": 1,
  "recordedAt": "2026-08-25 10:15",
  "endedAt": null
}
```

用户状态只允许 `pending`、`completed`、`cancelled`；类型只允许 `dependency`、`decision`、`other`。用户任务不建立 Markdown。归档任务增加非空 `archivedAt`。

各类记录只允许对应 schema 中声明的字段。活动任务不得关联归档目标；非终态任务只能关联 `active` 或 `blocked` 目标。`pending` 目标不得已有任务，`blocked` 目标不得保留 `active` AI 任务，`review`、`completed`、`cancelled` 目标的全部关联任务必须为终态。

## 管理日志

`log.json` 根字段为 `logs` 数组。日志追加且不提供写 API：

```json
{
  "id": 1,
  "time": "2026-08-25 10:00",
  "entity": "goal",
  "entityId": 1,
  "goalId": 1,
  "title": "建立任务管理看板",
  "action": "create",
  "statusFrom": null,
  "statusTo": "pending",
  "note": null
}
```

`entity` 为 `goal`、`ai`、`user`；动作必须属于对应命令枚举。日志不记录 actor、完整差异或标题前后值。实现提交属于 Git 历史，不写业务日志。

校验器逐条检查动作允许的源状态和目标状态、对象状态链连续性、最后状态以及最后标题快照；不能只靠最终状态相同来接受被篡改的动作历史。

## 不变量与存储

- `blocker` 当且仅当状态是 `blocked` 时为含非空 `reason`、`condition` 的对象。
- `endedAt` 当且仅当状态是 `completed` 或 `cancelled` 时非空。
- `archivedAt` 只在归档记录中存在；归档记录只能是终态。
- 用户任务终态必须有非空 `result`。
- 所有任务必须关联存在的目标；只有活动 `active` 目标可新增任务。
- Markdown 路径必须位于 `gogoal/` 内，文件名与编号稳定，一号标题须与 JSON 编号和当前标题一致。
- 时间直接使用设备本地时间 `YYYY-MM-DD HH:mm`，不保存时区或 UTC 偏移；除格式外还必须是有效日历时间。
- 修改命令在同一个跨平台文件锁内重新读取数据，写临时文件、原子替换并在正常失败时回滚。进程强制终止等极端情况由 `validate` 检出。
- 除创建对象或改标题会产生等待 AI 补文档的短暂状态外，业务修改前必须在锁内通过 JSON、日志、指南和对象 Markdown 的完整一致性检查；未恢复一致性时拒绝继续流转。
- CLI 对写后文件执行字节核对。JSON、日志、指南和对象 Markdown 发现常见凭据模式时校验失败，但模式检测不能替代主 AI 的人工安全审查。
