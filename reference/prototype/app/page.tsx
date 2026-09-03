"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type GoalStatus = "pending" | "active" | "blocked" | "review" | "completed" | "cancelled";
type AiStatus = "pending" | "active" | "blocked" | "completed" | "cancelled";
type UserStatus = "pending" | "completed" | "cancelled";
type EntityKind = "goal" | "ai" | "user";

type Goal = {
  id: number;
  title: string;
  description: string;
  status: GoalStatus;
  recordedAt: string;
  updatedAt: string;
  archived: boolean;
  blocker?: string;
};

type AiTask = {
  id: number;
  goalId: number;
  title: string;
  description: string;
  status: AiStatus;
  recordedAt: string;
  updatedAt: string;
  archived: boolean;
  blocker?: string;
};

type UserTask = {
  id: number;
  goalId: number;
  title: string;
  description: string;
  status: UserStatus;
  kind: "dependency" | "decision" | "other";
  recordedAt: string;
  updatedAt: string;
  archived: boolean;
  result?: string;
};

type LogItem = {
  id: number;
  time: string;
  entity: EntityKind;
  entityId: number;
  goalId: number;
  title: string;
  action: string;
  statusFrom: string | null;
  statusTo: string | null;
  note?: string;
};

type HoverInfo = {
  kind: EntityKind;
  id: number;
  title: string;
  status: string;
  fields: Array<{ label: string; value: string | number | null | undefined }>;
  x: number;
  y: number;
};

const locale = "zh-CN" as const;
const messages = {
  "zh-CN": {
    status: {
      pending: "待处理",
      active: "进行中",
      blocked: "已阻塞",
      review: "待验收",
      completed: "已完成",
      cancelled: "已取消",
    } as Record<string, string>,
    action: {
      create: "创建",
      update: "更新",
      start: "启动",
      block: "标记阻塞",
      resume: "恢复推进",
      submit: "提交验收",
      revise: "进入修改",
      complete: "完成",
      cancel: "取消",
      archive: "归档",
    } as Record<string, string>,
    kind: {
      dependency: "外部依赖",
      decision: "需要决策",
      other: "其他事项",
    } as Record<string, string>,
    field: {
      id: "编号",
      title: "标题",
      description: "描述",
      status: "状态",
      document: "文档路径",
      recordedAt: "登记时间",
      endedAt: "结束时间",
      blockerReason: "阻塞原因",
      blockerCondition: "解除条件",
      archivedAt: "归档时间",
      goalId: "所属目标编号",
      kind: "任务类型",
      result: "处理结果",
    },
    connectionReady: "数据已连接",
    dataScope: "数据范围",
    unarchived: "未归档",
    archived: "已归档",
    searchLabel: "搜索目标和任务",
    searchPlaceholder: "搜索编号、标题、状态或描述",
    clearSearch: "清空搜索",
    syncing: "正在同步…",
    dataUpdated: "数据已更新",
    autoRefresh: "自动 180s",
    refreshData: "刷新数据",
    manualRefresh: "手动刷新",
    switchTheme: "切换主题",
    themeTip: "切换明暗主题",
    goal: "目标",
    aiTask: "AI 任务",
    userTask: "用户任务",
    timeline: "时间线",
    statusSummary: "状态统计",
    noMatchingGoal: "没有匹配的目标",
    adjustSearch: "尝试调整搜索条件或切换数据范围。",
    noTask: "暂无任务",
    chooseWork: "选择目标或任务",
    timelineEmpty: "单击卡片后，这里会按时间倒序展示对应的管理活动。",
    none: "无",
    itemUnit: "条",
    hoverHint: "双击卡片查看完整详情",
    goalDocument: "目标文档",
    aiDocument: "AI 任务文档",
    userDetail: "用户任务详情",
    closeDetail: "关闭详情",
    currentStatus: "当前状态",
    recordedAt: "登记时间",
    updatedAt: "最近更新",
    parentGoal: "所属目标",
  },
};
const ui = messages[locale];
const statusLabels = ui.status;
const actionLabels = ui.action;
const kindLabels = ui.kind;

const goalStatuses: GoalStatus[] = ["pending", "active", "blocked", "review", "completed", "cancelled"];
const aiStatuses: AiStatus[] = ["pending", "active", "blocked", "completed", "cancelled"];
const userStatuses: UserStatus[] = ["pending", "completed", "cancelled"];

const goals: Goal[] = [
  { id: 9, title: "发布 GoGoal 开源 Skill", description: "完成安装体验、仓库说明、演示材料与 GitHub 发布准备。", status: "pending", recordedAt: "2026-08-18 10:20", updatedAt: "2026-08-18 10:20", archived: false },
  { id: 8, title: "完善目标任务文档规范", description: "确定目标与 AI 任务 Markdown 的稳定章节、更新边界和阅读方式。", status: "active", recordedAt: "2026-08-17 09:30", updatedAt: "2026-08-18 13:40", archived: false },
  { id: 7, title: "建立目标任务可视化看板", description: "实现单页只读看板，展示目标、AI 任务、用户任务和管理时间线。", status: "active", recordedAt: "2026-08-16 11:00", updatedAt: "2026-08-18 14:24", archived: false },
  { id: 6, title: "稳定化目标执行流程", description: "覆盖阻塞、恢复、验收修改、完成、取消与归档等关键路径。", status: "blocked", recordedAt: "2026-08-15 16:00", updatedAt: "2026-08-18 11:10", archived: false, blocker: "需要确认验收修改是否允许新增用户任务" },
  { id: 5, title: "定义 GoGoal 数据模型", description: "收敛配置、目标、任务、归档和管理日志的结构化格式。", status: "review", recordedAt: "2026-08-14 10:00", updatedAt: "2026-08-18 12:36", archived: false },
  { id: 4, title: "实现 CLI 数据内核", description: "提供可验证的状态查询、修改、归档和日志维护命令。", status: "completed", recordedAt: "2026-08-13 14:20", updatedAt: "2026-08-17 18:42", archived: false },
  { id: 3, title: "验证外部任务系统接入", description: "评估直接同步第三方任务平台的复杂度和维护成本。", status: "cancelled", recordedAt: "2026-08-12 09:00", updatedAt: "2026-08-15 15:12", archived: false },
  { id: 2, title: "整理早期文档索引方案", description: "以 Markdown 索引管理目标和任务基础信息。", status: "cancelled", recordedAt: "2026-08-09 10:30", updatedAt: "2026-08-12 16:00", archived: true },
  { id: 1, title: "验证目标驱动工作流", description: "通过真实项目检验目标分析、任务拆分与自主执行流程。", status: "completed", recordedAt: "2026-08-01 09:00", updatedAt: "2026-08-11 19:20", archived: true },
];

const aiTasks: AiTask[] = [
  { id: 18, goalId: 9, title: "编写 GitHub 发布说明", description: "整理定位、安装步骤、演示截图和安全边界。", status: "pending", recordedAt: "2026-08-18 10:24", updatedAt: "2026-08-18 10:24", archived: false },
  { id: 17, goalId: 8, title: "起草目标文档模板", description: "定义目标分析、范围、实施计划与验收结论等章节。", status: "active", recordedAt: "2026-08-17 10:00", updatedAt: "2026-08-18 13:40", archived: false },
  { id: 16, goalId: 7, title: "实现看板交互原型", description: "完成卡片筛选、联动选择、详情阅读与明暗主题。", status: "active", recordedAt: "2026-08-18 09:10", updatedAt: "2026-08-18 14:24", archived: false },
  { id: 15, goalId: 7, title: "实现只读数据服务", description: "提供配置、目标、任务、日志和 Markdown 的只读接口。", status: "pending", recordedAt: "2026-08-18 09:00", updatedAt: "2026-08-18 09:00", archived: false },
  { id: 14, goalId: 6, title: "补充验收修改流程", description: "覆盖 review 到 active 的回退和任务重开规则。", status: "blocked", recordedAt: "2026-08-16 09:20", updatedAt: "2026-08-18 11:10", archived: false, blocker: "等待用户确认修改阶段的任务边界" },
  { id: 13, goalId: 5, title: "校验日志级联规则", description: "验证目标取消和归档时每个关联任务均形成独立日志。", status: "completed", recordedAt: "2026-08-15 14:00", updatedAt: "2026-08-18 12:00", archived: false },
  { id: 12, goalId: 5, title: "统一状态枚举", description: "将目标与任务内部状态统一为单个英文单词。", status: "completed", recordedAt: "2026-08-15 11:30", updatedAt: "2026-08-17 17:00", archived: false },
  { id: 11, goalId: 4, title: "实现数据校验器", description: "校验目标、任务、状态、编号与文档路径的一致性。", status: "completed", recordedAt: "2026-08-14 14:20", updatedAt: "2026-08-17 18:42", archived: false },
  { id: 10, goalId: 3, title: "实现第三方平台同步器", description: "在第三方平台与本地数据之间建立双向同步。", status: "cancelled", recordedAt: "2026-08-12 10:00", updatedAt: "2026-08-15 15:12", archived: false },
  { id: 3, goalId: 2, title: "生成 Markdown 汇总索引", description: "根据目标和任务详情生成四份 Markdown 索引。", status: "cancelled", recordedAt: "2026-08-09 11:00", updatedAt: "2026-08-12 16:00", archived: true },
  { id: 2, goalId: 1, title: "完成真实项目试运行", description: "使用目标驱动流程完成一个小型开发项目。", status: "completed", recordedAt: "2026-08-02 09:00", updatedAt: "2026-08-11 18:10", archived: true },
  { id: 1, goalId: 1, title: "整理流程观察记录", description: "记录目标驱动工作流中的有效实践与常见阻塞。", status: "completed", recordedAt: "2026-08-01 10:20", updatedAt: "2026-08-11 19:20", archived: true },
];

const userTasks: UserTask[] = [
  { id: 8, goalId: 9, title: "确认开源许可证", description: "请确认首个公开版本采用 MIT 还是 Apache-2.0。", kind: "decision", status: "pending", recordedAt: "2026-08-18 10:30", updatedAt: "2026-08-18 10:30", archived: false },
  { id: 7, goalId: 8, title: "提供现有任务文档样例", description: "提供一份执行中和一份已完成任务文档，便于提取稳定结构。", kind: "dependency", status: "pending", recordedAt: "2026-08-17 10:10", updatedAt: "2026-08-17 10:10", archived: false },
  { id: 6, goalId: 7, title: "确认看板布局方向", description: "确认单页平铺、目标侧栏和上下分区的信息架构。", kind: "decision", status: "completed", result: "采用单页 1:5 分栏与右侧 60/40 分区", recordedAt: "2026-08-16 11:20", updatedAt: "2026-08-18 09:00", archived: false },
  { id: 5, goalId: 6, title: "确认验收修改边界", description: "确认目标进入修改阶段后是否允许创建新的用户任务。", kind: "decision", status: "pending", recordedAt: "2026-08-18 11:10", updatedAt: "2026-08-18 11:10", archived: false },
  { id: 4, goalId: 5, title: "复核数据字段清单", description: "复核目标、任务和日志字段是否覆盖日常管理需要。", kind: "other", status: "completed", result: "字段清单通过", recordedAt: "2026-08-15 10:30", updatedAt: "2026-08-18 12:36", archived: false },
  { id: 3, goalId: 3, title: "提供第三方平台访问凭证", description: "提供用于同步测试的第三方平台 API 访问凭证。", kind: "dependency", status: "cancelled", result: "目标取消，不再需要提供", recordedAt: "2026-08-12 10:20", updatedAt: "2026-08-15 15:12", archived: false },
  { id: 2, goalId: 2, title: "确认索引文件命名", description: "确认四份 Markdown 索引的命名方式。", kind: "decision", status: "cancelled", result: "方案废弃", recordedAt: "2026-08-09 11:20", updatedAt: "2026-08-12 16:00", archived: true },
  { id: 1, goalId: 1, title: "确认试运行结果", description: "确认目标驱动工作流是否达到日常使用标准。", kind: "decision", status: "completed", result: "流程可用，继续产品化", recordedAt: "2026-08-11 18:30", updatedAt: "2026-08-11 19:20", archived: true },
];

const logs: LogItem[] = [
  { id: 31, time: "2026-08-18 14:24", entity: "ai", entityId: 16, goalId: 7, title: "实现看板交互原型", action: "update", statusFrom: "active", statusTo: "active", note: "完成顶部工具区与主要看板骨架" },
  { id: 30, time: "2026-08-18 13:40", entity: "ai", entityId: 17, goalId: 8, title: "起草目标文档模板", action: "update", statusFrom: "active", statusTo: "active", note: "整理目标分析与范围章节" },
  { id: 29, time: "2026-08-18 12:36", entity: "goal", entityId: 5, goalId: 5, title: "定义 GoGoal 数据模型", action: "submit", statusFrom: "active", statusTo: "review", note: "字段、枚举与日志规则已完成复核" },
  { id: 28, time: "2026-08-18 12:00", entity: "ai", entityId: 13, goalId: 5, title: "校验日志级联规则", action: "complete", statusFrom: "active", statusTo: "completed", note: "级联日志测试通过" },
  { id: 27, time: "2026-08-18 11:10", entity: "ai", entityId: 14, goalId: 6, title: "补充验收修改流程", action: "block", statusFrom: "active", statusTo: "blocked", note: "等待确认修改阶段的任务边界" },
  { id: 26, time: "2026-08-18 11:10", entity: "goal", entityId: 6, goalId: 6, title: "稳定化目标执行流程", action: "block", statusFrom: "active", statusTo: "blocked", note: "关联关键任务无法继续推进" },
  { id: 25, time: "2026-08-18 10:30", entity: "user", entityId: 8, goalId: 9, title: "确认开源许可证", action: "create", statusFrom: null, statusTo: "pending" },
  { id: 24, time: "2026-08-18 10:24", entity: "ai", entityId: 18, goalId: 9, title: "编写 GitHub 发布说明", action: "create", statusFrom: null, statusTo: "pending" },
  { id: 23, time: "2026-08-18 10:20", entity: "goal", entityId: 9, goalId: 9, title: "发布 GoGoal 开源 Skill", action: "create", statusFrom: null, statusTo: "pending" },
  { id: 22, time: "2026-08-18 09:10", entity: "ai", entityId: 16, goalId: 7, title: "实现看板交互原型", action: "start", statusFrom: "pending", statusTo: "active" },
  { id: 21, time: "2026-08-18 09:00", entity: "user", entityId: 6, goalId: 7, title: "确认看板布局方向", action: "complete", statusFrom: "pending", statusTo: "completed", note: "采用单页 1:5 分栏与右侧 60/40 分区" },
  { id: 20, time: "2026-08-17 18:42", entity: "goal", entityId: 4, goalId: 4, title: "实现 CLI 数据内核", action: "complete", statusFrom: "review", statusTo: "completed", note: "命令与校验测试均通过" },
  { id: 19, time: "2026-08-17 17:00", entity: "ai", entityId: 12, goalId: 5, title: "统一状态枚举", action: "complete", statusFrom: "active", statusTo: "completed" },
  { id: 18, time: "2026-08-16 12:00", entity: "goal", entityId: 7, goalId: 7, title: "建立目标任务可视化看板", action: "start", statusFrom: "pending", statusTo: "active" },
];

function matchesSearch(item: { id: number; title: string; description: string; status: string }, query: string) {
  if (!query.trim()) return true;
  const text = `${item.id} ${item.title} ${item.description} ${item.status} ${statusLabels[item.status]}`.toLowerCase();
  return query.trim().toLowerCase().split(/\s+/).every((word) => text.includes(word));
}

function formatId(prefix: string, id: number) {
  return `${prefix}-${String(id).padStart(2, "0")}`;
}

function displayValue(value: string | number | null | undefined) {
  return value === null || value === undefined || value === "" ? "-" : String(value);
}

function goalHoverFields(goal: Goal) {
  return [
    { label: ui.field.id, value: goal.id },
    { label: ui.field.title, value: goal.title },
    { label: ui.field.description, value: goal.description },
    { label: ui.field.status, value: `${goal.status}（${statusLabels[goal.status]}）` },
    { label: ui.field.document, value: `targets/${goal.id}.md` },
    { label: ui.field.recordedAt, value: goal.recordedAt },
    { label: ui.field.endedAt, value: ["completed", "cancelled"].includes(goal.status) ? goal.updatedAt : null },
    { label: ui.field.blockerReason, value: goal.blocker },
    { label: ui.field.blockerCondition, value: null },
    ...(goal.archived ? [{ label: ui.field.archivedAt, value: goal.updatedAt }] : []),
  ];
}

function aiHoverFields(task: AiTask) {
  return [
    { label: ui.field.id, value: task.id },
    { label: ui.field.title, value: task.title },
    { label: ui.field.description, value: task.description },
    { label: ui.field.status, value: `${task.status}（${statusLabels[task.status]}）` },
    { label: ui.field.goalId, value: task.goalId },
    { label: ui.field.document, value: `tasks/${task.id}.md` },
    { label: ui.field.recordedAt, value: task.recordedAt },
    { label: ui.field.endedAt, value: ["completed", "cancelled"].includes(task.status) ? task.updatedAt : null },
    { label: ui.field.blockerReason, value: task.blocker },
    { label: ui.field.blockerCondition, value: null },
    ...(task.archived ? [{ label: ui.field.archivedAt, value: task.updatedAt }] : []),
  ];
}

function userHoverFields(task: UserTask) {
  return [
    { label: ui.field.id, value: task.id },
    { label: ui.field.title, value: task.title },
    { label: ui.field.description, value: task.description },
    { label: ui.field.kind, value: `${task.kind}（${kindLabels[task.kind]}）` },
    { label: ui.field.status, value: `${task.status}（${statusLabels[task.status]}）` },
    { label: ui.field.result, value: task.result },
    { label: ui.field.goalId, value: task.goalId },
    { label: ui.field.recordedAt, value: task.recordedAt },
    { label: ui.field.endedAt, value: ["completed", "cancelled"].includes(task.status) ? task.updatedAt : null },
    ...(task.archived ? [{ label: ui.field.archivedAt, value: task.updatedAt }] : []),
  ];
}

function StatusSummary({ statuses, items }: { statuses: string[]; items: { status: string }[] }) {
  return (
    <div className="status-summary" aria-label={ui.statusSummary}>
      {statuses.map((status) => (
        <span key={status} title={statusLabels[status]}>
          <i className={status} />
          <em>{items.filter((item) => item.status === status).length}</em>
        </span>
      ))}
    </div>
  );
}

export default function Home() {
  const [view, setView] = useState<"active" | "archive">("active");
  const [query, setQuery] = useState("");
  const [selectedGoal, setSelectedGoal] = useState<number | null>(null);
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [modal, setModal] = useState<{ kind: EntityKind; id: number } | null>(null);
  const [tooltip, setTooltip] = useState<HoverInfo | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [now, setNow] = useState(new Date());
  const [updatedAt, setUpdatedAt] = useState(new Date());
  const [refreshing, setRefreshing] = useState(false);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setModal(null);
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  const archived = view === "archive";
  const visibleGoals = useMemo(
    () => goals.filter((goal) => goal.archived === archived && matchesSearch(goal, query)).sort((a, b) => b.id - a.id),
    [archived, query],
  );

  const visibleAiTasks = useMemo(
    () => aiTasks
      .filter((task) => task.archived === archived)
      .filter((task) => selectedGoal === null || task.goalId === selectedGoal)
      .filter((task) => matchesSearch(task, query))
      .sort((a, b) => b.id - a.id),
    [archived, query, selectedGoal],
  );

  const visibleUserTasks = useMemo(
    () => userTasks
      .filter((task) => task.archived === archived)
      .filter((task) => selectedGoal === null || task.goalId === selectedGoal)
      .filter((task) => matchesSearch(task, query))
      .sort((a, b) => b.id - a.id),
    [archived, query, selectedGoal],
  );

  const timeline = useMemo(() => {
    if (selectedTask) {
      const [entity, rawId] = selectedTask.split(":");
      return logs.filter((log) => log.entity === entity && log.entityId === Number(rawId));
    }
    if (selectedGoal !== null) return logs.filter((log) => log.goalId === selectedGoal);
    return [];
  }, [selectedGoal, selectedTask]);

  const changeView = (next: "active" | "archive") => {
    setView(next);
    setSelectedGoal(null);
    setSelectedTask(null);
    setTooltip(null);
  };

  const changeQuery = (value: string) => {
    if (value.trim()) {
      setSelectedGoal(null);
      setSelectedTask(null);
    }
    setQuery(value);
  };

  const selectGoal = (id: number) => {
    setSelectedGoal((current) => current === id ? null : id);
    setSelectedTask(null);
  };

  const selectTask = (kind: "ai" | "user", id: number) => {
    const key = `${kind}:${id}`;
    setSelectedTask((current) => current === key ? null : key);
  };

  const beginHover = (info: Omit<HoverInfo, "x" | "y">, event: React.PointerEvent) => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    const x = event.clientX;
    const y = event.clientY;
    hoverTimer.current = setTimeout(() => setTooltip({ ...info, x, y }), 1000);
  };

  const moveHover = (event: React.PointerEvent) => {
    if (tooltip) setTooltip((current) => current ? { ...current, x: event.clientX, y: event.clientY } : current);
  };

  const endHover = () => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    hoverTimer.current = null;
    setTooltip(null);
  };

  const refresh = () => {
    setRefreshing(true);
    window.setTimeout(() => {
      setUpdatedAt(new Date());
      setRefreshing(false);
    }, 650);
  };

  const currentTime = new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(now);

  const modalGoal = modal?.kind === "goal" ? goals.find((item) => item.id === modal.id) : null;
  const modalAi = modal?.kind === "ai" ? aiTasks.find((item) => item.id === modal.id) : null;
  const modalUser = modal?.kind === "user" ? userTasks.find((item) => item.id === modal.id) : null;
  const modalRecord = modalGoal ?? modalAi ?? modalUser;

  return (
    <main className="app-shell" data-theme={theme}>
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true"><span>G</span></span>
          <div className="brand-copy">
            <strong>GoGoal</strong>
            <span className="project-name">目标管理技能</span>
          </div>
          <span className="connection"><i /> {ui.connectionReady}</span>
        </div>

        <div className="toolbar-center">
          <div className="view-switch" aria-label={ui.dataScope}>
            <button className={view === "active" ? "active" : ""} onClick={() => changeView("active")}>{ui.unarchived}</button>
            <button className={view === "archive" ? "active" : ""} onClick={() => changeView("archive")}>{ui.archived}</button>
          </div>
          <label className="search-box">
            <span className="search-glyph" aria-hidden="true">⌕</span>
            <input ref={searchRef} value={query} onChange={(event) => changeQuery(event.target.value)} aria-label={ui.searchLabel} placeholder={ui.searchPlaceholder} />
            {query && <button className="clear-search" onClick={() => changeQuery("")} aria-label={ui.clearSearch}>×</button>}
          </label>
        </div>

        <div className="toolbar-meta">
          <span><b suppressHydrationWarning>{currentTime}</b></span>
          <span><b>{refreshing ? ui.syncing : ui.dataUpdated}</b><small suppressHydrationWarning>{updatedAt.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })} · {ui.autoRefresh}</small></span>
          <button className={`icon-button ${refreshing ? "spinning" : ""}`} onClick={refresh} aria-label={ui.refreshData} title={ui.manualRefresh}>↻</button>
          <button className="icon-button" onClick={() => setTheme((current) => current === "light" ? "dark" : "light")} aria-label={ui.switchTheme} title={ui.themeTip}>{theme === "light" ? "☼" : "☾"}</button>
        </div>
      </header>

      <section className="board">
        <aside className="goal-panel panel">
          <PanelHeading icon="◎" title={ui.goal}>
            <StatusSummary statuses={goalStatuses} items={visibleGoals} />
          </PanelHeading>
          <div className="goal-list scroll-area">
            {visibleGoals.map((goal) => (
              <div
                key={goal.id}
                className={`work-card goal-card ${selectedGoal === goal.id ? "selected" : ""}`}
                tabIndex={0}
                role="button"
                aria-pressed={selectedGoal === goal.id}
                onClick={() => selectGoal(goal.id)}
                onDoubleClick={() => setModal({ kind: "goal", id: goal.id })}
                onKeyDown={(event) => event.key === "Enter" && selectGoal(goal.id)}
                onPointerEnter={(event) => beginHover({ kind: "goal", id: goal.id, title: goal.title, status: goal.status, fields: goalHoverFields(goal) }, event)}
                onPointerMove={moveHover}
                onPointerLeave={endHover}
              >
                <div className="card-top"><span>{formatId("G", goal.id)}</span><em className={`status ${goal.status}`}>{statusLabels[goal.status]}</em></div>
                <h2>{goal.title}</h2>
                <p>{goal.description}</p>
              </div>
            ))}
            {!visibleGoals.length && <EmptyState compact icon="⌕" title={ui.noMatchingGoal} description={ui.adjustSearch} />}
          </div>
        </aside>

        <section className="right-board">
          <section className="ai-panel panel">
            <PanelHeading icon="✦" title={ui.aiTask}>
              <StatusSummary statuses={aiStatuses} items={visibleAiTasks} />
            </PanelHeading>
            <div className="kanban-grid ai-grid">
              {aiStatuses.map((status) => {
                const tasks = visibleAiTasks.filter((task) => task.status === status);
                return (
                  <KanbanColumn key={status} status={status} count={tasks.length}>
                    {tasks.map((task) => (
                      <TaskCard
                        key={task.id}
                        kind="ai"
                        task={task}
                        selected={selectedTask === `ai:${task.id}`}
                        onSelect={() => selectTask("ai", task.id)}
                        onOpen={() => setModal({ kind: "ai", id: task.id })}
                        onHoverStart={(event) => beginHover({ kind: "ai", id: task.id, title: task.title, status: task.status, fields: aiHoverFields(task) }, event)}
                        onHoverMove={moveHover}
                        onHoverEnd={endHover}
                      />
                    ))}
                    {!tasks.length && <div className="column-empty"><span>＋</span><small>{ui.noTask}</small></div>}
                  </KanbanColumn>
                );
              })}
            </div>
          </section>

          <section className="bottom-board">
            <section className="user-panel panel">
              <PanelHeading icon="◇" title={ui.userTask}>
                <StatusSummary statuses={userStatuses} items={visibleUserTasks} />
              </PanelHeading>
              <div className="kanban-grid user-grid">
                {userStatuses.map((status) => {
                  const tasks = visibleUserTasks.filter((task) => task.status === status);
                  return (
                    <KanbanColumn key={status} status={status} count={tasks.length}>
                      {tasks.map((task) => (
                        <TaskCard
                          key={task.id}
                          kind="user"
                          task={task}
                          selected={selectedTask === `user:${task.id}`}
                          onSelect={() => selectTask("user", task.id)}
                          onOpen={() => setModal({ kind: "user", id: task.id })}
                          onHoverStart={(event) => beginHover({ kind: "user", id: task.id, title: task.title, status: task.status, fields: userHoverFields(task) }, event)}
                          onHoverMove={moveHover}
                          onHoverEnd={endHover}
                        />
                      ))}
                      {!tasks.length && <div className="column-empty"><span>＋</span><small>{ui.noTask}</small></div>}
                    </KanbanColumn>
                  );
                })}
              </div>
            </section>

            <section className="timeline-panel panel">
              <PanelHeading icon="◷" title={ui.timeline}>
                {timeline.length > 0 && <span className="count-pill">{timeline.length} {ui.itemUnit}</span>}
              </PanelHeading>
              <div className="timeline-list scroll-area">
                {!timeline.length ? (
                  <EmptyState icon="◷" title={ui.chooseWork} description={ui.timelineEmpty} />
                ) : timeline.map((item, index) => (
                  <article className="timeline-item" key={item.id}>
                    <div className={`timeline-dot ${item.entity}`}>{item.entity === "goal" ? "G" : item.entity === "ai" ? "A" : "U"}</div>
                    <div className="timeline-copy">
                      <div><strong>{actionLabels[item.action] ?? item.action}</strong><time>{item.time.slice(5)}</time></div>
                      <p>{item.title}</p>
                      {item.statusFrom !== item.statusTo && <div className="state-change"><span>{item.statusFrom ? statusLabels[item.statusFrom] : ui.none}</span><b>→</b><span>{item.statusTo ? statusLabels[item.statusTo] : ui.none}</span></div>}
                      {item.note && <small>{item.note}</small>}
                    </div>
                    {index < timeline.length - 1 && <i className="timeline-line" />}
                  </article>
                ))}
              </div>
            </section>
          </section>
        </section>
      </section>

      {tooltip && (
        <aside className="hover-card scroll-area" style={{ left: Math.max(12, Math.min(tooltip.x + 18, window.innerWidth - 408)), top: Math.max(12, Math.min(tooltip.y + 18, window.innerHeight - 488)) }}>
          <div className="hover-head"><span>{formatId(tooltip.kind === "goal" ? "G" : tooltip.kind === "ai" ? "A" : "U", tooltip.id)}</span><em className={`status ${tooltip.status}`}>{statusLabels[tooltip.status]}</em></div>
          <h3>{tooltip.title}</h3>
          <dl>{tooltip.fields.map((field) => <div key={field.label}><dt>{field.label}</dt><dd>{displayValue(field.value)}</dd></div>)}</dl>
          <small>{ui.hoverHint}</small>
        </aside>
      )}

      {modal && modalRecord && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.currentTarget === event.target && setModal(null)}>
          <article className="document-modal" role="dialog" aria-modal="true" aria-labelledby="document-title">
            <header>
              <div><span className="document-type">{modal.kind === "goal" ? ui.goalDocument : modal.kind === "ai" ? ui.aiDocument : ui.userDetail}</span><small>{formatId(modal.kind === "goal" ? "G" : modal.kind === "ai" ? "A" : "U", modalRecord.id)}</small></div>
              <button onClick={() => setModal(null)} aria-label={ui.closeDetail}>×</button>
            </header>
            <div className="document-reader scroll-area">
              <div className="markdown-body">
                <h1 id="document-title">{modalRecord.title}</h1>
                <p className="lead">{modalRecord.description}</p>
                <div className="document-meta">
                  <div><span>{ui.currentStatus}</span><strong className={`status ${modalRecord.status}`}>{statusLabels[modalRecord.status]}</strong></div>
                  <div><span>{ui.recordedAt}</span><strong>{modalRecord.recordedAt}</strong></div>
                  <div><span>{ui.updatedAt}</span><strong>{modalRecord.updatedAt}</strong></div>
                  {"goalId" in modalRecord && <div><span>{ui.parentGoal}</span><strong>{formatId("G", modalRecord.goalId)}</strong></div>}
                </div>
                {modal.kind === "user" ? (
                  <>
                    <div className="document-callout"><b>结构化用户任务</b><p>用户任务不建立独立 Markdown。此原型直接根据任务 JSON 展示所需依赖、选择或确认信息。</p></div>
                    <h2>需要用户处理</h2>
                    <p>{modalUser?.description}</p>
                    <h2>任务类型</h2>
                    <p>{modalUser ? kindLabels[modalUser.kind] : "—"}</p>
                    <h2>处理结果</h2>
                    <p>{modalUser?.result ?? "尚未提交处理结果。"}</p>
                  </>
                ) : (
                  <>
                    <h2>背景与目的</h2>
                    <p>{modalRecord.description} 本文档用于沉淀实施所需的完整上下文，列表和看板只读取上方结构化摘要。</p>
                    <h2>{modal.kind === "goal" ? "目标范围" : "实施边界"}</h2>
                    <ul><li>保持结构化状态与文档内容职责分离。</li><li>所有状态修改通过 GoGoal CLI 完成。</li><li>输出需要可验证、可追踪，并与目标结果直接相关。</li></ul>
                    <h2>当前进展</h2>
                    <p>已完成需求收敛和核心方案设计，正在按任务拆分持续推进。具体文档章节将在 Markdown 规范专项讨论中最终确定。</p>
                    {((modalGoal?.blocker) || (modalAi?.blocker)) && <div className="document-callout warning"><b>当前阻塞</b><p>{modalGoal?.blocker ?? modalAi?.blocker}</p></div>}
                    <h2>完成判断</h2>
                    <p>实现结果经过验证并满足用户确认的边界后，任务可以完成；目标还需进入待验收状态并由用户确认。</p>
                  </>
                )}
              </div>
            </div>
          </article>
        </div>
      )}
    </main>
  );
}

function PanelHeading({ icon, title, children }: { icon: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="panel-heading">
      <div><span className="heading-icon" aria-hidden="true">{icon}</span><h1>{title}</h1></div>
      {children}
    </div>
  );
}

function KanbanColumn({ status, count, children }: { status: string; count: number; children: React.ReactNode }) {
  return (
    <section className={`kanban-column column-${status}`}>
      <header><span><i className={status} />{statusLabels[status]}</span><b>{count}</b></header>
      <div className="column-cards scroll-area">{children}</div>
    </section>
  );
}

function TaskCard({ kind, task, selected, onSelect, onOpen, onHoverStart, onHoverMove, onHoverEnd }: {
  kind: "ai" | "user";
  task: AiTask | UserTask;
  selected: boolean;
  onSelect: () => void;
  onOpen: () => void;
  onHoverStart: (event: React.PointerEvent) => void;
  onHoverMove: (event: React.PointerEvent) => void;
  onHoverEnd: () => void;
}) {
  return (
    <div
      className={`work-card task-card ${selected ? "selected" : ""}`}
      tabIndex={0}
      role="button"
      aria-pressed={selected}
      onClick={onSelect}
      onDoubleClick={onOpen}
      onKeyDown={(event) => event.key === "Enter" && onSelect()}
      onPointerEnter={onHoverStart}
      onPointerMove={onHoverMove}
      onPointerLeave={onHoverEnd}
    >
      <div className="card-top"><span>{formatId(kind === "ai" ? "A" : "U", task.id)}</span><em className={`status ${task.status}`}>{statusLabels[task.status]}</em></div>
      <h2>{task.title}</h2>
      <p>{task.description}</p>
    </div>
  );
}

function EmptyState({ icon, title, description, compact = false }: { icon: string; title: string; description: string; compact?: boolean }) {
  return (
    <div className={`empty-state ${compact ? "compact" : ""}`}>
      <span aria-hidden="true">{icon}</span>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}
