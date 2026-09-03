import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("服务端能够渲染 GoGoal 看板首屏", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>GoGoal · 目标任务看板<\/title>/i);
  assert.match(html, /GoGoal/);
  assert.match(html, /AI 任务/);
  assert.match(html, /用户任务/);
  assert.match(html, /时间线/);
  assert.match(html, /建立目标任务可视化看板/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/);
});

test("原型包含约定的核心交互并移除启动模板", async () => {
  const [page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(page, /setSelectedGoal/);
  assert.match(page, /setSelectedTask/);
  assert.match(page, /onDoubleClick/);
  assert.match(page, /setTimeout\(\(\) => setTooltip/);
  assert.match(page, /data-theme=\{theme\}/);
  assert.match(page, /selectedGoal === null \|\| task\.goalId === selectedGoal/);
  assert.match(layout, /lang="zh-CN"/);
  assert.match(packageJson, /"name": "gogoal-dashboard-prototype"/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);

  await assert.rejects(access(new URL("../app/_sites-preview/SkeletonPreview.tsx", import.meta.url)));
  await assert.rejects(access(new URL("../app/_sites-preview/preview.css", import.meta.url)));
});
