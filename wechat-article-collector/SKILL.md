---
name: wechat-article-collector
description: 采集微信公众号历史文章、正文图片和阅读/点赞/在看/转发/收藏等互动数据；只有用户明确确认后才采集公开一级评论。Use when the user asks to 采集公众号历史文章、文章内容、互动指标或评论数据。
---

# 微信公众号文章采集

把指定公众号的历史文章、正文、静态图片和互动数据采集到本地。公开一级评论是单独的可选范围，默认不采集。默认输出到当前目录下的 `output/wechat-articles/`，也可以通过 `--output-dir` 指定其他位置。

## 采集前确认门（必须）

在任何计费接口调用前，先向用户展示可采集范围并等待明确确认。确认内容至少包括账号、日期/数量范围、输出目录和以下范围：

| 选项 | 采集内容 | 默认 |
| --- | --- | --- |
| A | 历史文章索引：标题、链接、发布时间、摘要、封面等 | 选中 |
| B | 文章内容：正文文本、Markdown 和正文静态图片 | 选中 |
| C | 互动指标：阅读、点赞、在看、转发、收藏、评论总数 | 选中 |
| D | 公开一级评论：评论内容、评论点赞数、置顶状态、省份 | 不选中 |

向用户确认时使用简短模板：

```text
本次准备采集：A 历史文章索引、B 正文与图片、C 互动指标；评论内容 D 默认不采集。
范围：<账号>/<日期或篇数>/<输出目录>。
是否确认？如果要采集公开一级评论，请明确回复“确认采集评论”。
```

收到明确确认后才执行采集。A/B/C 是默认文章采集包；用户明确选择 D 时，才在命令中加入 `--include-comments`。只有“确认”但没有清楚说明是否包含评论时，继续按默认不采集评论执行，并在结果中报告这一点。

## 第一次使用：由 Agent 帮用户配置

默认把用户当作不熟悉命令行的普通用户。不要先让用户执行 `cp`、`export`、编辑 `.env` 或理解“环境变量”。

运行前先检查当前工作目录能否读取 `DAJIALA_API_KEY`。如果没有，只用通俗语言询问：

1. “请把你在极致了/大加啦后台看到的 API Key 发给我。”
2. “如果后台设置了附加码，也请一起发给我；没有就回复‘没有’。”

如果用户还没有账号，直接把官方接口页发给他，让他完成注册或登录：

```text
https://www.dajiala.com/main/interface?actnav=0
```

收到 API Key 和附加码后，由 Agent 自动完成以下操作，不再要求用户输入命令：

1. 把凭据保存到本次采集工作目录的本地 `.env`。
2. 只写入或更新 `DAJIALA_API_KEY` 和 `DAJIALA_VERIFY_CODE`；没有附加码时写空值。
3. 如果目录属于 Git 仓库，先确认 `.gitignore` 已忽略 `.env` 和 `.env.*`；未忽略时先补上规则。
4. 检查 `.env` 没有出现在 Git 已跟踪文件或待提交列表中。
5. 只报告“配置成功/失败”，绝不在工具输出、最终回复、日志、Markdown 或 CSV 中回显密钥。

API Key 是敏感信息。提醒用户只在当前私聊任务中提供，不要发布到 GitHub、Issue、群聊或公开文档。不要提交或推送 `.env`。

## 脚本

使用内置脚本：

```bash
python3 scripts/collect_wechat_articles.py --account "公众号名称"
```

脚本调用大加啦/极致了接口：

- `POST https://www.dajiala.com/fbmain/monitor/v3/post_history`
- `POST https://www.dajiala.com/fbmain/monitor/v3/article_html`
- `POST https://www.dajiala.com/fbmain/monitor/v3/read_zan_pro`（阅读、点赞、在看、转发、收藏、评论总数）
- `POST https://www.dajiala.com/fbmain/monitor/v3/article_comment2`（仅在用户确认 D 后调用）

接口参数以官方 Apifox 文档为准：

```text
https://s.apifox.cn/410674f9-f451-4b4f-957a-5f54f243bc83/llms.txt
```

历史列表接口当前使用 `ghid`、文章 `url` 或 `nickname` 作为账号定位参数，使用 `offset` 翻页；旧的 `name`/`page` 参数不要再作为默认调用方式。脚本支持 `--ghid` 和 `--account-url`，只传 `--account` 时使用当前接口可用的 `nickname` 参数。

不要调用公众号文章二级评论接口。

## 获取大加啦 API Key

如果用户还没有大加啦/极致了账号，先引导他去官方接口页注册和开通：

```text
https://www.dajiala.com/main/interface?actnav=0
```

推荐步骤：

1. 打开官方接口页，按页面提示注册或登录账号。
2. 注册页通常会要求填写姓名、联系方式、公司/行业和大致需求；提交后按官网提示完成验证。
3. 登录后进入 API 接口页或会员中心，查看当前账号的 API key、余额/体验额度、接口资费和使用情况。
4. 如果页面显示有 `verifycode` 或“附加码”，把它填入 `DAJIALA_VERIFY_CODE`；如果没有开启附加码，可以留空。
5. 如果接口报权限、余额或次数不足，让用户回到接口页查看余额、充值续费和接口使用记录。

接口按请求计费。运行前确认账号余额和采集范围；不要为测试执行不必要的全量采集。

## 技术用户：手动配置（可选）

本节只给熟悉命令行的用户使用。普通用户应由 Agent 按“第一次使用”流程自动配置。

不要把 API key、verify code 写进仓库、文章 Markdown 或最终回复。可以在运行目录创建本地 `.env`，或用 `--env-file` 指定外部文件。

读取优先级：

1. 命令行参数：`--api-key`、`--verifycode`
2. `--env-file /path/to/file.env`
3. 当前运行目录 `.env`
4. 已导出的系统环境变量

支持的变量：

```bash
DAJIALA_API_KEY="your-api-key"
DAJIALA_VERIFY_CODE="your-verify-code"
```

兼容旧变量名：`JIZHILIAO_API_KEY`、`JIZHILIE_API_KEY`、`JIZHILIAO_VERIFY_CODE`、`JIZHILIAO_VERIFYCODE`、`JIZHILIE_VERIFY_CODE`、`VERIFY_CODE`。

## 输出

默认输出到：

```text
./output/wechat-articles/<公众号名>/
```

默认生成：

```text
<公众号名>/
├── 文章数据.csv
├── <日期>-<标题>.md
└── assets/
    └── <日期>-<标题>/
        ├── cover.jpg
        ├── 001.jpg
        └── 002.png
```

启用 `--include-comments` 后，额外生成：

```text
<公众号名>/评论/<文章标题>.csv
```

`文章数据.csv` 的字段固定为：

```text
title,content,article_url,publish_time,account,author,digest,read,like,looking,share,collect,comment_count
```

`评论/<文章标题>.csv` 每篇文章单独生成，文件名只使用文章标题。字段固定为：

```text
article_url,content,like_num,is_top,province_name
```

只有启用 `--include-comments` 时才生成 `评论/` 目录和评论 CSV。评论不包含昵称、头像、时间、用户或评论 ID，也不包含回复正文。

如果用户想保存到其他目录，必须显式传：

```bash
python3 scripts/collect_wechat_articles.py \
  --account "公众号名称" \
  --output-dir "/path/to/export/wechat-articles"
```

如果公众号名称无法定位，可使用公众号原始 ID 或任意文章链接：

```bash
python3 scripts/collect_wechat_articles.py \
  --ghid "gh_xxxxxxxxxxxx"

python3 scripts/collect_wechat_articles.py \
  --account-url "https://mp.weixin.qq.com/s/文章链接"
```

也可以继续直接使用公众号名称：

```bash
python3 scripts/collect_wechat_articles.py \
  --account "公众号名称"
```

用户明确确认采集评论后：

```bash
python3 scripts/collect_wechat_articles.py \
  --account "公众号名称" \
  --include-comments
```

## 常用命令

测试采集 1 篇：

```bash
python3 scripts/collect_wechat_articles.py --account "公众号名称" --limit 1
```

从指定日期开始：

```bash
python3 scripts/collect_wechat_articles.py --account "公众号名称" --start-date 2026-01-01
```

## 注意

- 只下载封面和正文实际使用的静态图片；GIF 不下载、不转换，也不写入 Markdown。
- 图片按内容去重，下载失败自动重试 3 次。仍失败时保留远程链接、报告部分成功并返回非零状态。
- 互动接口使用官方 Pro 接口，一次返回阅读、点赞、在看、转发、收藏和评论总数，并写入 `文章数据.csv` 和文章 Markdown 的指标表。这里的 `comment_count` 是数量指标，不等于采集评论正文。
- 评论接口使用 `buffer` 翻页采完公开一级评论，但仅在 `--include-comments` 已启用时调用；不调用二级评论接口，官方返回的昵称、头像和回复正文不写入当前匿名评论 CSV。
- `comment_count` 是互动接口返回的评论总数，可能包含公开回复。
- 历史接口使用 `offset` 翻页；接口返回 `is_end` 或没有下一页 offset 时停止，避免重复或无限请求。
- 官方接口 QPS 不得高于 5 次/秒；脚本对 `-1/106/107/111/112/2003/2005/500` 等临时错误做指数退避重试，全量采集仍建议使用 `--delay 0.8` 或更高。
- 如果接口返回 `code=105`，优先检查 `--ghid`、`--account-url` 或公众号名称定位；如果接口返回 `code=10002`，检查 API key 或 verify code。
- 默认运行不会读取、更新或删除已有评论文件；需要刷新评论时，先重新确认范围，再显式加入 `--include-comments`。
- 不要删除 `.git/`、`.env` 或用户无关目录；只操作本次指定的输出目录。

## 完成标准

只有同时满足以下条件才报告采集完成：

1. 已记录本次确认的账号、范围、输出目录和 A/B/C/D 选择。
2. `文章数据.csv` 字段完整，文章数量与实际写入的 Markdown 数量一致。
3. 每个 Markdown 的本地图片引用都能找到对应文件，输出目录中没有 GIF。
4. D 未选中时，未调用 `article_comment2`，且本次没有新建评论 CSV；D 已选中时，评论 CSV 与文章一一对应，并报告一级评论行数。
5. 最终报告区分 `comment_count` 总数和评论 CSV 的一级评论行数，并列出输出路径和异常数量。
