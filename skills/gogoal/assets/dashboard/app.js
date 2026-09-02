"use strict";

const I18N = {
  "zh-CN": {
    subtitle: "目标管理技能", connected: "数据已连接", disconnected: "连接失败", invalidData: "数据校验异常",
    unarchived: "未归档", archived: "已归档", searchPlaceholder: "搜索编号、标题、状态或描述",
    dataUpdated: "数据已更新", refresh: "立即刷新", theme: "切换明暗主题", close: "关闭",
    goals: "目标", aiTasks: "AI 任务", userTasks: "用户任务", timeline: "时间线",
    noTasks: "暂无任务", selectTimeline: "选择目标或任务", selectTimelineHint: "单击卡片后，这里会显示相关管理活动。",
    targetDocument: "目标文档", taskDocument: "AI 任务文档", userTaskDetail: "用户任务详情", documentError: "文档读取失败",
    searchEmpty: "没有匹配的数据", unknown: "未知", none: "-", autoRefresh: "自动刷新",
    fields: {
      id: "编号", title: "标题", description: "描述", status: "当前状态", document: "文档路径",
      recordedAt: "登记时间", endedAt: "结束时间", archivedAt: "归档时间", blocker: "当前阻塞",
      reason: "阻塞原因", condition: "解除条件", goalId: "关联目标", kind: "用户任务类型",
      result: "用户结果", entity: "对象类型", entityId: "对象编号", action: "动作",
      time: "发生时间", statusFrom: "原状态", statusTo: "新状态", note: "说明"
    },
    statuses: { pending: "待处理", active: "进行中", blocked: "已阻塞", review: "待验收", completed: "已完成", cancelled: "已取消" },
    kinds: { dependency: "外部依赖", decision: "用户决定", other: "其他事项" },
    actions: { create: "登记", update: "更新", start: "启动", implement: "实现", block: "阻塞", resume: "恢复", submit: "提交验收", revise: "验收修改", complete: "完成", cancel: "取消", archive: "归档" },
    entities: { goal: "目标", ai: "AI 任务", user: "用户任务" }, sources: { log: "管理日志", git: "Git 提交" }, commit: "提交",
    errors: { invalidMermaid: "Mermaid 图表无效", invalidDocumentPath: "文档路径非法", documentNotFound: "文档不存在", internal: "看板读取失败" }
  },
  "en-US": {
    subtitle: "Goal Management Skill", connected: "Data connected", disconnected: "Connection failed", invalidData: "Data validation issue",
    unarchived: "Unarchived", archived: "Archived", searchPlaceholder: "Search ID, title, status, or description",
    dataUpdated: "Data updated", refresh: "Refresh now", theme: "Toggle theme", close: "Close",
    goals: "Goals", aiTasks: "AI Tasks", userTasks: "User Tasks", timeline: "Timeline",
    noTasks: "No tasks", selectTimeline: "Select a goal or task", selectTimelineHint: "Select a card to view related management activity.",
    targetDocument: "Goal document", taskDocument: "AI task document", userTaskDetail: "User task details", documentError: "Unable to load document",
    searchEmpty: "No matching data", unknown: "Unknown", none: "-", autoRefresh: "Auto refresh",
    fields: {
      id: "ID", title: "Title", description: "Description", status: "Status", document: "Document",
      recordedAt: "Recorded at", endedAt: "Ended at", archivedAt: "Archived at", blocker: "Blocker",
      reason: "Reason", condition: "Recovery condition", goalId: "Related goal", kind: "User task kind",
      result: "User result", entity: "Entity", entityId: "Entity ID", action: "Action",
      time: "Time", statusFrom: "Previous status", statusTo: "New status", note: "Note"
    },
    statuses: { pending: "Pending", active: "Active", blocked: "Blocked", review: "Review", completed: "Completed", cancelled: "Cancelled" },
    kinds: { dependency: "Dependency", decision: "Decision", other: "Other" },
    actions: { create: "Created", update: "Updated", start: "Started", implement: "Implemented", block: "Blocked", resume: "Resumed", submit: "Submitted", revise: "Revised", complete: "Completed", cancel: "Cancelled", archive: "Archived" },
    entities: { goal: "Goal", ai: "AI task", user: "User task" }, sources: { log: "Management log", git: "Git commit" }, commit: "Commit",
    errors: { invalidMermaid: "Invalid Mermaid diagram", invalidDocumentPath: "Invalid document path", documentNotFound: "Document not found", internal: "Unable to read dashboard data" }
  }
};

const STATUS_COLORS = { pending: "#6a6a6a", active: "#2678f2", blocked: "#d97706", review: "#7c3aed", completed: "#087f5b", cancelled: "#8b8b8b" };
const AI_ORDER = ["pending", "active", "blocked", "completed", "cancelled"];
const USER_ORDER = ["pending", "completed", "cancelled"];
const app = { data: null, git: { commits: [] }, locale: "zh-CN", scope: "active", search: "", selectedGoal: null, selectedTask: null, tooltipTimer: null };
let mermaidId = 0;
const $ = (selector) => document.querySelector(selector);

function t(key) {
  let value = I18N[app.locale] || I18N["zh-CN"];
  for (const part of key.split(".")) value = value?.[part];
  return value ?? key;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

function applyLanguage() {
  document.documentElement.lang = app.locale;
  document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = t(node.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => { node.placeholder = t(node.dataset.i18nPlaceholder); });
  document.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle); node.setAttribute("aria-label", t(node.dataset.i18nTitle));
  });
}

function statusName(status) { return status ? t(`statuses.${status}`) : t("none"); }
function entityPrefix(entity) { return { goal: "G", ai: "A", user: "U" }[entity]; }
function selectedKey(entity, id) { return `${entity}:${id}`; }
function recordMatches(record, entity) {
  if (!app.search) return true;
  const values = [entityPrefix(entity), record.id, record.title, record.description, record.status, statusName(record.status), record.kind, record.result];
  return values.filter((value) => value !== null && value !== undefined).join(" ").toLocaleLowerCase().includes(app.search);
}

function currentData() {
  if (app.scope === "archive") return { goals: app.data.targetArchive, ai: app.data.aiTaskArchive, user: app.data.userTaskArchive };
  return { goals: app.data.targets, ai: app.data.aiTasks, user: app.data.userTasks };
}

function countsHtml(records, order) {
  return order.map((status) => {
    const count = records.filter((item) => item.status === status).length;
    return `<span class="status-count" title="${escapeHtml(statusName(status))}"><i class="status-dot" style="--status-color:${STATUS_COLORS[status]}"></i>${count}</span>`;
  }).join("");
}

function cardElement(record, entity) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "work-card";
  card.dataset.key = selectedKey(entity, record.id);
  card.style.setProperty("--status-color", STATUS_COLORS[record.status]);
  const selected = entity === "goal"
    ? app.selectedGoal?.id === record.id
    : app.selectedTask?.entity === entity && app.selectedTask?.id === record.id;
  if (selected) card.classList.add("selected");
  card.innerHTML = `
    <div class="card-meta"><span>${entityPrefix(entity)}-${record.id}</span><span class="status-pill">${escapeHtml(statusName(record.status))}</span></div>
    <div class="card-title">${escapeHtml(record.title)}</div>
    <div class="card-description">${escapeHtml(record.description)}</div>`;
  card.addEventListener("click", () => selectRecord(entity, record));
  card.addEventListener("dblclick", () => entity === "user" ? openStructuredDetail(record) : openDocument(entity, record));
  card.addEventListener("mouseenter", (event) => scheduleTooltip(event.currentTarget, record, entity));
  card.addEventListener("mouseleave", hideTooltip);
  card.addEventListener("focus", (event) => scheduleTooltip(event.currentTarget, record, entity));
  card.addEventListener("blur", hideTooltip);
  return card;
}

function renderGoals(goals) {
  const container = $("#goal-list");
  const records = [...goals].sort((a, b) => b.id - a.id).filter((item) => recordMatches(item, "goal"));
  container.replaceChildren(...records.map((item) => cardElement(item, "goal")));
  if (!records.length) container.innerHTML = `<div class="empty-state"><div><b>＋</b>${escapeHtml(t(app.search ? "searchEmpty" : "noTasks"))}</div></div>`;
  $("#goal-counts").innerHTML = countsHtml(goals, ["pending", "active", "blocked", "review", "completed", "cancelled"]);
}

function renderKanban(target, records, entity, order) {
  const board = $(target);
  board.replaceChildren();
  for (const status of order) {
    const column = document.createElement("section");
    column.className = `kanban-column column-${status}`;
    const filtered = [...records].sort((a, b) => b.id - a.id).filter((item) => item.status === status && recordMatches(item, entity));
    column.innerHTML = `<header class="column-header"><span><i class="status-dot" style="--status-color:${STATUS_COLORS[status]}"></i>${escapeHtml(statusName(status))}</span><span class="count-badge">${filtered.length}</span></header>`;
    const cards = document.createElement("div");
    cards.className = "column-cards scroll-area";
    if (filtered.length) filtered.forEach((item) => cards.append(cardElement(item, entity)));
    else cards.innerHTML = `<div class="empty-state"><div><b>＋</b>${escapeHtml(t(app.search ? "searchEmpty" : "noTasks"))}</div></div>`;
    column.append(cards); board.append(column);
  }
}

function selectRecord(entity, record) {
  if (entity === "goal") {
    const wasSelected = app.selectedGoal?.id === record.id;
    app.selectedGoal = wasSelected ? null : { id: record.id };
    app.selectedTask = null;
  } else {
    const wasSelected = app.selectedTask?.entity === entity && app.selectedTask?.id === record.id;
    app.selectedTask = wasSelected ? null : { entity, id: record.id, goalId: record.goalId };
  }
  render();
}

function renderTimeline() {
  const container = $("#timeline");
  const selection = app.selectedTask || (app.selectedGoal ? { entity: "goal", id: app.selectedGoal.id } : null);
  if (!selection) {
    $("#timeline-count").textContent = "";
    container.innerHTML = `<div class="timeline-empty"><div><span>◷</span><strong>${escapeHtml(t("selectTimeline"))}</strong><br>${escapeHtml(t("selectTimelineHint"))}</div></div>`;
    return;
  }
  let logs = app.data.logs.filter((entry) => selection.entity === "goal"
    ? entry.goalId === selection.id
    : entry.entity === selection.entity && entry.entityId === selection.id);
  const taskGoal = (entity, id) => {
    if (entity === "goal") return id;
    const pool = entity === "ai" ? [...app.data.aiTasks, ...app.data.aiTaskArchive] : [...app.data.userTasks, ...app.data.userTaskArchive];
    return pool.find((item) => item.id === id)?.goalId;
  };
  const commits = (app.git.commits || []).filter((entry) => selection.entity === "goal"
    ? taskGoal(entry.entity, entry.entityId) === selection.id
    : entry.entity === selection.entity && entry.entityId === selection.id);
  // 管理日志必须按稳定编号排序，不能依赖可能随设备变化的时间字符串。
  // Git 活动只是补充信息，保持 `git log` 返回顺序并列在管理日志之后。
  logs = logs.sort((a, b) => b.id - a.id);
  const timeline = [
    ...logs.map((entry) => ({ ...entry, source: "log" })),
    ...commits.map((entry) => ({ ...entry, source: "git" }))
  ];
  $("#timeline-count").textContent = timeline.length;
  container.replaceChildren();
  for (const entry of timeline) {
    const node = document.createElement("article");
    node.className = "timeline-item";
    node.style.setProperty("--status-color", STATUS_COLORS[entry.statusTo] || "#ff385c");
    const displayTime = entry.source === "git" ? new Date(entry.time).toLocaleString(app.locale, { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }) : entry.time.slice(5);
    const detail = entry.source === "git" ? `${t("commit")} ${entry.shortSha}` : (entry.note || `${statusName(entry.statusFrom)} → ${statusName(entry.statusTo)}`);
    node.innerHTML = `<span class="timeline-icon">${entry.source === "git" ? "◆" : entityPrefix(entry.entity)}</span>
      <div class="timeline-top"><strong>${escapeHtml(t(`actions.${entry.action}`))}</strong><span class="timeline-time">${escapeHtml(displayTime)}</span></div>
      <div class="timeline-title">${entityPrefix(entry.entity)}-${entry.entityId} · ${escapeHtml(entry.title)}</div>
      <div class="timeline-note">${escapeHtml(detail)} · ${escapeHtml(t(`sources.${entry.source}`))}</div>`;
    container.append(node);
  }
}

function render() {
  if (!app.data) return;
  const data = currentData();
  const selectedGoalId = app.selectedGoal?.id;
  const ai = selectedGoalId ? data.ai.filter((item) => item.goalId === selectedGoalId) : data.ai;
  const user = selectedGoalId ? data.user.filter((item) => item.goalId === selectedGoalId) : data.user;
  renderGoals(data.goals);
  renderKanban("#ai-board", ai, "ai", AI_ORDER);
  renderKanban("#user-board", user, "user", USER_ORDER);
  $("#ai-counts").innerHTML = countsHtml(ai, AI_ORDER);
  $("#user-counts").innerHTML = countsHtml(user, USER_ORDER);
  renderTimeline();
}

function displayValue(key, value) {
  if (value === null || value === undefined || value === "") return t("none");
  if (key === "status" || key === "statusFrom" || key === "statusTo") return statusName(value);
  if (key === "kind") return t(`kinds.${value}`);
  if (key === "entity") return t(`entities.${value}`);
  if (key === "action") return t(`actions.${value}`);
  if (key === "goalId") return `G-${value}`;
  if (typeof value === "object") {
    return Object.entries(value).map(([childKey, childValue]) => `${t(`fields.${childKey}`)}: ${displayValue(childKey, childValue)}`).join("\n");
  }
  return String(value);
}

function scheduleTooltip(anchor, record, entity) {
  clearTimeout(app.tooltipTimer);
  app.tooltipTimer = setTimeout(() => showTooltip(anchor, record, entity), 1000);
}

function showTooltip(anchor, record, entity) {
  const tooltip = $("#tooltip");
  const entries = Object.entries(record);
  tooltip.innerHTML = `<dl>${entries.map(([key, value]) => `<dt>${escapeHtml(t(`fields.${key}`))}</dt><dd class="${typeof value === "object" ? "object-value" : ""}">${escapeHtml(displayValue(key, value))}</dd>`).join("")}</dl>`;
  tooltip.hidden = false;
  const rect = anchor.getBoundingClientRect();
  const tip = tooltip.getBoundingClientRect();
  const gap = 8;
  let left = rect.right + gap;
  if (left + tip.width > window.innerWidth - gap) left = rect.left - tip.width - gap;
  left = Math.max(gap, Math.min(left, window.innerWidth - tip.width - gap));
  let top = rect.top;
  if (top + tip.height > window.innerHeight - gap) top = window.innerHeight - tip.height - gap;
  tooltip.style.left = `${left}px`; tooltip.style.top = `${Math.max(gap, top)}px`;
}

function hideTooltip() {
  clearTimeout(app.tooltipTimer); $("#tooltip").hidden = true;
}

function inlineMarkdown(text) {
  let safe = escapeHtml(text);
  safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
  safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  safe = safe.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  safe = safe.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label, href) => {
    const decoded = href.replace(/&amp;/g, "&");
    const allowed = /^(https?:\/\/|\.\.?\/|#)/.test(decoded);
    return allowed ? `<a href="${escapeHtml(decoded)}" target="_blank" rel="noopener noreferrer">${label}</a>` : label;
  });
  return safe;
}

function isTableDivider(line) { return /^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(line); }
function tableCells(line) { return line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim()); }

function markdownToHtml(markdown) {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const output = []; let index = 0; let listType = null;
  const closeList = () => { if (listType) { output.push(`</${listType}>`); listType = null; } };
  while (index < lines.length) {
    const line = lines[index];
    if (line.startsWith("```")) {
      closeList(); const language = line.slice(3).trim().toLowerCase(); const code = []; index += 1;
      while (index < lines.length && !lines[index].startsWith("```")) { code.push(lines[index]); index += 1; }
      const cls = language === "mermaid" ? "mermaid-source" : "";
      output.push(`<pre class="${cls}"><code>${escapeHtml(code.join("\n"))}</code></pre>`); index += 1; continue;
    }
    if (index + 1 < lines.length && line.includes("|") && isTableDivider(lines[index + 1])) {
      closeList(); const head = tableCells(line); index += 2; const rows = [];
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) { rows.push(tableCells(lines[index])); index += 1; }
      output.push(`<table><thead><tr>${head.map((cell) => `<th>${inlineMarkdown(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${head.map((_, cellIndex) => `<td>${inlineMarkdown(row[cellIndex] || "")}</td>`).join("")}</tr>`).join("")}</tbody></table>`); continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) { closeList(); const level = heading[1].length; output.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`); index += 1; continue; }
    const item = line.match(/^\s*([-*+]|\d+\.)\s+(.+)$/);
    if (item) {
      const nextType = /\d+\./.test(item[1]) ? "ol" : "ul";
      if (listType !== nextType) { closeList(); output.push(`<${nextType}>`); listType = nextType; }
      output.push(`<li>${inlineMarkdown(item[2])}</li>`); index += 1; continue;
    }
    closeList();
    if (line.startsWith("> ")) output.push(`<blockquote>${inlineMarkdown(line.slice(2))}</blockquote>`);
    else if (line.trim()) output.push(`<p>${inlineMarkdown(line)}</p>`);
    index += 1;
  }
  closeList(); return output.join("\n");
}

function renderMermaid(source) {
  const wrapper = document.createElement("div"); wrapper.className = "mermaid-view";
  const lines = source.split("\n").map((line) => line.trim()).filter(Boolean);
  const first = lines.shift() || "";
  if (!/^(graph|flowchart)\s+(TD|TB|LR|RL)$/i.test(first)) {
    const pre = document.createElement("pre"); pre.textContent = source; wrapper.append(pre); return wrapper;
  }
  const nodes = new Map(); const edges = [];
  for (const line of lines) {
    const match = line.match(/^([\w-]+)(?:\[([^\]]+)\]|\(([^)]+)\))?\s*--?>\s*([\w-]+)(?:\[([^\]]+)\]|\(([^)]+)\))?$/);
    if (!match) continue;
    nodes.set(match[1], match[2] || match[3] || match[1]); nodes.set(match[4], match[5] || match[6] || match[4]); edges.push([match[1], match[4]]);
  }
  if (!nodes.size) { const pre = document.createElement("pre"); pre.textContent = source; wrapper.append(pre); return wrapper; }
  const horizontal = /\s(LR|RL)$/i.test(first); const width = horizontal ? Math.max(520, nodes.size * 170) : 540; const height = horizontal ? 180 : Math.max(220, nodes.size * 100);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("viewBox", `0 0 ${width} ${height}`); svg.setAttribute("role", "img");
  const defs = document.createElementNS(svg.namespaceURI, "defs"); const marker = document.createElementNS(svg.namespaceURI, "marker"); marker.setAttribute("id", "arrow"); marker.setAttribute("viewBox", "0 0 10 10"); marker.setAttribute("refX", "9"); marker.setAttribute("refY", "5"); marker.setAttribute("markerWidth", "6"); marker.setAttribute("markerHeight", "6"); marker.setAttribute("orient", "auto-start-reverse"); const arrow = document.createElementNS(svg.namespaceURI, "path"); arrow.setAttribute("d", "M 0 0 L 10 5 L 0 10 z"); arrow.setAttribute("fill", "#ff385c"); marker.append(arrow); defs.append(marker); svg.append(defs);
  const positions = new Map(); [...nodes.keys()].forEach((id, i) => positions.set(id, horizontal ? [90 + i * 165, 90] : [270, 55 + i * 95]));
  for (const [from, to] of edges) { const [x1, y1] = positions.get(from); const [x2, y2] = positions.get(to); const path = document.createElementNS(svg.namespaceURI, "line"); path.setAttribute("x1", x1); path.setAttribute("y1", y1); path.setAttribute("x2", x2); path.setAttribute("y2", y2); path.setAttribute("stroke", "#ff385c"); path.setAttribute("stroke-width", "2"); path.setAttribute("marker-end", "url(#arrow)"); svg.append(path); }
  for (const [id, label] of nodes) { const [x, y] = positions.get(id); const group = document.createElementNS(svg.namespaceURI, "g"); const rect = document.createElementNS(svg.namespaceURI, "rect"); rect.setAttribute("x", x - 65); rect.setAttribute("y", y - 23); rect.setAttribute("width", "130"); rect.setAttribute("height", "46"); rect.setAttribute("rx", "11"); rect.setAttribute("fill", "var(--surface)"); rect.setAttribute("stroke", "#ff385c"); const text = document.createElementNS(svg.namespaceURI, "text"); text.setAttribute("x", x); text.setAttribute("y", y + 5); text.setAttribute("text-anchor", "middle"); text.setAttribute("fill", "currentColor"); text.setAttribute("font-size", "13"); text.textContent = label.slice(0, 18); group.append(rect, text); svg.append(group); }
  wrapper.append(svg); return wrapper;
}

function sanitizeMermaidSvg(svgText) {
  const documentNode = new DOMParser().parseFromString(svgText, "image/svg+xml");
  if (documentNode.querySelector("parsererror")) throw new Error("invalidMermaid");
  documentNode.querySelectorAll("script,foreignObject,iframe,object,embed,image").forEach((node) => node.remove());
  documentNode.querySelectorAll("a").forEach((node) => node.replaceWith(...node.childNodes));
  documentNode.querySelectorAll("*").forEach((node) => {
    for (const attribute of [...node.attributes]) {
      const name = attribute.name.toLowerCase(); const value = attribute.value.trim();
      if (name.startsWith("on") || ((name === "href" || name === "xlink:href") && !value.startsWith("#"))) node.removeAttribute(attribute.name);
      if (name === "style" && (/url\((?!["']?#)/i.test(value) || /@import|expression\s*\(/i.test(value))) node.removeAttribute(attribute.name);
    }
  });
  documentNode.querySelectorAll("style").forEach((node) => {
    if (/@import|url\((?!["']?#)/i.test(node.textContent || "")) node.remove();
  });
  return document.importNode(documentNode.documentElement, true);
}

async function renderFullMermaid(source) {
  if (!globalThis.mermaid) return renderMermaid(source);
  const wrapper = document.createElement("div"); wrapper.className = "mermaid-view";
  try {
    globalThis.mermaid.initialize({
      startOnLoad: false, securityLevel: "strict", secure: ["securityLevel", "startOnLoad", "maxTextSize"],
      maxTextSize: 50000, suppressErrorRendering: true,
      theme: document.documentElement.dataset.theme === "dark" ? "dark" : "default",
      flowchart: { htmlLabels: false }, sequence: { useMaxWidth: true }
    });
    const rendered = await globalThis.mermaid.render(`gogoal-mermaid-${++mermaidId}`, source);
    wrapper.append(sanitizeMermaidSvg(rendered.svg));
    return wrapper;
  } catch (_error) {
    const fallback = renderMermaid(source);
    fallback.prepend(Object.assign(document.createElement("small"), { textContent: t("documentError") + " · Mermaid" }));
    return fallback;
  }
}

async function openDocument(entity, record) {
  if (!record.document) return;
  hideTooltip();
  try {
    const response = await fetch(`/api/document?path=${encodeURIComponent(record.document)}`, { cache: "no-store" });
    if (!response.ok) throw new Error(await responseError(response));
    const payload = await response.json();
    $("#document-type").textContent = t(entity === "goal" ? "targetDocument" : "taskDocument");
    $("#document-id").textContent = `${entityPrefix(entity)}-${record.id}`;
    const reader = $("#document-reader"); reader.innerHTML = markdownToHtml(payload.content);
    for (const node of [...reader.querySelectorAll(".mermaid-source")]) {
      node.replaceWith(await renderFullMermaid(node.textContent));
    }
    reader.querySelectorAll("a").forEach((link) => {
      const href = link.getAttribute("href") || "";
      if (/^https?:\/\//.test(href) || href.startsWith("#")) return;
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const normalized = new URL(href, `http://gogoal.local/${record.document}`).pathname.slice(1);
        const pools = [
          ["goal", ...app.data.targets, ...app.data.targetArchive],
          ["ai", ...app.data.aiTasks, ...app.data.aiTaskArchive]
        ];
        for (const [targetEntity, ...records] of pools) {
          const target = records.find((item) => item.document === normalized);
          if (target) { openDocument(targetEntity, target); return; }
        }
      });
    });
    $("#modal").hidden = false; reader.scrollTop = 0;
  } catch (error) { toast(`${t("documentError")}: ${t(`errors.${error.message}`)}`); }
}

function openStructuredDetail(record) {
  hideTooltip();
  $("#document-type").textContent = t("userTaskDetail");
  $("#document-id").textContent = `U-${record.id}`;
  const reader = $("#document-reader");
  reader.innerHTML = `<section class="structured-detail"><h1>${escapeHtml(record.title)}</h1><dl>${Object.entries(record).map(([key, value]) =>
    `<dt>${escapeHtml(t(`fields.${key}`))}</dt><dd>${escapeHtml(displayValue(key, value))}</dd>`).join("")}</dl></section>`;
  $("#modal").hidden = false;
  reader.scrollTop = 0;
}

async function responseError(response) {
  try {
    const payload = await response.json();
    return payload.error || "internal";
  } catch (_error) {
    return "internal";
  }
}

function closeModal() { $("#modal").hidden = true; }
function toast(message) { const node = $("#toast"); node.textContent = message; node.hidden = false; setTimeout(() => { node.hidden = true; }, 3500); }

async function refresh() {
  try {
    const [response, gitResponse] = await Promise.all([
      fetch("/api/snapshot", { cache: "no-store" }), fetch("/api/git", { cache: "no-store" })
    ]);
    if (!response.ok) throw new Error(await responseError(response));
    app.data = await response.json(); app.git = gitResponse.ok ? await gitResponse.json() : { commits: [] };
    app.locale = I18N[app.data.config.locale] ? app.data.config.locale : "zh-CN";
    applyLanguage();
    const valid = app.data.validation?.valid !== false;
    $("#connection").textContent = `● ${t(valid ? "connected" : "invalidData")}`;
    $("#connection").classList.toggle("error", !valid);
    $("#project-name").textContent = app.data.config.project;
    $("#updated-at").textContent = `${app.data.updatedAt.slice(11)} · ${t("autoRefresh")} ${app.data.config.dashboard.refreshSeconds}s`;
    document.title = `GoGoal · ${app.data.config.project}`;
    const goals = [...app.data.targets, ...app.data.targetArchive];
    if (app.selectedGoal && !goals.some((item) => item.id === app.selectedGoal.id)) {
      app.selectedGoal = null; app.selectedTask = null;
    }
    if (app.selectedTask) {
      const tasks = app.selectedTask.entity === "ai"
        ? [...app.data.aiTasks, ...app.data.aiTaskArchive]
        : [...app.data.userTasks, ...app.data.userTaskArchive];
      if (!tasks.some((item) => item.id === app.selectedTask.id)) app.selectedTask = null;
    }
    render(); scheduleRefresh();
  } catch (error) {
    $("#connection").textContent = `● ${t("disconnected")}`; $("#connection").classList.add("error"); toast(t(`errors.${error.message}`)); scheduleRefresh(30);
  }
}

let refreshTimer;
function scheduleRefresh(seconds) { clearTimeout(refreshTimer); const delay = (seconds || app.data?.config?.dashboard?.refreshSeconds || 180) * 1000; refreshTimer = setTimeout(refresh, delay); }
function updateClock() { $("#clock").textContent = new Date().toLocaleTimeString(app.locale, { hour12: false }); }

function bindEvents() {
  $("#scope-active").addEventListener("click", () => { app.scope = "active"; app.selectedGoal = null; app.selectedTask = null; $("#scope-active").classList.add("active"); $("#scope-archive").classList.remove("active"); render(); });
  $("#scope-archive").addEventListener("click", () => { app.scope = "archive"; app.selectedGoal = null; app.selectedTask = null; $("#scope-archive").classList.add("active"); $("#scope-active").classList.remove("active"); render(); });
  $("#search").addEventListener("input", (event) => {
    app.search = event.target.value.trim().toLocaleLowerCase();
    if (app.search) { app.selectedGoal = null; app.selectedTask = null; }
    render();
  });
  $("#refresh").addEventListener("click", refresh);
  $("#theme").addEventListener("click", () => { const root = document.documentElement; const next = root.dataset.theme === "dark" ? "light" : "dark"; root.dataset.theme = next; localStorage.setItem("gogoal-theme", next); });
  $("#modal-close").addEventListener("click", closeModal);
  $("#modal").addEventListener("click", (event) => { if (event.target === event.currentTarget) closeModal(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") { hideTooltip(); closeModal(); } });
  window.addEventListener("resize", hideTooltip);
}

document.documentElement.dataset.theme = localStorage.getItem("gogoal-theme") || "light";
bindEvents(); applyLanguage(); updateClock(); setInterval(updateClock, 1000); refresh();
