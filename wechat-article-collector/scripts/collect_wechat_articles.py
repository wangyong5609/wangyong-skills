#!/usr/bin/env python3
"""Collect WeChat articles, local static images, metrics, and first-level comments."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Optional


API_BASE = "https://www.dajiala.com"
TRANSIENT_API_CODES = {-1, 106, 107, 111, 112, 2003, 2005, 500}
DEFAULT_OUTPUT_DIR = Path(
    os.getenv("WECHAT_ARTICLE_OUTPUT_DIR", Path.cwd() / "output" / "wechat-articles")
).expanduser()
ARTICLE_FIELDS = [
    "title",
    "content",
    "article_url",
    "publish_time",
    "account",
    "author",
    "digest",
    "read",
    "like",
    "looking",
    "share",
    "collect",
    "comment_count",
]
COMMENT_FIELDS = ["article_url", "content", "like_num", "is_top", "province_name"]
BLOCK_TAGS = {"p", "section", "div", "article", "blockquote"}
SKIP_TAGS = {"head", "script", "style"}
ImageResolver = Callable[[str, dict[str, Optional[str]]], Optional[str]]


class SimpleHtmlToMarkdown(HTMLParser):
    def __init__(self, image_resolver: ImageResolver | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.href_stack: list[str | None] = []
        self.image_resolver = image_resolver
        self.skip_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip_tag:
            return
        if tag in SKIP_TAGS:
            self.skip_tag = tag
            return

        attrs_dict = dict(attrs)
        if tag in BLOCK_TAGS or tag == "br":
            self.parts.append("\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "img":
            src = attrs_dict.get("data-src") or attrs_dict.get("src") or ""
            alt = attrs_dict.get("alt") or ""
            if not src:
                return
            resolved = self.image_resolver(src, attrs_dict) if self.image_resolver else src
            if resolved:
                self.parts.append(f"\n![{alt}]({resolved})\n")
        elif tag == "a":
            self.href_stack.append(attrs_dict.get("href"))
        elif tag in {"strong", "b"}:
            self.parts.append("**")

    def handle_endtag(self, tag: str) -> None:
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_tag = None
            return
        if tag in BLOCK_TAGS or tag.startswith("h") and tag[1:].isdigit() or tag == "li":
            self.parts.append("\n")
        elif tag == "a":
            href = self.href_stack.pop() if self.href_stack else None
            if href:
                self.parts.append(f"({href})")
        elif tag in {"strong", "b"}:
            self.parts.append("**")

    def handle_data(self, data: str) -> None:
        if self.skip_tag:
            return
        text = html.unescape(data).strip()
        if not text:
            return
        if self.href_stack:
            self.parts.append(f"[{text}]")
        else:
            self.parts.append(text)

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


class SimpleHtmlToText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if self.skip_tag:
            return
        if tag in SKIP_TAGS:
            self.skip_tag = tag
        elif tag in BLOCK_TAGS or tag in {"br", "li"} or tag.startswith("h") and tag[1:].isdigit():
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_tag = None
            return
        if tag in BLOCK_TAGS or tag == "li" or tag.startswith("h") and tag[1:].isdigit():
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_tag:
            text = html.unescape(data).strip()
            if text:
                self.parts.append(text)

    def text(self) -> str:
        value = "".join(self.parts)
        value = re.sub(r"[ \t]+\n", "\n", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()


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
        if value and (override or key not in os.environ):
            os.environ[key] = value


def env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


def sanitize_filename(value: str, max_len: int = 80) -> str:
    value = re.sub(r'[\\/:*?"<>|#\n\r\t]', " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value or "未命名")[:max_len]


def parse_ts(value: Any) -> dt.datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or str(value).isdigit():
        number = int(value)
        if number > 100000000000:
            number //= 1000
        return dt.datetime.fromtimestamp(number)
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        return None


def html_to_markdown(html_text: str, image_resolver: ImageResolver | None = None) -> str:
    parser = SimpleHtmlToMarkdown(image_resolver=image_resolver)
    parser.feed(html_text or "")
    return parser.markdown()


def html_to_text(html_text: str) -> str:
    parser = SimpleHtmlToText()
    parser.feed(html_text or "")
    return parser.text()


def is_gif_reference(url: str, attrs: dict[str, str | None] | None = None) -> bool:
    attrs = attrs or {}
    if str(attrs.get("data-type") or "").lower() == "gif":
        return True
    parsed = urllib.parse.urlparse(html.unescape(url))
    query = urllib.parse.parse_qs(parsed.query)
    if (query.get("wx_fmt") or [""])[0].lower() == "gif":
        return True
    return parsed.path.lower().endswith(".gif")


def image_extension(data: bytes, content_type: str, url: str) -> str:
    media_type = content_type.split(";", 1)[0].strip().lower()
    by_type = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/avif": ".avif",
        "image/bmp": ".bmp",
        "image/svg+xml": ".svg",
    }
    if media_type in by_type:
        return by_type[media_type]
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    parsed = urllib.parse.urlparse(url)
    fmt = (urllib.parse.parse_qs(parsed.query).get("wx_fmt") or [""])[0].lower()
    if fmt in {"jpeg", "jpg", "png", "webp", "avif", "bmp"}:
        return ".jpg" if fmt == "jpeg" else f".{fmt}"
    suffix = Path(parsed.path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp", ".svg"} else ".bin"


@dataclass
class ImageLocalizer:
    asset_dir: Path
    relative_asset_dir: Path
    referer: str
    timeout: int = 30
    retries: int = 3
    downloaded: int = 0
    skipped_gifs: int = 0
    failures: list[str] = field(default_factory=list)
    url_cache: dict[str, str | None] = field(default_factory=dict)
    digest_cache: dict[str, str] = field(default_factory=dict)
    next_index: int = 1

    def resolve(self, url: str, attrs: dict[str, str | None]) -> str | None:
        return self.localize(url, attrs=attrs)

    def localize(
        self,
        url: str,
        *,
        attrs: dict[str, str | None] | None = None,
        preferred_name: str = "",
    ) -> str | None:
        url = html.unescape(url).strip()
        if not url:
            return None
        if url.startswith("//"):
            url = "https:" + url
        if not url.lower().startswith(("http://", "https://")):
            return url
        if url in self.url_cache:
            return self.url_cache[url]
        if is_gif_reference(url, attrs):
            self.skipped_gifs += 1
            self.url_cache[url] = None
            return None

        error = "unknown error"
        for attempt in range(1, self.retries + 1):
            try:
                request = urllib.request.Request(
                    url,
                    headers={
                        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                        "Referer": self.referer,
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    },
                )
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = response.read()
                    content_type = response.headers.get("Content-Type", "")
                if not data:
                    raise RuntimeError("empty image response")
                if content_type.lower().startswith("image/gif") or data.startswith((b"GIF87a", b"GIF89a")):
                    self.skipped_gifs += 1
                    self.url_cache[url] = None
                    return None

                digest = hashlib.sha256(data).hexdigest()
                if digest in self.digest_cache:
                    relative = self.digest_cache[digest]
                    self.url_cache[url] = relative
                    return relative

                extension = image_extension(data, content_type, url)
                if extension == ".bin":
                    raise RuntimeError(f"unsupported image type: {content_type or 'unknown'}")
                if preferred_name:
                    filename = sanitize_filename(preferred_name, max_len=40) + extension
                else:
                    filename = f"{self.next_index:03d}{extension}"
                    self.next_index += 1
                self.asset_dir.mkdir(parents=True, exist_ok=True)
                destination = self.asset_dir / filename
                destination.write_bytes(data)
                relative = (self.relative_asset_dir / filename).as_posix()
                self.digest_cache[digest] = relative
                self.url_cache[url] = relative
                self.downloaded += 1
                return relative
            except (OSError, RuntimeError, urllib.error.URLError) as exc:
                error = str(exc)
                if attempt < self.retries:
                    time.sleep(0.4 * attempt)

        self.failures.append(f"{url}: {error}")
        self.url_cache[url] = url
        return url


@dataclass
class DajialaClient:
    api_key: str
    verifycode: str = ""
    timeout: int = 30
    api_base: str = API_BASE
    api_retries: int = 3
    retry_backoff: float = 2.0

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
            url = f"{url}?{urllib.parse.urlencode(params, doseq=True, safe='')}"
        data = None
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {raw[:300]}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"接口返回不是 JSON: {raw[:300]}") from exc

    def credentials(self) -> dict[str, str]:
        return {"key": self.api_key, "verifycode": self.verifycode}

    def request_with_retry(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response: dict[str, Any] = {}
        for attempt in range(self.api_retries + 1):
            response = self.request_json(method, path, params=params, body=body)
            if response.get("code") not in TRANSIENT_API_CODES or attempt >= self.api_retries:
                return response
            time.sleep(self.retry_backoff * (2**attempt))
        return response

    def history(
        self,
        account: str,
        *,
        offset: str = "",
        ghid: str = "",
        url: str = "",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"offset": offset, **self.credentials()}
        if ghid:
            body["ghid"] = ghid
        elif url:
            body["url"] = url
        else:
            # The current endpoint accepts nickname; the old name parameter now returns code=105.
            body["nickname"] = account
        return self.request_with_retry(
            "POST",
            "/fbmain/monitor/v3/post_history",
            body=body,
        )

    def article_html(self, article_url: str) -> dict[str, Any]:
        return self.request_with_retry(
            "POST",
            "/fbmain/monitor/v3/article_html",
            body={"url": article_url, **self.credentials()},
        )

    def metrics(self, article_url: str) -> dict[str, Any]:
        return self.request_with_retry(
            "POST",
            "/fbmain/monitor/v3/read_zan_pro",
            body={"url": article_url, **self.credentials()},
        )

    def comments(self, article_url: str, buffer: str) -> dict[str, Any]:
        return self.request_with_retry(
            "POST",
            "/fbmain/monitor/v3/article_comment2",
            body={"url": article_url, "buffer": buffer, **self.credentials()},
        )


def assert_ok(response: dict[str, Any], context: str, allow_end: bool = False) -> None:
    code = response.get("code")
    if code in (0, None):
        return
    if allow_end and code in (110, 115):
        return
    message = response.get("msg") or response.get("msk") or response.get("message") or ""
    raise RuntimeError(f"{context}失败: code={code}, msg={message}")


def pick_metrics(response: dict[str, Any]) -> dict[str, int]:
    data = response.get("data") or {}
    return {
        "read": int(data.get("read") or 0),
        "like": int(data.get("zan") or 0),
        "looking": int(data.get("looking") or 0),
        "share": int(data.get("share_num") or 0),
        "collect": int(data.get("collect_num") or 0),
        "comment_count": int(data.get("comment_count") if data.get("comment_count") is not None else 0),
    }


def collect_first_level_comments(client: DajialaClient, article_url: str) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen_comments: set[str] = set()
    seen_buffers: set[str] = set()
    buffer = ""

    for page in range(1, 101):
        response = client.comments(article_url, buffer)
        if response.get("code") == 103:
            return []
        assert_ok(response, f"获取一级评论第 {page} 页")
        items = response.get("data") or []
        total = int(response.get("total") or 0)
        for item in items:
            dedupe_key = str(
                item.get("content_id")
                or item.get("id")
                or hashlib.sha256(
                    "|".join(
                        [
                            str(item.get("content") or ""),
                            str(item.get("create_time_stamp") or ""),
                            str(item.get("nick_name") or ""),
                        ]
                    ).encode("utf-8")
                ).hexdigest()
            )
            if dedupe_key in seen_comments:
                continue
            seen_comments.add(dedupe_key)
            collected.append(
                {
                    "article_url": article_url,
                    "content": item.get("content") or "",
                    "like_num": int(item.get("like_num") or 0),
                    "is_top": int(item.get("is_top") or 0),
                    "province_name": item.get("province_name") or "",
                }
            )

        next_buffer_value = response.get("buffer")
        next_buffer = "" if next_buffer_value in (None, "") else str(next_buffer_value)
        if not items or not next_buffer or next_buffer in seen_buffers or total and len(collected) >= total:
            break
        seen_buffers.add(next_buffer)
        buffer = next_buffer
    else:
        raise RuntimeError("一级评论翻页超过 100 页，已停止以避免无限请求")

    return collected


def merge_article(
    requested_account: str,
    history: dict[str, Any],
    html_response: dict[str, Any],
    metrics: dict[str, int],
) -> dict[str, Any]:
    data = html_response.get("data") or {}
    html_content = data.get("html") or ""
    publish_dt = parse_ts(data.get("post_time") or data.get("post_time_str") or history.get("post_time"))
    return {
        "title": data.get("title") or history.get("title") or "无标题",
        "content": html_to_text(html_content),
        "article_url": history.get("url") or data.get("article_url") or "",
        "publish_time": publish_dt.isoformat(sep=" ") if publish_dt else "",
        "date": publish_dt.date().isoformat() if publish_dt else "未知日期",
        "account": data.get("nickname") or requested_account,
        "author": data.get("author") or "",
        "digest": data.get("desc") or history.get("digest") or "",
        "read": metrics["read"],
        "like": metrics["like"],
        "looking": metrics["looking"],
        "share": metrics["share"],
        "collect": metrics["collect"],
        "comment_count": metrics["comment_count"],
        "_html": html_content,
        "_cover_url": data.get("cover_url") or history.get("cover_url") or "",
    }


def article_file_name(article: dict[str, Any]) -> str:
    return f"{article['date']}-{sanitize_filename(article['title'])}.md"


def comment_file_name(article: dict[str, Any]) -> str:
    return f"{sanitize_filename(article['title'])}.csv"


def write_article(output_dir: Path, article: dict[str, Any], timeout: int) -> tuple[Path, ImageLocalizer]:
    account_dir = output_dir / sanitize_filename(article["account"])
    account_dir.mkdir(parents=True, exist_ok=True)
    article_path = account_dir / article_file_name(article)
    asset_folder_name = article_path.stem
    asset_dir = account_dir / "assets" / asset_folder_name
    staging_asset_dir = asset_dir.parent / f".{asset_folder_name}.tmp"
    if staging_asset_dir.exists():
        shutil.rmtree(staging_asset_dir)

    localizer = ImageLocalizer(
        asset_dir=staging_asset_dir,
        relative_asset_dir=Path("assets") / asset_folder_name,
        referer=article["article_url"],
        timeout=timeout,
    )
    temporary_article_path = article_path.with_name(f".{article_path.name}.tmp")
    try:
        cover = ""
        if article.get("_cover_url"):
            cover = localizer.localize(article["_cover_url"], preferred_name="cover") or ""
        markdown_content = html_to_markdown(article.get("_html") or "", localizer.resolve)
        if not markdown_content:
            markdown_content = article.get("content") or ""

        metric_table = "\n".join(
            [
                "| 指标 | 数值 |",
                "| --- | ---: |",
                f"| 阅读 | {article['read']} |",
                f"| 点赞 | {article['like']} |",
                f"| 在看 | {article['looking']} |",
                f"| 转发 | {article['share']} |",
                f"| 收藏 | {article['collect']} |",
                f"| 评论总数 | {article['comment_count']} |",
            ]
        )
        parts = [
            f"# {article['title']}",
            f"公众号：{article['account']}",
            f"作者：{article['author']}",
            f"原文：{article['article_url']}",
            f"发布时间：{article['publish_time'] or '未知'}",
            "摘要：" + (article["digest"] or "无"),
            metric_table,
        ]
        if cover:
            parts.append(f"![封面]({cover})")
        parts.append("## 正文\n" + markdown_content)
        temporary_article_path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")

        if asset_dir.exists():
            shutil.rmtree(asset_dir)
        if staging_asset_dir.exists():
            staging_asset_dir.replace(asset_dir)
        temporary_article_path.replace(article_path)
    except Exception:
        if staging_asset_dir.exists():
            shutil.rmtree(staging_asset_dir)
        if temporary_article_path.exists():
            temporary_article_path.unlink()
        raise
    return article_path, localizer


def write_tables(
    account_dir: Path,
    articles: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    *,
    include_comments: bool = False,
) -> None:
    account_dir.mkdir(parents=True, exist_ok=True)
    stale_overview = account_dir / "账号概览.md"
    if stale_overview.exists():
        stale_overview.unlink()

    with (account_dir / "文章数据.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=ARTICLE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for article in sorted(articles, key=lambda item: item.get("publish_time") or "", reverse=True):
            writer.writerow({key: article.get(key, "") for key in ARTICLE_FIELDS})

    if not include_comments:
        return

    stale_comment_table = account_dir / "评论数据.csv"
    if stale_comment_table.exists():
        stale_comment_table.unlink()

    comment_dir = account_dir / "评论"
    comment_dir.mkdir(parents=True, exist_ok=True)
    comments_by_url: dict[str, list[dict[str, Any]]] = {}
    for comment in comments:
        comments_by_url.setdefault(str(comment.get("article_url") or ""), []).append(comment)

    used_paths: dict[Path, str] = {}
    for article in articles:
        article_url = str(article.get("article_url") or "")
        path = comment_dir / comment_file_name(article)
        previous_url = used_paths.get(path)
        if previous_url and previous_url != article_url:
            raise RuntimeError(f"文章标题重复，评论文件名冲突：{article['title']}")
        used_paths[path] = article_url
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=COMMENT_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for comment in comments_by_url.get(article_url, []):
                writer.writerow({key: comment.get(key, "") for key in COMMENT_FIELDS})


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
    if not api_key:
        print(
            "还没有配置极致了 API Key。请把 API Key 和附加码提供给 Agent，让它帮你完成本地配置。",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    account = args.account.strip()
    if not account and not args.ghid and not args.account_url:
        print("请至少提供 --account、--ghid 或 --account-url 其中一个。", file=sys.stderr)
        return 2
    account_label = account or args.ghid or args.account_url
    client = DajialaClient(api_key=api_key, verifycode=verifycode, timeout=args.timeout)
    start_date = dt.date.fromisoformat(args.start_date) if args.start_date else None
    articles: list[dict[str, Any]] = []
    all_comments: list[dict[str, Any]] = []
    include_comments = bool(getattr(args, "include_comments", False))
    seen_urls: set[str] = set()
    image_downloaded = 0
    image_failures: list[str] = []
    gif_skipped = 0
    page = 1
    offset = ""
    seen_offsets: set[str] = set()

    while True:
        if args.max_pages and page > args.max_pages:
            break
        print(f"获取列表：{account_label} 第 {page} 页")
        history_response = client.history(
            account,
            offset=offset,
            ghid=args.ghid,
            url=args.account_url,
        )
        assert_ok(history_response, "获取文章列表", allow_end=True)
        if history_response.get("code") in (110, 115):
            break
        items = history_response.get("data") or []
        if not items:
            break

        should_stop = False
        for item in items:
            if not args.include_deleted and str(item.get("is_deleted", "0")) != "0":
                continue
            article_url = item.get("url") or ""
            if not article_url or article_url in seen_urls:
                continue
            publish_dt = parse_ts(item.get("post_time") or item.get("post_time_str"))
            if start_date and publish_dt and publish_dt.date() < start_date:
                should_stop = True
                continue

            seen_urls.add(article_url)
            print(f"  采集：{item.get('title') or article_url}")
            html_response = client.article_html(article_url)
            assert_ok(html_response, "获取文章 HTML")
            metrics_response = client.metrics(article_url)
            assert_ok(metrics_response, "获取互动数据")
            comments = collect_first_level_comments(client, article_url) if include_comments else []
            article = merge_article(account, item, html_response, pick_metrics(metrics_response))
            if not article["content"]:
                raise RuntimeError(f"正文为空：{article['title']}")
            _, localizer = write_article(output_dir, article, args.timeout)
            image_downloaded += localizer.downloaded
            image_failures.extend(localizer.failures)
            gif_skipped += localizer.skipped_gifs
            articles.append(article)
            all_comments.extend(comments)

            if args.limit and len(articles) >= args.limit:
                should_stop = True
                break
            time.sleep(args.delay)

        next_offset_value = history_response.get("offset")
        next_offset = "" if next_offset_value in (None, "") else str(next_offset_value)
        is_end = history_response.get("is_end") in (True, 1, "1", "true", "True")
        if should_stop or is_end or next_offset in seen_offsets or next_offset == offset:
            break
        if not next_offset:
            # The current API uses offset; stop safely if an incomplete response omits it.
            break
        if next_offset:
            seen_offsets.add(next_offset)
            offset = next_offset
        page += 1
        time.sleep(args.delay)

    if articles:
        account_name = articles[0]["account"] or account
        account_dir = output_dir / sanitize_filename(account_name)
        write_tables(account_dir, articles, all_comments, include_comments=include_comments)

    status = "部分成功" if image_failures else "成功"
    print(
        f"完成：{status}；文章 {len(articles)} 篇，一级评论 {len(all_comments)} 条，"
        f"本地静态图片 {image_downloaded} 张，跳过 GIF {gif_skipped} 张，"
        f"图片失败 {len(image_failures)} 张；评论内容 {'已采集' if include_comments else '未采集'}；"
        f"输出目录 {output_dir}"
    )
    for failure in image_failures:
        print(f"图片下载失败：{failure}", file=sys.stderr)
    return 1 if image_failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="采集公众号文章、本地静态图片和互动数据；评论需显式启用")
    parser.add_argument("--account", default="", help="公众号名称，例如：广州楼市发布")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录，默认 ./output/wechat-articles")
    parser.add_argument("--start-date", default="", help="只采集此日期及之后的文章，格式 YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=0, help="最多采集文章数，0 表示不限制")
    parser.add_argument("--max-pages", type=int, default=0, help="最多获取列表页数，0 表示采完")
    parser.add_argument("--delay", type=float, default=0.6, help="文章之间的接口调用间隔秒数")
    parser.add_argument("--timeout", type=int, default=30, help="接口和图片下载超时秒数")
    parser.add_argument("--include-deleted", action="store_true", help="包含列表中标记为已删除的文章")
    parser.add_argument("--ghid", default="", help="公众号原始 ID；优先于公众号名称查询历史文章")
    parser.add_argument("--account-url", default="", help="任意该公众号文章链接；用于查询历史文章")
    parser.add_argument(
        "--include-comments",
        action="store_true",
        help="仅在用户明确确认后使用：采集公开一级评论并生成评论 CSV",
    )
    parser.add_argument("--api-key", default="", help="极致了 API key，建议使用环境变量 DAJIALA_API_KEY")
    parser.add_argument("--verifycode", default="", help="附加码，建议使用环境变量 DAJIALA_VERIFY_CODE")
    parser.add_argument("--env-file", default="", help="读取指定 .env 文件；优先级高于当前目录 .env")
    return parser


def main() -> int:
    return collect(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
