# 次幂公众号接口映射

来源：次幂数据 API 文档（2026-08-19 核对），主机 `https://api.cimidata.com`。所有请求为 JSON，所有受保护接口在 query 中传 `access_token`。

## 认证与成本

| 能力 | 路径 | 单价（元） | 必要 body |
| --- | --- | ---: | --- |
| 获取 token | `POST /api/v2/token` | 免费 | `app_id`, `app_secret` |
| 账号关键词检索 | `POST /api/v3/accounts/search` | 0.10 | `keyword` |
| 账号基本信息 | `POST /api/v2/accounts/detail` | 0.04 | `biz` 优先，或 `nickname` |
| 当日发文 | `POST /api/v2/articles/current` | 0.04 | `wxid` 优先，或 `nickname` |
| 历史文章 | `POST /api/v2/articles/history` | 0.05/页 | `wxid` |
| 完整文章 HTML | `POST /api/v2/articles/detail` | 0.01 | `url` |
| 完整互动 | `POST /api/v2/articles/data2` | 0.03 | `url` |
| 基础互动 | `POST /api/v2/articles/data` | 0.02 | `url` |
| 文章账号与基础信息 | `POST /api/v2/articles/info` | 0.02 | `url` |
| 一级评论 | `POST /api/v3/articles/comments` | 0.03/页 | `url` |
| 数据库关键词搜文 | `POST /api/v2/articles/search` | 0.02 | `keyword` |
| 微信搜一搜搜文 | `POST /api/v3/articles/search` | 0.05/页 | `keyword`, 可选 `page`（1–5） |
| 微信爆文 | `POST /api/v2/hot/articles` | 0.10/页 | 可选 `category`, `read_num`, `published_at`, `last_id` |
| 10w+ 爆文 | `POST /api/v2/10w/articles` | 0.10/页 | 可选 `category`, `published_at`, `last_id` |
| 网络热榜 | 文档页待实时读取 | 0.01 | 依 ShowDoc 当前页 |

文章纯正文和封面使用 `article-info` 的 `article.body` / `article.cover` 投影或完整 HTML 的本地正文提取，不额外叠加付费请求。请求频率：完整互动每篇至少间隔 3 秒，账号当天发文最多 1 QPS，文章基础信息最多 2 QPS。

## 字段归一化

- 文章 URL：优先 `content_url`，输出统一为 `article_url`。
- 互动：`read_num` → `read_count`，`old_like_num` → `like_count`，`like_num` → `watching_count`，`share_num` → `share_count`。
- 评论：仅保留 `content` 与 `like_num` 映射后的 `like_count`；分页标志 `buffer` 仅用于报告，默认不继续翻页。
- 历史列表中的 `content_url`、`cover`、`digest`、`published_at`、`title` 是归档所需的最小字段。

## 未固化的辅助端点

ShowDoc 左侧还提供搜狗临时链接转永久链接、封面单查、长链转短链、余额和错误码页。这些并非归档主链，也未出现在公开价格表。调用前先读取对应文档页，通过 `provider-call --path ... --body-json ... --price ...` 显式传入当次页面确认的路径、JSON body 与价格（免费填 `0`）；脚本不会猜测这些端点。
