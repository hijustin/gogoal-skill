# GoGoal

GoGoal 是一个通用、可分发的 Agent Skill：用户先与 AI 明确目标，授权启动后由主 AI 拆分、调度并完成任务，同时用项目内 JSON、Markdown、审计日志和本地只读看板保持全局可见。

GoGoal 遵循开放的 Agent Skills 目录约定，不依赖 Codex Plugin、Marketplace 或特定 AI 宿主。任何能够加载 `SKILL.md` 并执行本地脚本的智能体工具都可以集成它。

## 功能

- 目标、AI 任务和用户任务的完整状态流转与校验。
- 四个聚合 JSON 作为当前事实源，`log.json` 作为追加式管理时间线。
- 每个目标和 AI 任务使用独立 Markdown，写作结构可以在项目内自定义。
- Git 可用时支持主 AI 自主选择顺序执行、分支、工作树和子代理；Git 不可用时安全降级为单任务顺序执行。
- 离线、本地、只读看板，支持中文和英文、明暗主题、关联筛选、详情浮框和 Markdown 阅读。

## 安装

将 [`skills/gogoal`](skills/gogoal) 整个目录复制到宿主的 Skill 搜索路径，或让支持 GitHub Skill 安装的宿主从本仓库安装该目录。运行环境需要 Python 3.12 或更高版本；Git 和桌面 Chrome/Edge 为可选能力。

仓库本身就是分发载体，不需要 Codex Plugin、Marketplace、Node 包或 Python 包安装：

```bash
git clone https://github.com/hijustin/gogoal-skill.git
# 将 gogoal-skill/skills/gogoal 复制或链接到宿主公开的 Skill 搜索目录
```

GoGoal 不要求全局安装 Python 包。逻辑命令 `gogoal` 对应：

```bash
python3.12 <skill目录>/scripts/gogoal.py
```

如果希望在终端直接使用 `gogoal`，可以在自己的 PATH 中创建指向该脚本的包装命令；Skill 本身不修改用户环境。

Windows 可使用：

```powershell
py -3.12 <skill目录>\scripts\gogoal.py --version
```

## 快速开始

```bash
python3.12 skills/gogoal/scripts/gogoal.py init --project "示例项目"
python3.12 skills/gogoal/scripts/gogoal.py goal create \
  --title "发布项目" \
  --description "完成代码、文档和发布准备"
```

创建目标后，AI 按 `gogoal/goal-writing.md` 编写 `gogoal/targets/1.md`，再执行：

```bash
python3.12 skills/gogoal/scripts/gogoal.py validate
python3.12 skills/gogoal/scripts/gogoal.py goal start 1
python3.12 skills/gogoal/scripts/gogoal.py dashboard serve --open
```

CLI 的完整用法见 [命令参考](skills/gogoal/references/cli-reference.md)，工作流与权限边界见 [工作流](skills/gogoal/references/workflow.md)。

无需创建数据也可以直接体验仓库内的只读示例：

```bash
cd examples/demo-project
python3.12 ../../skills/gogoal/scripts/gogoal.py validate --strict
python3.12 ../../skills/gogoal/scripts/gogoal.py dashboard serve --open
```

## 安全边界

- CLI 只修改当前项目的 `gogoal/` 数据，不直接修改业务实现文件。
- CLI 永不创建 Git 提交、推送、Pull Request 或发布；`git.autoCommit` 只声明主 AI 是否可在完整动作后自行创建本地提交。
- 看板默认只监听 `127.0.0.1`，也允许通过配置或命令显式覆盖监听地址且不增加二次确认；非本机监听应仅在可信网络中使用，所有写入仍必须通过 CLI。
- 子代理只实现被派发任务，不得修改 GoGoal 管理数据或生命周期。
- JSON、日志和文档不应保存密码、令牌、个人敏感信息或生产隐私数据。

## 开发

```bash
/path/to/python3.12 -m unittest discover -s tests -v
/path/to/python3.12 skills/gogoal/scripts/gogoal.py --version
```

开发依据保留在 [`reference/`](reference)；它不是 Skill 运行时的一部分。

## 许可证

GoGoal 使用 [Apache License 2.0](LICENSE)。第三方组件说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
