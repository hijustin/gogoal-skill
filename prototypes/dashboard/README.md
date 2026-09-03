# GoGoal 看板页面原型

这是根据 [`docs/design/page.md`](../../docs/design/page.md)、[`docs/design/design.md`](../../docs/design/design.md) 和 [`docs/architecture/blueprint.md`](../../docs/architecture/blueprint.md) 实现的单页面交互原型，用于验证 GoGoal 目标任务看板的信息架构与视觉方向。

## 已实现内容

- 顶部项目、数据连接、归档切换、全局搜索、设备时间、180 秒自动刷新和主题控制，不展示时区。
- 左侧目标列表，以及右侧 AI 任务、用户任务和管理时间线区域。
- 目标与任务联动选择、状态分栏、内部滚动和空状态。
- 输入即搜索，支持编号、标题、状态和描述模糊匹配。
- 卡片停留一秒展示信息浮层，双击打开详情阅读弹窗。
- 亮色和暗色主题、键盘搜索快捷键与 `Esc` 关闭弹窗。
- 采用与 GoGoal 蓝图一致的目标、AI 任务、用户任务和日志演示数据。

当前数据均为前端原型数据，尚未连接 GoGoal CLI 的只读 HTTP 服务。

## 本地运行

```bash
npm install
npm run dev
```

默认访问地址为 `http://localhost:3000/`。

## 验证

```bash
npm run lint
npm test
```

`npm test` 会完成生产构建，并验证服务端首屏内容与核心交互结构。
