#!/usr/bin/env python3
"""Collect WeChat official-account articles into Markdown and CSV files.

The script calls the Dajiala/Jizhiliao API endpoints:
- POST /fbmain/monitor/v3/post_history
- GET  /fbmain/monitor/v3/article_detail
- POST /fbmain/monitor/v3/read_zan_pro
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


API_BASE = "https://www.dajiala.com"
DEFAULT_OUTPUT_DIR = Path(
    os.getenv("WECHAT_ARTICLE_OUTPUT_DIR", Path.cwd() / "output" / "wechat-articles")
).expanduser()
WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


class SimpleHtmlToMarkdown(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.href_stack: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag in {"p", "section", "div", "br"}:
            self.parts.append("\n")
        elif tag in {"h1", "h2", "h3"}:
            self.parts.append("\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "img":
            src = attrs_dict.get("data-src") or attrs_dict.get("src") or ""
            alt = attrs_dict.get("alt") or ""
            if src:
                self.parts.append(f"\n![{alt}]({src})\n")
        elif tag == "a":
            self.href_stack.append(attrs_dict.get("href"))
        elif tag in {"strong", "b"}:
            self.parts.append("**")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "section", "div", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")
        elif tag == "a":
            href = self.href_stack.pop() if self.href_stack else None
            if href:
                self.parts.append(f"({href})")
        elif tag in {"strong", "b"}:
            self.parts.append("**")

    def handle_data(self, data: str) -> None:
        text = html.unescape(data).strip()
        if text:
            if self.href_stack:
                self.parts.append(f"[{text}]")
            else:
                self.parts.append(text)

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def load_dotenv(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not value:
            continue
        if override or key not in os.environ:
            os.environ[key] = value


def env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


def sanitize_filename(value: str, max_len: int = 80) -> str:
    value = re.sub(r"[\\/:*?\"<>|#\n\r\t]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value or "未命名")[:max_len]


def parse_ts(value: Any) -> dt.datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or str(value).isdigit():
        num = int(value)
        if num > 100000000000:
            num //= 1000
        return dt.datetime.fromtimestamp(num)
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        return None


def yaml_scalar(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def html_to_markdown(html_text: str) -> str:
    parser = SimpleHtmlToMarkdown()
    parser.feed(html_text or "")
    return parser.markdown()


@dataclass
class DajialaClient:
    api_key: str
    verifycode: str = ""
    cookie: str = ""
    timeout: int = 30
    api_base: str = API_BASE

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self.api_base.rstrip("/") + path
        if params:
            query = urllib.parse.urlencode(params, doseq=True, safe="")
            url = f"{url}?{query}"

        data = None
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {raw[:300]}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"接口返回不是 JSON: {raw[:300]}") from exc

    def history(self, account: str, page: int) -> dict[str, Any]:
        return self.request_json(
            "POST",
            "/fbmain/monitor/v3/post_history",
            body={
                "biz": "",
                "url": "",
                "name": account,
                "page": page,
                "key": self.api_key,
                "verifycode": self.verifycode,
            },
        )

    def detail(self, article_url: str) -> dict[str, Any]:
        return self.request_json(
            "GET",
            "/fbmain/monitor/v3/article_detail",
            params={
                "url": article_url,
                "key": self.api_key,
                "model": 1,
                "mode": 1,
                "verifycode": self.verifycode,
            },
        )

    def metrics(self, article_url: str) -> dict[str, Any]:
        return self.request_json(
            "POST",
            "/fbmain/monitor/v3/read_zan_pro",
            body={
                "url": article_url,
                "key": self.api_key,
                "verifycode": self.verifycode,
            },
        )


def assert_ok(response: dict[str, Any], context: str, allow_end: bool = False) -> None:
    code = response.get("code")
    if code in (0, None):
        return
    if allow_end and code in (110, 115):
        return
    msg = response.get("msg") or response.get("message") or ""
    raise RuntimeError(f"{context}失败: code={code}, msg={msg}")


def pick_metrics(response: dict[str, Any]) -> dict[str, int]:
    data = response.get("data") or {}
    return {
        "read": int(data.get("read") or data.get("read_num") or 0),
        "like": int(data.get("zan") or data.get("like_num") or 0),
        "looking": int(data.get("looking") or data.get("old_like_num") or 0),
        "share": int(data.get("share_num") or data.get("share_count") or 0),
        "collect": int(data.get("collect_num") or 0),
        "comment": int(data.get("comment_count") or 0),
    }


def merge_article(account: str, history: dict[str, Any], detail: dict[str, Any], metrics: dict[str, int]) -> dict[str, Any]:
    publish_dt = parse_ts(history.get("post_time") or detail.get("pubtime") or detail.get("create_time"))
    markdown = html_to_markdown(detail.get("content_multi_text") or "")
    plain_content = detail.get("content") or ""
    if not markdown:
        markdown = plain_content.strip()

    images = detail.get("picture_page_info_list") or []
    videos = detail.get("video_page_infos") or []
    return {
        "title": detail.get("title") or history.get("title") or "无标题",
        "account": detail.get("nick_name") or account,
        "author": detail.get("author") or "",
        "url": detail.get("url") or history.get("url") or "",
        "source_url": detail.get("source_url") or "",
        "digest": detail.get("desc") or history.get("digest") or "",
        "publish_time": publish_dt.isoformat(sep=" ") if publish_dt else "",
        "date": publish_dt.date().isoformat() if publish_dt else "未知日期",
        "year": publish_dt.year if publish_dt else "",
        "month": publish_dt.month if publish_dt else "",
        "weekday": WEEKDAYS[publish_dt.weekday()] if publish_dt else "",
        "cover": detail.get("cdn_url_1_1") or history.get("cover_url") or history.get("pic_cdn_url_1_1") or "",
        "biz": detail.get("biz") or "",
        "hashid": detail.get("hashid") or "",
        "idx": detail.get("idx") or history.get("position") or "",
        "appmsgid": history.get("appmsgid") or "",
        "original": detail.get("copyright_stat") if detail.get("copyright_stat") is not None else history.get("original"),
        "item_show_type": detail.get("item_show_type") or history.get("item_show_type") or "",
        "read": metrics["read"],
        "like": metrics["like"],
        "looking": metrics["looking"],
        "share": metrics["share"],
        "collect": metrics["collect"],
        "comment": metrics["comment"],
        "word_count": len(plain_content),
        "images": images,
        "videos": videos,
        "content": markdown,
        "plain_content": plain_content,
    }


def article_file_name(article: dict[str, Any]) -> str:
    unique = str(article.get("appmsgid") or article.get("hashid") or "")
    suffix = f"-{unique}" if unique else ""
    return f"{article['date']}-{sanitize_filename(article['title'])}{suffix}.md"


def write_article(output_dir: Path, article: dict[str, Any]) -> Path:
    account_dir = output_dir / sanitize_filename(article["account"])
    account_dir.mkdir(parents=True, exist_ok=True)

    path = account_dir / article_file_name(article)

    frontmatter_keys = [
        "title",
        "account",
        "author",
        "url",
        "source_url",
        "digest",
        "publish_time",
        "date",
        "year",
        "month",
        "weekday",
        "cover",
        "biz",
        "hashid",
        "idx",
        "appmsgid",
        "original",
        "item_show_type",
        "read",
        "like",
        "looking",
        "share",
        "collect",
        "comment",
        "word_count",
    ]
    fm = ["---"]
    for key in frontmatter_keys:
        fm.append(f"{key}: {yaml_scalar(article.get(key))}")
    fm.append("tags:")
    fm.append("  - 公众号文章")
    fm.append("  - 创作数据")
    fm.append("---")

    metric_table = "\n".join(
        [
            "| 指标 | 数值 |",
            "| --- | ---: |",
            f"| 阅读量 | {article['read']} |",
            f"| 点赞 | {article['like']} |",
            f"| 在看 | {article['looking']} |",
            f"| 转发 | {article['share']} |",
            f"| 收藏 | {article['collect']} |",
            f"| 评论 | {article['comment']} |",
            f"| 字数 | {article['word_count']} |",
        ]
    )
    cover_block = f"![封面]({article['cover']})" if article.get("cover") else ""
    body_parts = [
        "\n".join(fm),
        f"# {article['title']}",
    ]
    if cover_block:
        body_parts.append(cover_block)
    body_parts.extend(
        [
            f"公众号：{article['account']}",
            f"原文：{article['url']}",
            f"发布时间：{article['publish_time'] or '未知'}",
            metric_table,
            "## 摘要\n" + (article["digest"] or "无"),
            "## 正文\n" + (article["content"] or article["plain_content"] or "无正文"),
        ]
    )
    body = "\n\n".join(body_parts)
    path.write_text(body + "\n", encoding="utf-8")
    return path


def write_indexes(account_dir: Path, account: str, articles: list[dict[str, Any]]) -> None:
    articles = sorted(articles, key=lambda x: x.get("publish_time") or "", reverse=True)
    total_read = sum(int(a.get("read") or 0) for a in articles)
    total_like = sum(int(a.get("like") or 0) for a in articles)

    overview_lines = [
        f"# {account} 账号概览",
        "",
        f"- 文章数：{len(articles)}",
        f"- 总阅读：{total_read}",
        f"- 总点赞：{total_like}",
        f"- 最近采集：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 文章列表",
    ]
    for article in articles:
        file_name = article_file_name(article)
        link = urllib.parse.quote(file_name)
        overview_lines.append(
            f"- [{article['date']} {article['title']}]({link})"
            f" 阅读 {article['read']} / 赞 {article['like']} / 在看 {article['looking']}"
        )
    (account_dir / "账号概览.md").write_text("\n".join(overview_lines) + "\n", encoding="utf-8")

    with (account_dir / "文章数据.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "publish_time",
                "url",
                "read",
                "like",
                "looking",
                "share",
                "collect",
                "comment",
                "word_count",
            ],
        )
        writer.writeheader()
        for article in articles:
            writer.writerow({key: article.get(key, "") for key in writer.fieldnames})


def collect(args: argparse.Namespace) -> int:
    load_dotenv(Path.cwd() / ".env", override=True)
    if args.env_file:
        load_dotenv(Path(args.env_file).expanduser(), override=True)

    api_key = args.api_key or env_first("DAJIALA_API_KEY", "JIZHILIAO_API_KEY", "JIZHILIE_API_KEY")
    verifycode = args.verifycode or env_first(
        "DAJIALA_VERIFY_CODE",
        "JIZHILIAO_VERIFY_CODE",
        "JIZHILIAO_VERIFYCODE",
        "JIZHILIE_VERIFY_CODE",
        "VERIFY_CODE",
    )
    cookie = args.cookie or env_first("DAJIALA_COOKIE")
    if not api_key:
        print("缺少 API key：请设置 DAJIALA_API_KEY，或传 --api-key", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    account = args.account.strip()
    client = DajialaClient(api_key=api_key, verifycode=verifycode, cookie=cookie, timeout=args.timeout)

    start_date = dt.date.fromisoformat(args.start_date) if args.start_date else None
    collected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    page = 1

    while True:
        if args.max_pages and page > args.max_pages:
            break
        print(f"获取列表：{account} 第 {page} 页")
        history_response = client.history(account, page)
        assert_ok(history_response, "获取文章列表", allow_end=True)
        if history_response.get("code") in (110, 115):
            break
        items = history_response.get("data") or []
        if not items:
            break

        should_stop_by_date = False
        for item in items:
            if not args.include_deleted and str(item.get("is_deleted", "0")) != "0":
                continue
            article_url = item.get("url") or ""
            if not article_url or article_url in seen_urls:
                continue
            publish_dt = parse_ts(item.get("post_time") or item.get("post_time_str"))
            if start_date and publish_dt and publish_dt.date() < start_date:
                should_stop_by_date = True
                continue

            seen_urls.add(article_url)
            print(f"  采集：{item.get('title') or article_url}")
            detail = client.detail(article_url)
            assert_ok(detail, "获取文章详情")
            metric_values = {"read": 0, "like": 0, "looking": 0, "share": 0, "collect": 0, "comment": 0}
            if args.collect_metrics:
                metric_response = client.metrics(article_url)
                assert_ok(metric_response, "获取互动数据")
                metric_values = pick_metrics(metric_response)

            article = merge_article(account, item, detail, metric_values)
            write_article(output_dir, article)
            collected.append(article)
            if args.limit and len(collected) >= args.limit:
                should_stop_by_date = True
                break
            time.sleep(args.delay)

        total_page = int(history_response.get("total_page") or 0)
        if should_stop_by_date or (total_page and page >= total_page):
            break
        page += 1
        time.sleep(args.delay)

    if collected:
        account_name = collected[0]["account"] or account
        account_dir = output_dir / sanitize_filename(account_name)
        write_indexes(account_dir, account_name, collected)
    print(f"完成：采集 {len(collected)} 篇，输出目录 {output_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="采集公众号历史文章，输出 Markdown 与 CSV")
    parser.add_argument("--account", required=True, help="公众号名称，例如：人民日报")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认 ./output/wechat-articles")
    parser.add_argument("--start-date", default="", help="只采集此日期之后，格式 YYYY-MM-DD；留空采集全部")
    parser.add_argument("--limit", type=int, default=0, help="最多采集文章数，0 表示不限制")
    parser.add_argument("--max-pages", type=int, default=0, help="最多翻页数，0 表示按接口 total_page 采完")
    parser.add_argument("--delay", type=float, default=0.6, help="接口调用间隔秒数")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP 超时秒数")
    parser.add_argument("--no-metrics", dest="collect_metrics", action="store_false", help="不采集阅读/点赞等互动数据")
    parser.add_argument("--include-deleted", action="store_true", help="包含已删除文章")
    parser.add_argument("--api-key", default="", help="大加啦/极致了 API key，建议用环境变量 DAJIALA_API_KEY")
    parser.add_argument("--verifycode", default="", help="附加码，建议用环境变量 DAJIALA_VERIFY_CODE")
    parser.add_argument("--cookie", default="", help="必要时传大加啦 Cookie，建议用环境变量 DAJIALA_COOKIE")
    parser.add_argument("--env-file", default="", help="读取指定 .env 文件；优先级高于当前目录 .env")
    parser.set_defaults(collect_metrics=True)
    return parser


def main() -> int:
    return collect(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
