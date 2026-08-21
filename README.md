# wangyong-skills

一个持续维护的中文 AI Agent Skill 开源仓库。每个目录都是独立 Skill，解决一个明确的问题；安装后直接告诉 AI 你想完成什么即可。

## 安装任意一个 Skill

把下面这段提示词复制给你的 AI，并把 `<skill-name>` 换成下表中的 Skill 名称：

```text
请帮我安装这个仓库里的 <skill-name>：
https://github.com/wangyong5609/wangyong-skills

只安装这个 Skill。安装完成后，告诉我可以怎么开始使用。
```

例如，安装次幂公众号文章采集 Skill 时，把 `<skill-name>` 换成 `cimidata-wechat-article-collector`。

## Skill 目录

| Skill | 能做什么 | 状态 |
| --- | --- | --- |
| `cimidata-wechat-article-collector` | 按最近文章或日期范围采集公众号正文，支持断点续查、互动数据和脱敏评论 | 推荐安装 |
| `wechat-article-collector` | 使用极致了/大加啦采集公众号历史文章、正文图片、互动数据和可选评论 | 持续维护 |
| `wechat-official-account-comic` | 生成可发布的微信公众号漫画长图，支持多种可复用风格 | 持续维护 |
| `macos-app-icon` | 生成、优化、预览和打包 macOS `.icns` 图标 | 持续维护 |
| `life-interview-planner` | 通过结构化访谈梳理人生方向、优势与下一步实验 | 持续维护 |
| `ai-creator-cover` | 设计 AI 自媒体视频封面和中文生图提示词 | 持续维护 |

所有 Skill 都可以单独安装、单独使用。具体输入、输出和首次使用说明，请以各目录中的 `SKILL.md` 为准。

## 公众号文章采集：怎么选

| Skill | 数据来源 | 适合谁 |
| --- | --- | --- |
| `cimidata-wechat-article-collector` | 次幂数据 API | 新用户、希望控制成本的日常采集；当前更推荐安装 |
| `wechat-article-collector` | 极致了/大加啦 API | 已有极致了账号、已有相关工作流的用户 |

两者都能采集正文和互动数据。次幂版的常见调用成本通常更低，执行前会先展示本次最高费用并等待确认；极致了版保留给已有用户继续使用。接口价格会调整，请以各服务商当期后台价格为准。

## 使用示例

安装后，直接用结果描述来告诉 AI：

```text
帮我采集「公众号名称」最近一篇文章，只要正文。
```

```text
帮我采集「公众号名称」2026 年发布的全部文章，只要正文。
```

```text
帮我做一张微信公众号漫画长图，主题是“为什么下午三点容易困”。
```

```text
根据这张图片生成一个 macOS 应用图标。
```

```text
和我做一次人生方向访谈。
```

```text
帮我设计一张 AI 自媒体视频封面。
```

## 效果预览

| Skill | 示例 |
| --- | --- |
| `wechat-article-collector` | [查看采集效果](./docs/examples/wechat-article-collector.png) |
| `wechat-official-account-comic` | [暖白手绘漫画](./docs/examples/wechat-comic-warm-white-handdrawn.png) / [蓝栏柔彩漫画](./docs/examples/wechat-comic-blue-bar-soft-color.png) / [绿底粗线漫画](./docs/examples/wechat-comic-green-bold-line.png) |
| `ai-creator-cover` | [查看全部封面示例](./ai-creator-cover/assets/examples/showcase/) |

## 项目说明

这是个人维护的开源 Skill 仓库。新的 Skill 会在完成真实使用验证后加入；已有 Skill 会根据实际反馈持续改进。

项目约定：

- 每个顶层 Skill 目录必须包含 `SKILL.md`。
- 目录名使用 kebab-case，并与 frontmatter 中的 `name` 对应。
- 可复用脚本放入 `scripts/`，参考资料放入 `docs/` 或 `references/`。
- 不提交 API Key、Secret、Cookie、个人照片、生成产物或本地研究数据。
- 付费接口必须先说明范围与费用上限，得到确认后才调用。

## 贡献与反馈

欢迎提交 Issue、改进建议和经过真实使用验证的 Skill。新增 Skill 请说明：

- 它解决什么问题；
- 用户会怎样描述这个需求；
- 是否依赖外部 API 或付费服务；
- 如何验证它能正常工作。


本仓库不维护统一依赖文件；需要依赖的 Skill 会在自己的目录中说明。

## 开源许可

[MIT License](./LICENSE)
