---
name: wechat-article-collector
description: 采集微信公众号历史文章，使用大加啦/极致了 API 获取正文、非 GIF 本地图片、阅读/点赞/在看/转发/收藏/评论总数和匿名一级评论，输出 Markdown、文章 CSV 与评论 CSV。Use when the user asks to 采集公众号文章、保存公众号历史文章和图片到本地、导出互动数据或一级评论用于内容分析。
---

# 微信公众号文章采集

把指定公众号的历史文章、静态图片、互动数据和公开一级评论采集到本地。默认输出到当前目录下的 `output/wechat-articles/`，也可以通过 `--output-dir` 指定其他位置。

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
- `POST https://www.dajiala.com/fbmain/monitor/v3/read_zan_pro`
- `POST https://www.dajiala.com/fbmain/monitor/v3/article_comment2`

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

不要把 API key、verify code、Cookie 写进仓库、文章 Markdown 或最终回复。可以在运行目录创建本地 `.env`，或用 `--env-file` 指定外部文件。

读取优先级：

1. 命令行参数：`--api-key`、`--verifycode`、`--cookie`
2. `--env-file /path/to/file.env`
3. 当前运行目录 `.env`
4. 已导出的系统环境变量

支持的变量：

```bash
DAJIALA_API_KEY="your-api-key"
DAJIALA_VERIFY_CODE="your-verify-code"
DAJIALA_COOKIE="optional-cookie"
```

兼容旧变量名：`JIZHILIAO_API_KEY`、`JIZHILIE_API_KEY`、`JIZHILIAO_VERIFY_CODE`、`JIZHILIAO_VERIFYCODE`、`JIZHILIE_VERIFY_CODE`、`VERIFY_CODE`。

## 输出

默认输出到：

```text
./output/wechat-articles/<公众号名>/
```

脚本仅生成：

```text
<公众号名>/
├── 文章数据.csv
├── 评论数据.csv
├── <日期>-<标题>.md
└── assets/
    └── <日期>-<标题>/
        ├── cover.jpg
        ├── 001.jpg
        └── 002.png
```

`文章数据.csv` 的字段固定为：

```text
title,content,article_url,publish_time,account,author,digest,read,like,looking,share,collect,comment_count
```

`评论数据.csv` 的字段固定为：

```text
article_url,content,like_num,is_top,province_name
```

评论不包含昵称、头像、时间、用户或评论 ID，也不包含回复正文。

如果用户想保存到其他目录，必须显式传：

```bash
python3 scripts/collect_wechat_articles.py \
  --account "公众号名称" \
  --output-dir "/path/to/export/wechat-articles"
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
- 评论接口使用 `buffer` 翻页采完公开一级评论，但不调用二级评论接口。
- `comment_count` 是互动接口返回的评论总数，可能包含公开回复。
- 全量采集建议使用 `--delay 0.8` 或更高，降低接口限流概率。
- 如果接口返回 `code=10002`，检查 API key、verify code 或 Cookie。
- 不要删除 `.git/`、`.env` 或用户无关目录；只操作本次指定的输出目录。
- 完成后检查两个 CSV 的字段、Markdown 本地图片引用，以及输出目录中不存在 GIF。
