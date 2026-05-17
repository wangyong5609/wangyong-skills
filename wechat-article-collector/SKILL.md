---
name: wechat-article-collector
description: 采集微信公众号历史文章，使用大加啦/极致了 API 获取文章列表、正文、封面、阅读量、点赞、在看、转发、收藏和评论，并输出通用 Markdown 与 CSV。Use when the user asks to 采集公众号文章、保存公众号历史文章、导出公众号正文/封面/互动数据、生成公众号文章数据 CSV。
---

# 微信公众号文章采集

把指定公众号的历史文章采集到本地目录，生成每篇文章的 Markdown、账号概览和文章数据 CSV。默认输出到当前目录下的 `output/wechat-articles/`，用户可以通过 `--output-dir` 指定任意位置。

## 脚本

使用内置脚本：

```bash
python3 scripts/collect_wechat_articles.py --account "公众号名称"
```

脚本调用大加啦/极致了接口：

- `POST https://www.dajiala.com/fbmain/monitor/v3/post_history`
- `GET https://www.dajiala.com/fbmain/monitor/v3/article_detail`
- `POST https://www.dajiala.com/fbmain/monitor/v3/read_zan_pro`

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

官网接口页当前包含公众号历史发文列表、文章详情、阅读/点赞/分享/评论/收藏数等接口说明；本脚本只使用其中采集文章所需的接口。页面结构可能调整，最终以官网登录后展示为准。

## 密钥配置

不要把 API key、verify code、Cookie 写进仓库、文章 Markdown 或最终回复。推荐在运行目录创建本地 `.env`，或用 `--env-file` 指定外部文件。

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

脚本生成：

- 每篇文章一个 Markdown，包含 frontmatter、封面、指标表、摘要和正文
- `账号概览.md`
- `文章数据.csv`

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

只采集正文，不采集阅读/点赞等互动数据：

```bash
python3 scripts/collect_wechat_articles.py --account "公众号名称" --no-metrics
```

## 注意

- 全量采集建议使用 `--delay 0.8` 或更高，降低接口限流概率。
- 如果接口返回 `code=10002`，检查 API key、verify code 或 Cookie。
- 不要删除 `.git/`、`.env` 或用户无关目录；只操作本次指定的输出目录。
- 完成后检查 `账号概览.md` 和 `文章数据.csv`。
