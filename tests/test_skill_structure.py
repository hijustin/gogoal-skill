from __future__ import annotations

import re
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "gogoal"


class SkillStructureTestCase(unittest.TestCase):
    def test_open_agent_skill_layout_and_frontmatter(self) -> None:
        skill_md = SKILL / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        self.assertIsNotNone(match, "SKILL.md 必须包含 YAML frontmatter")
        fields = {}
        for line in match.group(1).splitlines():
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
        self.assertEqual(set(fields), {"name", "description"})
        self.assertEqual(fields["name"], "gogoal")
        self.assertRegex(fields["name"], r"^[a-z0-9-]{1,64}$")
        self.assertLessEqual(len(fields["description"]), 1024)
        self.assertNotIn("<", fields["description"])
        self.assertNotIn(">", fields["description"])
        self.assertLess(len(content.splitlines()), 500)
        self.assertEqual({item.name for item in SKILL.iterdir()}, {"SKILL.md", "scripts", "references", "assets"})

    def test_referenced_resources_exist_at_one_level(self) -> None:
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        references = set(re.findall(r"`(references/[^`]+)`", content))
        self.assertEqual(references, {
            "references/workflow.md", "references/data-format.md",
            "references/cli-reference.md", "references/document-contract.md",
            "references/git-workflow.md",
        })
        for relative in references:
            self.assertTrue((SKILL / relative).is_file(), relative)

    def test_no_plugin_or_runtime_package_manager_metadata(self) -> None:
        self.assertFalse((ROOT / ".codex-plugin").exists())
        self.assertFalse((ROOT / ".agents" / "plugins").exists())
        forbidden = {"package.json", "requirements.txt", "poetry.lock", "Pipfile"}
        self.assertFalse(any(path.name in forbidden for path in SKILL.rglob("*")))

    def test_dashboard_is_offline_and_third_party_inventory_is_present(self) -> None:
        assets = SKILL / "assets" / "dashboard"
        for name in ("index.html", "styles.css", "app.js"):
            self.assertTrue((assets / name).is_file())
            content = (assets / name).read_text(encoding="utf-8")
            self.assertNotRegex(content, r"<(script|link)[^>]+(src|href)=[\"']https?://", f"{name} 不能依赖 CDN")
            self.assertNotRegex(content, r"\bimport\s*\([^)]*https?://", f"{name} 不能动态加载远程模块")
        self.assertTrue((ROOT / "THIRD_PARTY_NOTICES.md").is_file())
        vendor = assets / "vendor"
        mermaid = vendor / "mermaid.min.js"
        self.assertEqual(hashlib.sha256(mermaid.read_bytes()).hexdigest(), "61b335a46df05a7ce1c98378f60e5f3e77a7fb608a1056997e8a649304a936d6")
        for name in ("DEPENDENCIES.md", "MERMAID_LICENSE.txt", "THIRD_PARTY_LICENSES.txt"):
            self.assertTrue((vendor / name).is_file(), name)
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("Mermaid | 10.9.1", notices)
        self.assertTrue((ROOT / "LICENSE").read_text(encoding="utf-8").startswith("                                 Apache License"))

    def test_required_locales_and_entrypoint(self) -> None:
        for locale in ("zh-CN", "en-US"):
            for name in ("goal-writing.md", "task-writing.md"):
                self.assertTrue((SKILL / "assets" / "writing" / locale / name).is_file())
        self.assertTrue((SKILL / "scripts" / "gogoal.py").is_file())

    def test_repository_documentation_layout(self) -> None:
        runtime_references = {path.name for path in (SKILL / "references").glob("*.md")}
        translated_references = {
            path.name for path in (ROOT / "docs" / "zh-CN" / "skill-reference").glob("*.md")
        }
        self.assertEqual(translated_references, runtime_references)
        self.assertTrue((ROOT / "docs" / "architecture" / "blueprint.md").is_file())
        self.assertTrue((ROOT / "docs" / "design" / "page.md").is_file())
        self.assertTrue((ROOT / "docs" / "design" / "design.md").is_file())
        self.assertTrue((ROOT / "docs" / "assets" / "gogoal-hero.png").is_file())
        self.assertTrue((ROOT / "docs" / "assets" / "gogoal-dashboard-en-US.jpg").is_file())
        self.assertTrue((ROOT / "docs" / "assets" / "gogoal-dashboard-zh-CN.jpg").is_file())
        self.assertTrue((ROOT / "README.zh-CN.md").is_file())
        self.assertFalse((ROOT / "reference").exists())

    def test_prototype_uses_device_time_and_current_refresh_interval(self) -> None:
        source = (ROOT / "prototypes" / "dashboard" / "app" / "page.tsx").read_text(encoding="utf-8")
        self.assertNotIn("Asia/Shanghai", source)
        self.assertNotIn("自动 60s", source)
        self.assertIn("自动 180s", source)


if __name__ == "__main__":
    unittest.main()
