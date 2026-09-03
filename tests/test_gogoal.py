from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPOSITORY / "skills" / "gogoal"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from gogoal.dashboard import COMMIT_RE, DashboardHandler
from gogoal.errors import GoGoalError
from gogoal.platform import git_capability
from gogoal.service import COMMIT_LABELS, GoGoalService, _suggested_commit
from gogoal import storage


def goal_document(identity: int, title: str) -> str:
    return f"""# G-{identity} {title}

## 1. 目标定义

测试目标。

## 2. 实施方案

按自动化测试执行。

## 3. 任务规划与执行

通过任务验证完整流转。

## 4. 交付与验收

自动化验证通过。

## 5. 评审记录

| 时间 | 评审类型 | 评审内容 |
| --- | --- | --- |
"""


def task_document(identity: int, title: str, goal_id: int) -> str:
    return f"""# A-{identity} {title}

> 关联目标：[G-{goal_id}](../targets/{goal_id}.md)

## 1. 任务定义

验证任务。

## 2. 实施计划

执行自动化检查。

## 3. 实施记录

已执行。

## 4. 验证结果

通过。

## 5. 交付结果

测试结果。

## 6. 阻塞、恢复与取消记录

无。
"""


class ServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        GoGoalService.initialize(SKILL_ROOT, self.root, "测试项目", "zh-CN")
        self.service = GoGoalService.locate(SKILL_ROOT, self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_goal(self, identity: int, title: str) -> None:
        (self.root / "gogoal" / "targets" / f"{identity}.md").write_text(goal_document(identity, title), encoding="utf-8")

    def write_task(self, identity: int, title: str, goal_id: int) -> None:
        (self.root / "gogoal" / "tasks" / f"{identity}.md").write_text(task_document(identity, title, goal_id), encoding="utf-8")

    def test_default_config_and_guides(self) -> None:
        config = self.service.config_list()
        self.assertEqual(config["execution"]["maxParallelTasks"], 2)
        self.assertEqual(config["git"]["branchPrefix"], "gogoal/")
        self.assertEqual(config["dashboard"]["refreshSeconds"], 180)
        self.assertTrue((self.root / "gogoal" / "goal-writing.md").is_file())
        self.assertTrue((self.root / "gogoal" / "task-writing.md").is_file())
        with self.assertRaises(GoGoalError):
            GoGoalService.initialize(SKILL_ROOT, self.root, "覆盖", "en-US")
        with self.assertRaises(GoGoalError):
            self.service.goal_create("敏感内容", "api_token=do-not-store")
        with self.assertRaises(GoGoalError):
            self.service.goal_create("跨行\n标题", "标题必须保持单行")
        with self.assertRaises(GoGoalError):
            self.service.goal_create("控制字符", "描述包含\x00控制字符")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(GoGoalError):
                GoGoalService.initialize(SKILL_ROOT, Path(directory), "api_key=do-not-store", "zh-CN")

    def test_all_suggested_management_commits_match_dashboard_format(self) -> None:
        prefixes = {"goal": "G", "ai": "A", "user": "U"}
        for entity, actions in COMMIT_LABELS.items():
            record = {"id": 7, "title": "示例标题"}
            for action in actions:
                subject = _suggested_commit(entity, action, record)
                match = COMMIT_RE.fullmatch(subject)
                self.assertIsNotNone(match, subject)
                self.assertEqual(match.group(3), prefixes[entity])

    def test_full_lifecycle_archive_and_logs(self) -> None:
        goal = self.service.goal_create("发布技能", "完成实现和验收")["record"]
        self.write_goal(goal["id"], goal["title"])
        self.assertTrue(self.service.validate()["valid"])
        self.service.goal_start(goal["id"])

        ai_one = self.service.task_create("ai", goal["id"], "实现 CLI", "实现稳定命令")["record"]
        self.write_task(ai_one["id"], ai_one["title"], goal["id"])
        ai_two = self.service.task_create("ai", goal["id"], "实现看板", "实现只读页面")["record"]
        self.write_task(ai_two["id"], ai_two["title"], goal["id"])
        user = self.service.task_create("user", goal["id"], "确认发布", "确认发布边界", "decision")["record"]

        self.service.task_start(ai_one["id"])
        with self.assertRaises(GoGoalError):
            self.service.task_start(ai_two["id"])
        self.service.task_block(ai_one["id"], "等待内部验证", "验证工具可用")
        self.service.task_start(ai_two["id"])
        self.service.task_resume(ai_one["id"])
        self.assertEqual(self.service.capacity()["activeTasks"], 2)
        self.assertEqual(self.service.capacity()["effectiveLimit"], 1)

        self.service.task_complete_ai(ai_one["id"])
        self.service.task_complete_ai(ai_two["id"])
        self.service.task_finish_user(user["id"], "complete", "同意本地只读发布范围")
        self.service.goal_submit(goal["id"])
        self.service.goal_complete(goal["id"])
        self.service.goal_archive(goal["id"])

        self.assertEqual(self.service.goal_records("active"), [])
        self.assertEqual(len(self.service.goal_records("archive")), 1)
        archived_tasks = self.service.task_records("archive")
        self.assertEqual(len(archived_tasks["aiTasks"]), 2)
        self.assertEqual(len(archived_tasks["userTasks"]), 1)
        result = self.service.validate(strict=True)
        self.assertTrue(result["valid"], result["errors"])
        log_ids = [item["id"] for item in self.service.log_list()]
        self.assertEqual(log_ids, list(range(1, len(log_ids) + 1)))

    def test_cancel_goal_cascades_non_terminal_tasks(self) -> None:
        goal = self.service.goal_create("取消测试", "验证级联取消")["record"]
        self.write_goal(goal["id"], goal["title"])
        self.service.goal_start(goal["id"])
        ai = self.service.task_create("ai", goal["id"], "候选实现", "等待取消")["record"]
        self.write_task(ai["id"], ai["title"], goal["id"])
        user = self.service.task_create("user", goal["id"], "外部输入", "等待输入", "dependency")["record"]
        self.service.task_start(ai["id"])
        self.service.goal_cancel(goal["id"], "用户终止目标")
        self.assertEqual(self.service.task_show(ai["id"], "ai")["status"], "cancelled")
        user_result = self.service.task_show(user["id"], "user")
        self.assertEqual(user_result["status"], "cancelled")
        self.assertEqual(user_result["result"], "用户终止目标")
        self.assertTrue(self.service.validate()["valid"])

    def test_config_validation_and_normalization(self) -> None:
        self.service.config_set("git.branchPrefix", "feature")
        self.assertEqual(self.service.config_get("git.branchPrefix"), "feature/")
        self.service.config_set("execution.maxParallelTasks", 4)
        self.assertEqual(self.service.capacity()["configuredLimit"], 4)
        with self.assertRaises(GoGoalError):
            self.service.config_set("execution.maxParallelTasks", 0)
        with self.assertRaises(GoGoalError):
            self.service.config_set("git.worktreeRoot", "inside-worktrees")
        with self.assertRaises(GoGoalError):
            self.service.config_set("git.branchPrefix", "bad prefix")
        with self.assertRaises(GoGoalError):
            self.service.config_set("format", 2)

    def test_disabling_git_skips_environment_probe(self) -> None:
        self.service.config_set("git.enabled", False)
        with patch("gogoal.platform.shutil.which") as which:
            capability = git_capability(self.root, enabled=False)
        which.assert_not_called()
        self.assertFalse(capability["available"])
        self.assertIsNone(capability["executable"])
        with patch("gogoal.service.git_capability", wraps=git_capability) as probe:
            capacity = self.service.capacity()
        probe.assert_called_once_with(self.service.paths.root, False)
        self.assertEqual(capacity["effectiveLimit"], 1)
        self.assertFalse(capacity["gitIntegration"])

    def test_validation_detects_document_title_and_log_tampering(self) -> None:
        goal = self.service.goal_create("校验目标", "验证错误检测")["record"]
        self.write_goal(goal["id"], "错误标题")
        result = self.service.validate()
        self.assertFalse(result["valid"])
        self.assertTrue(any("一级标题" in item for item in result["errors"]))
        self.write_goal(goal["id"], goal["title"])
        log_path = self.root / "gogoal" / "log.json"
        log_data = json.loads(log_path.read_text(encoding="utf-8"))
        log_data["logs"][0]["statusTo"] = "active"
        log_path.write_text(json.dumps(log_data, ensure_ascii=False), encoding="utf-8")
        result = self.service.validate()
        self.assertFalse(result["valid"])
        self.assertTrue(any("日志末状态" in item for item in result["errors"]))

    def test_validation_detects_sensitive_or_multiline_blocker(self) -> None:
        goal = self.service.goal_create("阻塞校验", "验证阻塞摘要安全")['record']
        self.write_goal(goal["id"], goal["title"])
        self.service.goal_start(goal["id"])
        self.service.goal_block(goal["id"], "等待资源", "资源恢复")
        target_path = self.root / "gogoal" / "target.json"
        target = json.loads(target_path.read_text(encoding="utf-8"))
        target["targets"][0]["blocker"]["reason"] = "api_token=do-not-store"
        target["targets"][0]["blocker"]["condition"] = "第一行\n第二行"
        target_path.write_text(json.dumps(target, ensure_ascii=False), encoding="utf-8")
        result = self.service.validate()
        self.assertFalse(result["valid"])
        self.assertTrue(any("blocker.reason 疑似包含敏感凭据" in item for item in result["errors"]))
        self.assertTrue(any("blocker.condition 必须是无控制字符的单行文本" in item for item in result["errors"]))

    def test_validation_requires_create_as_first_object_log(self) -> None:
        goal = self.service.goal_create("日志起点", "验证创建日志不可缺失")["record"]
        self.write_goal(goal["id"], goal["title"])
        self.service.goal_start(goal["id"])
        log_path = self.root / "gogoal" / "log.json"
        payload = json.loads(log_path.read_text(encoding="utf-8"))
        payload["logs"] = payload["logs"][1:]
        payload["logs"][0]["id"] = 1
        log_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        result = self.service.validate()
        self.assertFalse(result["valid"])
        self.assertTrue(any("首条日志" in item and "create" in item for item in result["errors"]))

    def test_validation_rejects_unknown_fields_invalid_times_and_action_mismatch(self) -> None:
        goal = self.service.goal_create("严格结构", "拒绝结构漂移")["record"]
        self.write_goal(goal["id"], goal["title"])
        target_path = self.root / "gogoal" / "target.json"
        target = json.loads(target_path.read_text(encoding="utf-8"))
        target["unexpectedRoot"] = []
        target["targets"][0]["unexpected"] = True
        target["targets"][0]["recordedAt"] = "2026-13-40 28:99"
        target_path.write_text(json.dumps(target, ensure_ascii=False), encoding="utf-8")
        result = self.service.validate()
        self.assertFalse(result["valid"])
        self.assertTrue(any("target.json 包含未知字段" in item for item in result["errors"]))

        del target["unexpectedRoot"]
        target_path.write_text(json.dumps(target, ensure_ascii=False), encoding="utf-8")
        log_path = self.root / "gogoal" / "log.json"
        logs = json.loads(log_path.read_text(encoding="utf-8"))
        logs["logs"][0]["action"] = "update"
        log_path.write_text(json.dumps(logs, ensure_ascii=False), encoding="utf-8")
        result = self.service.validate()
        self.assertFalse(result["valid"])
        self.assertTrue(any("未知字段" in item for item in result["errors"]))
        self.assertTrue(any("recordedAt" in item for item in result["errors"]))
        self.assertTrue(any("动作与状态迁移不匹配" in item for item in result["errors"]))

    def test_illegal_state_transitions_are_rejected(self) -> None:
        goal = self.service.goal_create("非法流转", "验证状态矩阵")["record"]
        self.write_goal(goal["id"], goal["title"])
        with self.assertRaises(GoGoalError): self.service.goal_complete(goal["id"])
        with self.assertRaises(GoGoalError): self.service.goal_block(goal["id"], "原因", "条件")
        with self.assertRaises(GoGoalError): self.service.goal_archive(goal["id"])
        with self.assertRaises(GoGoalError): self.service.task_create("ai", goal["id"], "过早任务", "目标未启动")

        self.service.goal_start(goal["id"])
        with self.assertRaises(GoGoalError): self.service.goal_start(goal["id"])
        ai = self.service.task_create("ai", goal["id"], "AI 任务", "验证 AI 状态")["record"]
        self.write_task(ai["id"], ai["title"], goal["id"])
        user = self.service.task_create("user", goal["id"], "用户任务", "验证用户状态", "other")["record"]
        with self.assertRaises(GoGoalError): self.service.task_complete_ai(ai["id"])
        with self.assertRaises(GoGoalError): self.service.task_block(ai["id"], "原因", "条件")
        with self.assertRaises(GoGoalError): self.service.task_resume(ai["id"])
        with self.assertRaises(GoGoalError): self.service.task_archive(ai["id"], "ai")
        with self.assertRaises(GoGoalError): self.service.goal_submit(goal["id"])

        self.service.task_start(ai["id"])
        with self.assertRaises(GoGoalError): self.service.goal_block(goal["id"], "原因", "条件")
        self.service.task_complete_ai(ai["id"])
        with self.assertRaises(GoGoalError): self.service.task_update(ai["id"], "ai", "终态改名", None)
        self.service.task_finish_user(user["id"], "complete", "已处理")
        with self.assertRaises(GoGoalError): self.service.task_finish_user(user["id"], "complete", "重复")
        self.service.goal_submit(goal["id"])
        with self.assertRaises(GoGoalError): self.service.goal_submit(goal["id"])
        self.service.goal_complete(goal["id"])
        with self.assertRaises(GoGoalError): self.service.goal_update(goal["id"], "终态改名", None)
        with self.assertRaises(GoGoalError): self.service.goal_cancel(goal["id"], "重复终结")
        self.assertTrue(self.service.validate()["valid"])

    def test_lifecycle_stops_until_markdown_consistency_is_restored(self) -> None:
        goal = self.service.goal_create("文档门槛", "文档缺失时禁止继续")["record"]
        with self.assertRaises(GoGoalError):
            self.service.goal_start(goal["id"])
        self.write_goal(goal["id"], goal["title"])
        self.service.goal_update(goal["id"], "更新后的标题", None)
        with self.assertRaises(GoGoalError):
            self.service.goal_start(goal["id"])
        self.write_goal(goal["id"], "更新后的标题")
        self.service.goal_start(goal["id"])
        ai = self.service.task_create("ai", goal["id"], "待补任务文档", "任务文档门槛")["record"]
        with self.assertRaises(GoGoalError):
            self.service.task_start(ai["id"])
        self.write_task(ai["id"], ai["title"], goal["id"])
        self.service.task_start(ai["id"])

    def test_goal_block_resume_revise_and_task_archives(self) -> None:
        goal = self.service.goal_create("恢复与修改", "覆盖剩余合法状态")["record"]
        self.write_goal(goal["id"], goal["title"])
        self.service.goal_start(goal["id"])
        self.service.goal_block(goal["id"], "外部服务不可用", "服务恢复")
        blocked = self.service.goal_show(goal["id"])
        self.assertEqual(blocked["blocker"]["condition"], "服务恢复")
        self.service.goal_resume(goal["id"])

        ai = self.service.task_create("ai", goal["id"], "取消 AI", "验证单独取消归档")["record"]
        self.write_task(ai["id"], ai["title"], goal["id"])
        user = self.service.task_create("user", goal["id"], "取消用户任务", "验证结果归档", "other")["record"]
        self.service.task_cancel_ai(ai["id"], "不再需要此实现")
        self.service.task_finish_user(user["id"], "cancel", "用户确认无需处理")
        self.service.task_archive(ai["id"], "ai")
        self.service.task_archive(user["id"], "user")
        self.assertTrue(self.service.task_show(ai["id"], "ai")["archived"])
        self.assertTrue(self.service.task_show(user["id"], "user")["archived"])

        self.service.goal_submit(goal["id"])
        self.service.goal_revise(goal["id"], "补充交付说明")
        self.service.goal_submit(goal["id"])
        self.service.goal_complete(goal["id"])
        self.assertTrue(self.service.validate()["valid"])

    def test_identifiers_are_not_reused_after_archive(self) -> None:
        first = self.service.goal_create("第一个目标", "验证编号")["record"]
        self.write_goal(first["id"], first["title"])
        self.service.goal_cancel(first["id"], "完成编号验证")
        self.service.goal_archive(first["id"])
        second = self.service.goal_create("第二个目标", "编号必须递增")["record"]
        self.write_goal(second["id"], second["title"])
        self.assertEqual((first["id"], second["id"]), (1, 2))

    def test_concurrent_creates_are_serialized(self) -> None:
        goal = self.service.goal_create("并发目标", "验证文件锁和编号")["record"]
        self.write_goal(goal["id"], goal["title"])
        self.service.goal_start(goal["id"])

        def create(index: int) -> int:
            service = GoGoalService.locate(SKILL_ROOT, self.root)
            return service.task_create("user", goal["id"], f"并发任务 {index}", "验证文件锁和编号", "other")["record"]["id"]

        with ThreadPoolExecutor(max_workers=6) as executor:
            ids = list(executor.map(create, range(12)))
        self.assertEqual(sorted(ids), list(range(1, 13)))
        logs = self.service.log_list()
        self.assertEqual([item["id"] for item in logs], list(range(1, len(logs) + 1)))

    def test_cross_file_write_failure_rolls_back(self) -> None:
        target_path = self.root / "gogoal" / "target.json"
        log_path = self.root / "gogoal" / "log.json"
        before_target, before_log = target_path.read_bytes(), log_path.read_bytes()
        original_replace = storage._replace_bytes
        calls = 0

        def fail_second(path: Path, content: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("模拟第二个文件替换失败")
            original_replace(path, content)

        with patch("gogoal.storage._replace_bytes", side_effect=fail_second):
            with self.assertRaises(GoGoalError):
                self.service.goal_create("回滚目标", "写入不得留下部分状态")
        self.assertEqual(target_path.read_bytes(), before_target)
        self.assertEqual(log_path.read_bytes(), before_log)

    def test_english_initialization_copies_english_guides(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            GoGoalService.initialize(SKILL_ROOT, root, "English Project", "en-US")
            service = GoGoalService.locate(SKILL_ROOT, root)
            self.assertEqual(service.config_get("locale"), "en-US")
            self.assertIn("Goal document", (root / "gogoal" / "goal-writing.md").read_text(encoding="utf-8"))
            self.assertIn("AI task document", (root / "gogoal" / "task-writing.md").read_text(encoding="utf-8"))

    def test_incomplete_initialization_never_overwrites_existing_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "gogoal"
            data.mkdir()
            sentinel = data / "target.json"
            sentinel.write_text("do-not-overwrite", encoding="utf-8")
            with self.assertRaises(GoGoalError):
                GoGoalService.initialize(SKILL_ROOT, root, "冲突项目", "zh-CN")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "do-not-overwrite")
            self.assertFalse((data / "config.json").exists())

    def test_parallel_limit_lowering_and_resume_are_non_preemptive(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("设备没有 Git")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.service.config_set("execution.maxParallelTasks", 2)
        goal = self.service.goal_create("并行准入", "验证非抢占式规则")["record"]
        self.write_goal(goal["id"], goal["title"])
        self.service.goal_start(goal["id"])
        tasks = []
        for index in range(3):
            task = self.service.task_create("ai", goal["id"], f"任务 {index}", "验证容量")["record"]
            self.write_task(task["id"], task["title"], goal["id"])
            tasks.append(task)
        self.service.task_start(tasks[0]["id"])
        self.service.task_start(tasks[1]["id"])
        self.service.config_set("execution.maxParallelTasks", 1)
        self.assertEqual(self.service.capacity()["activeTasks"], 2)
        with self.assertRaises(GoGoalError):
            self.service.task_start(tasks[2]["id"])
        self.service.task_block(tasks[0]["id"], "等待资源", "资源恢复")
        self.service.task_resume(tasks[0]["id"])
        self.assertEqual(self.service.capacity()["activeTasks"], 2)


class DashboardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        GoGoalService.initialize(SKILL_ROOT, self.root, "测试项目", "zh-CN")
        self.service = GoGoalService.locate(SKILL_ROOT, self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_goal(self, identity: int, title: str) -> None:
        (self.root / "gogoal" / "targets" / f"{identity}.md").write_text(goal_document(identity, title), encoding="utf-8")

    def test_read_only_dashboard_api(self) -> None:
        goal = self.service.goal_create("看板目标", "验证真实 API")["record"]
        self.write_goal(goal["id"], goal["title"])
        handler = type("TestHandler", (DashboardHandler,), {
            "service": self.service,
            "assets": SKILL_ROOT / "assets" / "dashboard",
        })
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urllib.request.urlopen(base + "/api/snapshot") as response:
                snapshot = json.load(response)
                self.assertEqual(snapshot["config"]["project"], "测试项目")
                self.assertEqual(snapshot["targets"][0]["id"], goal["id"])
                self.assertTrue(snapshot["validation"]["valid"])
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            with urllib.request.urlopen(base + "/api/document?path=targets%2F1.md") as response:
                document = json.load(response)
                self.assertTrue(document["content"].startswith("# G-1 看板目标"))
            request = urllib.request.Request(base + "/api/snapshot", method="POST")
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(request)
            self.assertEqual(context.exception.code, 405)
            self.assertEqual(json.load(context.exception)["error"], "readOnly")
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(base + "/api/document?path=..%2Fconfig.json")
            self.assertEqual(context.exception.code, 400)
            self.assertEqual(json.load(context.exception)["error"], "invalidDocumentPath")
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=3)


class CliIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.entry = SKILL_ROOT / "scripts" / "gogoal.py"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def cli(self, *arguments: str, json_output: bool = False, expected: int = 0) -> object:
        command = [sys.executable, "-B", str(self.entry), "--project-root", str(self.root), *arguments]
        if json_output:
            command.append("--json")
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return json.loads(result.stdout) if json_output and result.stdout else result

    def write_goal(self, identity: int, title: str) -> None:
        (self.root / "gogoal" / "targets" / f"{identity}.md").write_text(goal_document(identity, title), encoding="utf-8")

    def write_task(self, identity: int, title: str, goal_id: int) -> None:
        (self.root / "gogoal" / "tasks" / f"{identity}.md").write_text(task_document(identity, title, goal_id), encoding="utf-8")

    def test_complete_cli_lifecycle_and_english_interface(self) -> None:
        initialized = self.cli("init", "--project", "English Project", "--locale", "en-US", json_output=True)
        self.assertEqual(initialized["message"], "GoGoal project initialized.")
        help_result = self.cli("--help")
        self.assertIn("Goal and task management Skill CLI", help_result.stdout)

        invalid_id = self.cli("task", "list", "--goal", "0", expected=2)
        self.assertIn("must be a positive integer", invalid_id.stderr)
        empty_title = self.cli("goal", "create", "--title", "", "--description", "Example", expected=2)
        self.assertIn("Title must not be empty.", empty_title.stderr)
        sensitive = self.cli("goal", "create", "--title", "Example", "--description", "api_token=do-not-store", expected=2)
        self.assertIn("Description may contain sensitive credentials", sensitive.stderr)

        goal = self.cli("goal", "create", "--title", "Release Skill", "--description", "Complete release", json_output=True)["record"]
        self.write_goal(goal["id"], goal["title"])
        self.cli("goal", "update", str(goal["id"]), "--title", "Release GoGoal")
        goal["title"] = "Release GoGoal"
        self.write_goal(goal["id"], goal["title"])
        self.cli("goal", "start", str(goal["id"]))

        ai = self.cli("task", "create", "--type", "ai", "--goal", str(goal["id"]), "--title", "Implement CLI", "--description", "Implement lifecycle", json_output=True)["record"]
        self.write_task(ai["id"], ai["title"], goal["id"])
        user = self.cli("task", "create", "--type", "user", "--kind", "decision", "--goal", str(goal["id"]), "--title", "Approve scope", "--description", "Confirm release scope", json_output=True)["record"]
        self.cli("task", "start", str(ai["id"]), "--type", "ai")
        self.cli("task", "block", str(ai["id"]), "--type", "ai", "--reason", "Waiting for test", "--condition", "Test available")
        self.cli("task", "resume", str(ai["id"]), "--type", "ai")
        self.cli("task", "complete", str(ai["id"]), "--type", "ai")
        self.cli("task", "complete", str(user["id"]), "--type", "user", "--result", "Approved")
        self.cli("goal", "submit", str(goal["id"]))
        self.cli("goal", "revise", str(goal["id"]), "--note", "Clarify release notes")
        self.cli("goal", "submit", str(goal["id"]))
        self.cli("goal", "complete", str(goal["id"]))
        archive = self.cli("goal", "archive", str(goal["id"]), json_output=True)
        self.assertEqual(archive["record"]["status"], "completed")
        validated = self.cli("validate", "--strict", json_output=True)
        self.assertTrue(validated["valid"])
        logs = self.cli("log", "list", "--limit", "100", json_output=True)
        self.assertEqual([entry["id"] for entry in logs], sorted((entry["id"] for entry in logs), reverse=True))
        self.assertTrue(any(entry["note"] == "Blocker resolved" for entry in logs))

    def test_cli_never_creates_git_commits(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("设备没有 Git")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.cli("init", "--project", "No Auto Commit")
        self.cli("config", "set", "git.autoCommit", "true")
        self.cli("goal", "create", "--title", "No commit", "--description", "CLI must not commit")
        result = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=self.root, text=True, capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
