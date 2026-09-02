# 第三方组件说明

GoGoal CLI 使用 Python 标准库；Markdown 转换与渲染安全层为本项目代码。看板随 Skill 打包以下固定前端组件，运行时不访问 CDN 或包管理器。

| 组件 | 版本 | 来源 | 许可证 | 用途 |
| --- | --- | --- | --- | --- |
| Mermaid | 10.9.1 | https://github.com/mermaid-js/mermaid | MIT | 离线渲染目标与任务 Markdown 中的 Mermaid 图。 |

Mermaid 浏览器构建包含其生产依赖代码。完整组件名称、版本、SPDX 许可证和来源见 `skills/gogoal/assets/dashboard/vendor/DEPENDENCIES.md`；随包许可证正文见同目录的 `MERMAID_LICENSE.txt` 与 `THIRD_PARTY_LICENSES.txt`。这些第三方组件继续遵守各自许可证，不因 GoGoal 使用 Apache-2.0 而改变。

开发参考目录中的原型依赖不进入正式运行时，也不构成 GoGoal 再分发组件。后续新增、移除或升级随 Skill 分发的第三方组件时，必须同步更新本文件、依赖清单和许可证正文，并在 CI 中校验。
