# 仓库开发指南

## 项目结构与模块组织

本仓库存放独立的 AI Agent skills。每个 skill 独占一个顶层目录，并包含一个带 YAML frontmatter 的 `SKILL.md` 入口文件：

```text
skill-name/
  SKILL.md
  scripts/
  docs/
  templates/
  agents/ 或 config/
```

现有 skill 包括 `cimidata-wechat-article-collector/`、`wechat-article-collector/`、`wechat-official-account-comic/`、`macos-app-icon/`、`life-interview-planner/` 和 `ai-creator-cover/`。可复用的 Python 或 shell 脚本放 `scripts/`，参考资料放 `docs/` 或 `references/`，静态提示词/数据文件放 `templates/`，模型或 agent 配置放 `agents/` 或 `config/`。

## 构建、测试与开发命令

仓库目前没有统一的构建系统，改动在哪个 skill 目录就在哪个目录里操作。

常用命令：

```bash
git status --short
python3 path/to/script.py --help
python3 -m py_compile path/to/script.py
```

用 `--help` 验证脚本接口，用 `py_compile` 做 Python 脚本的快速语法检查。如果某个 skill 新增依赖，在该 skill 的 `SKILL.md` 里写清安装和运行命令。

## 代码风格与命名约定

新增 skill 的目录名使用 kebab-case，并与 `SKILL.md` frontmatter 里的 `name` 保持一致。Markdown 要直接、面向任务。Python 使用 4 空格缩进、清晰的 `argparse` 参数，本地配置走环境变量。不要提交生成产物、本地 IDE 状态、`.DS_Store`、凭据、Cookie、API key 或用户私有导出文件。

新增 skill 时，`SKILL.md` 需要包含：

```yaml
---
name: example-skill
description: 简短的触发场景描述。
---
```

## 测试指南

根目录没有配置正式的测试框架。对带脚本的 skill，当逻辑不简单时，在脚本旁边添加针对性测试，命名为 `test_*.py` 或 `*.test.py`。至少要做语法检查和一次小规模试运行，例如：

```bash
python3 -m py_compile wechat-article-collector/scripts/collect_wechat_articles.py
python3 -m py_compile wechat-official-account-comic/scripts/build_long_comic.py
python3 wechat-article-collector/scripts/collect_wechat_articles.py --help
```

除非凭据和调用范围明确，否则不要运行会调用付费或限流 API 的命令。

## Commit 与 Pull Request 规范

使用简洁的祈使句 commit message，例如 `Add wechat article collector skill` 或 `Update macOS icon workflow`。

Pull request 需要说明：改动了哪个 skill、验证命令清单、新增的环境变量；涉及视觉或生成类资产的流程时，附截图或示例输出。

## 安全与配置注意事项

密钥等敏感信息放在仓库之外。使用 `.env`、本地配置文件或环境变量，文档里只写变量名、不写真实值。如果脚本要写入仓库外的目录，输出路径必须显式指定，且不要删除无关文件。
